from app.chat.chat_engine import ChatEngine
from app.chat.constants import INSUFFICIENT_EVIDENCE_MESSAGE
from app.chat.llm.gemini_chat_client import GeminiChatClient
from app.config import config
from app.graph.graph_engine import KnowledgeGraphEngine
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.conftest import empty_scan_result, make_scan_result, python_fastapi_scan


class MockGeminiClient(GeminiChatClient):
    def __init__(self, text: str = "", enabled: bool = True) -> None:
        super().__init__(api_key="test", enabled=enabled)
        self._text = text

    def generate(self, prompt: str) -> dict:
        return {"ok": True, "text": self._text, "error": None}


class ExplodingGeminiClient(GeminiChatClient):
    def __init__(self) -> None:
        super().__init__(api_key="test", enabled=True)

    def generate(self, prompt: str) -> dict:
        raise AssertionError("Gemini should not be called when orchestration is requested and disabled.")


def test_empty_question_rejected():
    engine = ChatEngine(llm_client=MockGeminiClient(enabled=False))
    scan = empty_scan_result()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)

    try:
        engine.answer("", scan, intelligence, graph)
    except ValueError as exc:
        assert "Question must not be empty" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_chat_engine_works_with_llm_disabled():
    scan = python_fastapi_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    engine = ChatEngine(llm_client=GeminiChatClient(enabled=False))

    answer = engine.answer("Which API endpoints exist?", scan, intelligence, graph)
    assert answer.answer
    assert answer.insufficient_context is False
    assert answer.evidence


def test_chat_engine_returns_insufficient_evidence_when_no_context():
    scan = empty_scan_result()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    engine = ChatEngine(llm_client=GeminiChatClient(enabled=False))

    answer = engine.answer("What API endpoints exist?", scan, intelligence, graph)
    assert answer.answer == INSUFFICIENT_EVIDENCE_MESSAGE
    assert answer.insufficient_context is True


def test_chat_engine_mocked_gemini_answer_works():
    scan = python_fastapi_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    engine = ChatEngine(llm_client=MockGeminiClient(text="- GET /users [E1]"))

    answer = engine.answer("Which API endpoint handles users?", scan, intelligence, graph)
    assert "[E1]" in answer.answer
    assert answer.insufficient_context is False


def test_chat_engine_orchestration_uses_fallback_when_disabled():
    old = config.scanner.llm_orchestration_enabled
    object.__setattr__(config.scanner, "llm_orchestration_enabled", False)
    try:
        scan = python_fastapi_scan()
        intelligence = IntelligenceEngine().analyze(scan)
        graph = KnowledgeGraphEngine().build(scan, intelligence)
        engine = ChatEngine(llm_client=ExplodingGeminiClient())
        answer = engine.answer(
            "Which API endpoints exist?",
            scan,
            intelligence,
            graph,
            include_llm_orchestration=True,
        )
    finally:
        object.__setattr__(config.scanner, "llm_orchestration_enabled", old)

    assert answer.answer
    assert any("orchestration disabled" in warning.lower() for warning in answer.warnings)
    assert "magicmock" not in answer.answer.lower()


def test_general_question_filters_ignored_paths_and_returns_project_summary():
    scan = make_scan_result(
        files=[
            {"path": "main.py", "extension": ".py"},
            {"path": "requirements.txt", "extension": ".txt"},
            {"path": "node_modules/@swc/helpers/index.js", "extension": ".js"},
        ],
        contents={
            "main.py": 'from fastapi import FastAPI\napp = FastAPI()\n',
            "requirements.txt": "fastapi\nuvicorn\n",
            "node_modules/@swc/helpers/index.js": "export const helper = 1;\n",
        },
    )
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    engine = ChatEngine(llm_client=GeminiChatClient(enabled=False))

    answer = engine.answer("What is the goal of this project?", scan, intelligence, graph)
    assert "node_modules" not in answer.answer.lower()
    assert "site-packages" not in answer.answer.lower()
    assert answer.evidence
    assert all(not (ev.file and "node_modules" in ev.file.lower()) for ev in answer.evidence)
    assert all("node_modules" not in path.lower() for path in answer.related_files)
    assert all("node_modules" not in node.lower() for node in answer.related_nodes)
    assert "classified as" in answer.answer.lower() or "project" in answer.answer.lower() or answer.answer == INSUFFICIENT_EVIDENCE_MESSAGE


