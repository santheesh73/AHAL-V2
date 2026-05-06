from __future__ import annotations

from app.chat.chat_engine import ChatEngine
from app.chat.llm.gemini_chat_client import GeminiChatClient
from app.docs.prd_engine import PRDEngine
from app.graph.graph_engine import KnowledgeGraphEngine
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.test_canonical_presenter import _contextbridge_scan


def test_chat_project_overview_matches_canonical():
    scan = _contextbridge_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    prd = PRDEngine().generate(scan, intelligence, graph, session_id="session-1")
    answer = ChatEngine(llm_client=GeminiChatClient(enabled=False)).answer(
        "What does this project do?",
        scan,
        intelligence,
        graph,
        session_id="session-1",
    )

    assert prd.canonical_intelligence is not None
    assert prd.canonical_intelligence.what in answer.answer or prd.canonical_intelligence.product_summary in answer.answer
    assert "developer tool" in answer.answer.lower() or "code intelligence" in answer.answer.lower()
    assert prd.canonical_intelligence.product_domain in answer.answer.lower() or "developer tool" in answer.answer.lower()
    assert "content management application" not in answer.answer.lower()


def test_chat_overview_has_zero_cms_matches():
    scan = _contextbridge_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    answer = ChatEngine(llm_client=GeminiChatClient(enabled=False)).answer(
        "What does this project do?",
        scan,
        intelligence,
        graph,
        session_id="session-1",
    )

    assert "content management application" not in answer.answer.lower()


def test_chat_why_matches_canonical():
    scan = _contextbridge_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    prd = PRDEngine().generate(scan, intelligence, graph, session_id="session-1")
    answer = ChatEngine(llm_client=GeminiChatClient(enabled=False)).answer(
        "Why does this project exist?",
        scan,
        intelligence,
        graph,
        session_id="session-1",
    )

    assert prd.canonical_intelligence is not None
    assert prd.canonical_intelligence.why in answer.answer
