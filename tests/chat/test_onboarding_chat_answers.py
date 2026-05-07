from __future__ import annotations

from types import SimpleNamespace

from app.chat.answer_composer_v2 import AnswerComposerV2
from app.chat.context_pack_builder import ChatContextPackBuilder
from app.chat.intent_classifier import ChatIntentClassifier
from app.chat.models import ChatContextPack, ChatIntentEntities, ChatIntentResult, EvidenceReference
from app.intelligence.presentation_models import CanonicalProjectIntelligence


def _canonical() -> CanonicalProjectIntelligence:
    return CanonicalProjectIntelligence(
        session_id="onboarding-session",
        project_name="ContextBridge AI",
        project_type="fullstack",
        repo_type="fullstack_app",
        product_summary="ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.",
        project_goal="ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.",
        product_domain="code intelligence platform",
        architecture_summary="Fullstack project with frontend and backend surfaces.",
        what="ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.",
        why="It exists to help teams turn code changes into structured, queryable project knowledge.",
    )


def _context_pack(onboarding_steps: list[dict] | None = None) -> ChatContextPack:
    evidence = [
        EvidenceReference(source_type="file", source_id="README.md", file="README.md", reason="Project overview.", confidence="high"),
        EvidenceReference(source_type="file", source_id="package.json", file="package.json", reason="Dependency manifest.", confidence="high"),
        EvidenceReference(source_type="file", source_id="Dockerfile", file="Dockerfile", reason="Runtime container.", confidence="medium"),
        EvidenceReference(source_type="file", source_id="app/api/__init__.py", file="app/api/__init__.py", reason="API package.", confidence="medium"),
        EvidenceReference(source_type="file", source_id="frontend/src/app/api/page.tsx", file="frontend/src/app/api/page.tsx", reason="Frontend route/page.", confidence="medium"),
        EvidenceReference(source_type="file", source_id="very/deep/generated/file.ts", file="very/deep/generated/file.ts", reason="Generated file.", confidence="low"),
    ]
    return ChatContextPack(
        session_id="onboarding-session",
        question="I'm new to this project! Where do I start first?",
        intent="onboarding_question",
        project_identity={"project_type": "fullstack", "frameworks": ["React", "FastAPI"]},
        architecture_summary={"type": "fullstack", "entry_points": ["frontend/src/main.tsx", "app/main.py"]},
        relevant_apis=[{"method": "POST", "path": "/analyze", "file": "app/api/__init__.py", "handler": "Analysis API", "framework": "FastAPI", "evidence": []}],
        relevant_onboarding_steps=onboarding_steps or [],
        selected_evidence=evidence,
        evidence_map={f"E{index}": item for index, item in enumerate(evidence, start=1)},
        confidence="high",
        canonical_intelligence=_canonical(),
    )


def _compose(context_pack: ChatContextPack | None = None):
    intent = ChatIntentResult(intent="onboarding_question", confidence="high", entities=ChatIntentEntities())
    return AnswerComposerV2().compose("I'm new to this project! Where do I start first?", intent, context_pack or _context_pack())


def test_onboarding_answer_has_reading_order():
    answer = _compose()

    titles = [section.title for section in answer.sections]
    assert "First 10 minutes" in titles
    assert "Next 20 minutes" in titles
    assert "Key files to inspect" in titles


def test_onboarding_answer_not_generic_overview():
    answer = _compose()

    rendered = answer.answer.lower()
    assert rendered.count("what it is") == 0
    assert "detected architecture" not in rendered


def test_onboarding_evidence_limited():
    answer = _compose()

    assert len(answer.evidence) <= 5


def test_onboarding_no_command_hallucination():
    answer = _compose()

    rendered = answer.answer.lower()
    assert "npm install" not in rendered
    assert "npm run dev" not in rendered
    assert "python -m app.main" not in rendered
    assert "docker compose up" not in rendered


def test_onboarding_uses_canonical_and_onboarding_report():
    report = SimpleNamespace(
        summary="Read the product docs, then trace one workflow.",
        reading_order=[
            SimpleNamespace(title="Read Product Context", description="Start with README.md.", files_to_read=["README.md"], evidence=[]),
            SimpleNamespace(title="Trace Main Entry Points", description="Open frontend and backend entry points.", files_to_read=["frontend/src/main.tsx", "app/main.py"], evidence=[]),
        ],
        key_entry_points=["frontend/src/main.tsx - frontend entry point", "app/main.py - backend entry point"],
        important_apis=["POST /analyze - defined in app/api/__init__.py"],
        main_workflows=["Frontend submits an analysis request to the backend API."],
        gotchas=["Do not assume business purpose beyond canonical evidence."],
        avoid_first=["Generated files and deep config."],
    )
    context_pack = ChatContextPackBuilder().build(
        session_id="onboarding-session",
        question="I'm new to this project! Where do I start first?",
        intent=ChatIntentResult(intent="onboarding_question", confidence="high", entities=ChatIntentEntities()),
        intelligence_result=SimpleNamespace(architecture=SimpleNamespace(type="fullstack", confidence="high"), frameworks=[], databases=[], api_endpoints=[], modules=[], workflow=None, warnings=[]),
        onboarding_report=report,
        canonical_intelligence=_canonical(),
    )

    answer = _compose(context_pack)

    rendered = answer.answer
    assert "Read Product Context" in rendered
    assert "Trace Main Entry Points" in rendered
    assert "POST /analyze" in rendered
    assert _canonical().what not in rendered


def test_onboarding_suggested_followups_present():
    answer = _compose()

    assert "What APIs exist?" in answer.suggested_followups
    assert "How does the main workflow work?" in answer.suggested_followups


def test_intent_classifier_new_to_project_is_onboarding():
    result = ChatIntentClassifier().classify("I'm new to this project! Where do I start first?")

    assert result.intent == "onboarding_question"
