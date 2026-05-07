from app.chat.answer_composer_v2 import AnswerComposerV2
from app.chat.models import ChatContextPack, ChatIntentEntities, ChatIntentResult, EvidenceReference
from app.intelligence.canonical_presenter import CanonicalProjectPresenter
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.test_repository_archetypes import _dataset_scan, _python_package_scan


def _context_for(scan, session_id: str):
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build(session_id, scan, intelligence)
    evidence = [EvidenceReference(source_type="file", source_id="README.md", file="README.md", reason="Repository summary evidence.", confidence="high")]
    return ChatContextPack(
        session_id=session_id,
        question="What APIs exist?",
        intent="api_explanation",
        project_identity={
            "summary": canonical.product_summary,
            "project_type": canonical.project_type,
            "domain": canonical.product_domain,
        },
        architecture_summary={"type": canonical.project_type, "confidence": "medium", "entry_points": []},
        selected_evidence=evidence,
        evidence_map={"E1": evidence[0]},
        canonical_intelligence=canonical,
        confidence="medium",
    )


def test_chat_apis_for_package_says_no_http_apis():
    context_pack = _context_for(_python_package_scan(), "chat-pkg")
    answer = AnswerComposerV2().compose(
        "What APIs exist?",
        ChatIntentResult(intent="api_explanation", confidence="high", entities=ChatIntentEntities()),
        context_pack,
    )

    assert "no http api endpoints were identified" in answer.answer.lower()
    assert "package/library apis" in answer.answer.lower()


def test_chat_what_is_built_for_dataset_uses_dataset_language():
    context_pack = _context_for(_dataset_scan(), "chat-dataset")
    answer = AnswerComposerV2().compose(
        "What is built?",
        ChatIntentResult(intent="what_is_built", confidence="high", entities=ChatIntentEntities()),
        context_pack.model_copy(update={"intent": "what_is_built", "question": "What is built?"}),
    )

    assert "dataset assets" in answer.answer.lower()
    assert "metadata" in answer.answer.lower()
    assert "application features" in answer.answer.lower()