def test_kannadi_med_goal_question_returns_product_level_answer():
    scan = make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "main.py", "extension": ".py"},
        ],
        contents={
            "README.md": "# Kannadi Med\n\nAI-assisted clinical diagnosis tool.\n",
            "main.py": 'from fastapi import FastAPI\napp = FastAPI()\n\n@app.post("/diagnose")\ndef diagnose(): pass\n\n@app.post("/search")\ndef search(): pass\n',
        },
    )
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    engine = ChatEngine(llm_client=GeminiChatClient(enabled=False))

    answer = engine.answer("What does this project do?", scan, intelligence, graph)
    
    answer_lower = answer.answer.lower()
    
    # Check for requested product-level phrases
    assert "kannadi med is an offline-first ai-assisted medical diagnosis and knowledge retrieval backend built with fastapi" in answer_lower
    
    # Check that safety rules stripped 'clinical'
    assert "clinical" not in answer_lower
    
    # Must NOT contain raw repr patterns
    for bad in ["type='", "confidence='", "reasoning=[", "evidence=[", "EvidenceItem(", "ArchitectureResult("]:
        assert bad not in answer.answer

    # Must retain evidence
    assert answer.evidence
    # Must retain high confidence
    assert answer.confidence in ("high", "medium")
    
    # Clean answer contains valid citation markers
    assert "[E1]" in answer.answer
    assert "See evidence" in answer.answer

    # No speculative language warnings when answering from facts
    assert all("speculative" not in w.lower() for w in answer.warnings)


def test_ahal_ai_goal_question_returns_startup_level_answer():
    scan = make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "main.py", "extension": ".py"},
            {"path": "app/chat/chat_service.py", "extension": ".py"},
            {"path": "app/docs/report.py", "extension": ".py"},
            {"path": "frontend/dashboard/page.tsx", "extension": ".tsx"},
            {"path": "frontend/lib/api.ts", "extension": ".ts"},
        ],
        contents={
            "README.md": "# AHAL AI\n\nAI-Powered Developer Intelligence System.\n",
            "main.py": 'from fastapi import FastAPI\napp = FastAPI()\n\n@app.post("/analyze")\ndef analyze(): pass\n\n@app.post("/ask")\ndef ask(): pass\n\n@app.post("/summarize")\ndef summarize(): pass\n\n@app.get("/session/status")\ndef status(): pass\n',
            "app/chat/chat_service.py": "class ChatService: pass\n",
            "app/docs/report.py": "class ReportGenerator: pass\n",
            "frontend/dashboard/page.tsx": "export default function Dashboard() {}\n",
            "frontend/lib/api.ts": "export const api = {};\n",
        },
    )
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    engine = ChatEngine(llm_client=GeminiChatClient(enabled=False))

    answer = engine.answer("What is the goal of this project?", scan, intelligence, graph)

    answer_lower = answer.answer.lower()

    # Product-level assertions
    assert "ahal ai" in answer_lower
    assert "repository intelligence" in answer_lower or "code intelligence" in answer_lower
    assert "fastapi" in answer_lower

    # At least one API route or capability term mentioned
    assert any(term in answer_lower for term in [
        "analyze", "analysis", "ask", "query", "summarize", "summarization",
    ])

    # Citations
    assert "[E1]" in answer.answer
    assert answer.confidence in ("high", "medium")

    # No unsupported claims
    for bad in ["funding", "revenue", "enterprise-grade security", "guarantees"]:
        assert bad not in answer_lower

    # No raw repr
    for bad in ["type='", "confidence='", "EvidenceItem(", "ArchitectureResult("]:
        assert bad not in answer.answer


def test_remaining_question_uses_project_brief():
    scan = make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "main.py", "extension": ".py"},
        ],
        contents={
            "README.md": "# Service\n\nBackend service.\n",
            "main.py": 'from fastapi import FastAPI\napp = FastAPI()\n',
        },
    )
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    engine = ChatEngine(llm_client=GeminiChatClient(enabled=False))

    answer = engine.answer("What is remaining?", scan, intelligence, graph)
    assert "remaining work appears to include" in answer.answer.lower()


def test_issues_question_uses_project_brief():
    scan = make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "main.py", "extension": ".py"},
        ],
        contents={
            "README.md": "# Service\n\nBackend service.\n",
            "main.py": 'from fastapi import FastAPI\napp = FastAPI()\n',
        },
    )
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    engine = ChatEngine(llm_client=GeminiChatClient(enabled=False))

    answer = engine.answer("What are the issues?", scan, intelligence, graph)
    assert "issues" in answer.answer.lower() or "no critical issues" in answer.answer.lower()


def test_hi_through_engine_returns_casual():
    scan = empty_scan_result()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    engine = ChatEngine(llm_client=GeminiChatClient(enabled=False))

    answer = engine.answer("hi", scan, intelligence, graph)
    assert "hi" in answer.answer.lower() or "help" in answer.answer.lower()
    assert answer.intent == "casual"
    assert not answer.evidence
    assert not answer.sections


def test_unsupported_question_through_engine_returns_safe_refusal():
    scan = empty_scan_result()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    engine = ChatEngine(llm_client=GeminiChatClient(enabled=False))

    answer = engine.answer("What is my bank password?", scan, intelligence, graph)
    assert "enough relevant project evidence" in answer.answer.lower()
    assert answer.intent == "unsupported"
    assert not answer.evidence


def test_repo_question_still_routes_to_repo_pipeline():
    scan = python_fastapi_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    engine = ChatEngine(llm_client=GeminiChatClient(enabled=False))

    # "What does this project do?" should still trigger repo pipeline
    answer = engine.answer("What does this project do?", scan, intelligence, graph)
    assert answer.intent == "project_overview"
    assert answer.evidence
    assert answer.sections

