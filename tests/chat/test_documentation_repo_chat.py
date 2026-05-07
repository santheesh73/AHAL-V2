from app.chat.answer_composer_v2 import AnswerComposerV2
from app.chat.models import ChatContextPack, ChatIntentEntities, ChatIntentResult, EvidenceReference
from app.intelligence.canonical_presenter import CanonicalProjectPresenter
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.test_repository_type_classifier import _coding_interview_university_scan


def test_chat_apis_for_curriculum_says_no_apis():
    scan = _coding_interview_university_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("curriculum-chat", scan, intelligence)
    evidence = [
        EvidenceReference(source_type="file", source_id="README.md", file="README.md", reason="README describes the study plan.", confidence="high"),
    ]
    context_pack = ChatContextPack(
        session_id="curriculum-chat",
        question="What APIs exist?",
        intent="api_explanation",
        project_identity={
            "summary": canonical.product_summary,
            "project_type": canonical.project_type,
            "domain": canonical.product_domain,
        },
        architecture_summary={"type": "unknown", "confidence": "low", "entry_points": []},
        selected_evidence=evidence,
        evidence_map={"E1": evidence[0]},
        canonical_intelligence=canonical,
        confidence="medium",
    )

    answer = AnswerComposerV2().compose(
        "What APIs exist?",
        ChatIntentResult(intent="api_explanation", confidence="high", entities=ChatIntentEntities()),
        context_pack,
    )

    assert "no api endpoints were identified" in answer.answer.lower()
    assert "documentation/curriculum repository" in answer.answer.lower()

