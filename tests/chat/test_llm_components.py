from app.chat.constants import INSUFFICIENT_EVIDENCE_MESSAGE
from app.chat.llm.answer_validator import AnswerValidator
from app.chat.llm.chat_prompt_builder import ChatPromptBuilder
from app.chat.models import ChatAnswer, EvidenceReference, QuestionClassification, RetrievedContext


def test_prompt_contains_evidence_ids():
    context = RetrievedContext(
        context_id="ctx-1",
        title="API users",
        content="GET /users in app/api/routes.py",
        source_type="api_endpoint",
        source_id="GET:/users",
        category="api",
        evidence=[
            EvidenceReference(
                source_type="api_endpoint",
                source_id="GET:/users",
                file="app/api/routes.py",
                reason="FastAPI route decorator found",
                confidence="high",
            )
        ],
    )
    prompt = ChatPromptBuilder().build(
        "Which endpoint handles users?",
        QuestionClassification(category="api", entities=["users"], confidence="high"),
        [context],
    )

    assert "[E1]" in prompt
    assert "FastAPI route decorator found" in prompt


def test_validator_rejects_unknown_citations():
    context = RetrievedContext(
        context_id="ctx-1",
        title="Summary",
        content="Known context",
        source_type="file",
        source_id="main.py",
        category="general",
        evidence=[
            EvidenceReference(
                source_type="file",
                source_id="main.py",
                file="main.py",
                reason="Scanned content",
                confidence="high",
            )
        ],
    )
    answer = ChatAnswer(
        answer="This is backed by [E2].",
        confidence="high",
        evidence=context.evidence,
        warnings=[],
        insufficient_context=False,
    )

    validated = AnswerValidator().validate(answer, [context])
    assert validated.answer == INSUFFICIENT_EVIDENCE_MESSAGE
    assert validated.insufficient_context is True


def test_validator_repairs_missing_citations():
    context = RetrievedContext(
        context_id="ctx-1",
        title="Summary",
        content="Known context",
        source_type="file",
        source_id="main.py",
        category="general",
        evidence=[
            EvidenceReference(
                source_type="file",
                source_id="main.py",
                file="main.py",
                reason="Scanned content",
                confidence="high",
            )
        ],
    )
    answer = ChatAnswer(
        answer="This is a deterministic answer.",
        confidence="high",
        evidence=context.evidence,
        warnings=[],
        insufficient_context=False,
    )

    validated = AnswerValidator().validate(answer, [context])
    assert "[E1]" in validated.answer
    assert validated.confidence == "high"
