"""Structured, evidence-grounded chat engine for repository sessions."""

from __future__ import annotations

import json
import logging
from typing import Optional

from app.chat.answer_composer_v2 import AnswerComposerV2
from app.chat.casual_composer import CasualChatComposer
from app.chat.chat_router import ChatMessageRouter
from app.chat.constants import INSUFFICIENT_EVIDENCE_MESSAGE
from app.chat.context_pack_builder import ChatContextPackBuilder
from app.chat.intent_classifier import ChatIntentClassifier
from app.chat.llm.answer_validator import AnswerValidator
from app.chat.llm.chat_prompt_builder import ChatPromptBuilder
from app.chat.llm.gemini_chat_client import GeminiChatClient
from app.chat.memory.chat_memory import chat_memory
from app.chat.models import ChatAnswer, ChatIntentResult, ChatMessage
from app.chat.retrieval.project_purpose_extractor import ProjectPurposeExtractor
from app.chat.utils import build_followups, filter_chat_evidence, sanitize_chat_answer, sanitize_chat_text
from app.config import config
from app.docs.prd_engine import PRDEngine
from app.intelligence.canonical_presenter import CanonicalProjectPresenter
from app.intelligence.consistency_validator import OutputConsistencyValidator
from app.intelligence.product_identity import ProductIdentityResolver
from app.llm_orchestration import LLMOrchestrator, OrchestrationRequest
from app.onboarding import OnboardingGenerator
from app.testing import TestGapDetector

logger = logging.getLogger(__name__)


class ChatEngine:
    def __init__(
        self,
        intent_classifier: Optional[ChatIntentClassifier] = None,
        context_pack_builder: Optional[ChatContextPackBuilder] = None,
        prompt_builder: Optional[ChatPromptBuilder] = None,
        llm_client: Optional[GeminiChatClient] = None,
        validator: Optional[AnswerValidator] = None,
        answer_composer: Optional[AnswerComposerV2] = None,
        orchestrator: Optional[LLMOrchestrator] = None,
    ) -> None:
        self._intent_classifier = intent_classifier or ChatIntentClassifier()
        self._context_pack_builder = context_pack_builder or ChatContextPackBuilder()
        self._prompt_builder = prompt_builder or ChatPromptBuilder()
        self._llm_client = llm_client or GeminiChatClient()
        self._validator = validator or AnswerValidator()
        self._answer_composer = answer_composer or AnswerComposerV2()
        self._orchestrator = orchestrator or LLMOrchestrator()
        self._message_router = ChatMessageRouter()
        self._casual_composer = CasualChatComposer()
        self._truth_validator = OutputConsistencyValidator()
        self._identity_resolver = ProductIdentityResolver()
        self._purpose_extractor = ProjectPurposeExtractor()
        self._canonical_presenter = CanonicalProjectPresenter()

    def answer(
        self,
        question: str,
        scan_result,
        intelligence_result,
        graph_result,
        session_id: Optional[str] = None,
        include_history: bool = True,
        max_context_items: int = 20,
        include_llm_orchestration: bool = False,
    ) -> ChatAnswer:
        normalized_question = (question or "").strip()
        if not normalized_question:
            raise ValueError("Question must not be empty")

        # ── Phase 10E.1: Natural chat routing ────────────────────
        history = chat_memory.get_history(session_id) if session_id and include_history else []
        route = self._message_router.classify(normalized_question, history)

        if route.route == "casual":
            answer = self._casual_composer.compose(normalized_question, intent=route.intent)
            self._store_in_memory(session_id, include_history, normalized_question, answer, "casual")
            return answer

        if route.route == "unsupported":
            answer = self._casual_composer.compose_unsupported()
            self._store_in_memory(session_id, include_history, normalized_question, answer, "unsupported")
            return answer

        if route.route == "clarification":
            if not history:
                answer = self._casual_composer.compose_clarification_fallback()
                self._store_in_memory(session_id, include_history, normalized_question, answer, "casual")
                return answer
            # Has history — fall through to repo pipeline to resolve with context
        # ── End Phase 10E.1 routing ──────────────────────────────

        # history already fetched above in routing block
        intent = self._classify_with_memory(normalized_question, history)
        logger.info("Chat intent classified", extra={"session_id": session_id, "intent": intent.intent})

        prd_result = None
        test_gap_result = None
        onboarding_report = None
        repo_index = None
        purpose = self._purpose_extractor.extract(getattr(scan_result, "contents", {}) or {}, intelligence_result)

        try:
            prd_result = PRDEngine().generate(scan_result, intelligence_result, graph_result, session_id)
        except Exception as exc:
            logger.warning("PRD generation unavailable for chat context: %s", exc)

        if intent.intent in {"test_gap_question", "risk_analysis", "what_remaining", "onboarding_question"}:
            try:
                test_gap_result = TestGapDetector().detect(
                    session_id=session_id or getattr(scan_result, "session_id", "chat-session"),
                    scan_result=scan_result,
                    intelligence_result=intelligence_result,
                    graph_result=graph_result,
                )
            except Exception as exc:
                logger.warning("Test gap generation unavailable for chat context: %s", exc)

        if intent.intent in {"onboarding_question", "how_to_modify", "how_to_run"}:
            try:
                onboarding_report = OnboardingGenerator().generate(
                    session_id=session_id or getattr(scan_result, "session_id", "chat-session"),
                    scan_result=scan_result,
                    intelligence_result=intelligence_result,
                    graph_result=graph_result,
                    prd_result=prd_result,
                )
            except Exception as exc:
                logger.warning("Onboarding generation unavailable for chat context: %s", exc)
        canonical = self._canonical_presenter.build(
            session_id=session_id or getattr(scan_result, "session_id", "chat-session"),
            scan_result=scan_result,
            intelligence_result=intelligence_result,
            graph_result=graph_result,
            prd_result=prd_result,
        )

        context_pack = self._context_pack_builder.build(
            session_id=session_id or getattr(scan_result, "session_id", "chat-session"),
            question=normalized_question,
            intent=intent,
            intelligence_result=intelligence_result,
            prd_result=prd_result,
            test_gap_result=test_gap_result,
            onboarding_report=onboarding_report,
            repo_index=repo_index,
            chat_history=history,
            scan_result=scan_result,
            graph_result=graph_result,
            canonical_intelligence=canonical,
        )
        context_pack.project_identity["summary"] = sanitize_chat_text(canonical.product_summary or getattr(purpose, "summary", "") or context_pack.project_identity.get("summary") or "")
        context_pack.project_identity["project_name"] = sanitize_chat_text(canonical.project_name or getattr(purpose, "title", "") or "")
        for evidence in getattr(purpose, "evidence", [])[:3]:
            if evidence not in context_pack.selected_evidence:
                context_pack.selected_evidence.append(evidence)
            if len(context_pack.selected_evidence) >= 8:
                break
        context_pack.selected_evidence = filter_chat_evidence(context_pack.selected_evidence, limit=8)
        context_pack.evidence_map = {f"E{index}": evidence for index, evidence in enumerate(context_pack.selected_evidence[:8], start=1)}

        llm_payload = None
        warnings = list(context_pack.warnings)
        if not include_llm_orchestration:
            if self._llm_client.enabled:
                prompt = self._build_llm_prompt(normalized_question, intent, context_pack)
                try:
                    llm_result = self._llm_client.generate(prompt)
                    if llm_result.get("ok") and llm_result.get("text"):
                        llm_payload = self._parse_llm_output(llm_result["text"])
                        if llm_payload is None:
                            warnings.append("LLM polish unavailable — deterministic answer shown.")
                    else:
                        warnings.append(str(llm_result.get("error") or "LLM polish unavailable — deterministic answer shown."))
                except Exception as exc:
                    warnings.append(f"LLM execution failed: {type(exc).__name__}")
            else:
                warnings.append("LLM disabled; deterministic answer shown.")

        answer = self._answer_composer.compose(
            question=normalized_question,
            intent=intent,
            context_pack=context_pack.model_copy(update={"warnings": warnings}),
            llm_result=llm_payload,
        )
        answer = self._validator.validate(answer, self._pseudo_contexts_for_validation(context_pack))
        identity = self._identity_resolver.resolve(scan_result=scan_result, intelligence_result=intelligence_result)
        answer = self._truth_validator.validate_chat_answer(answer, identity)

        if include_llm_orchestration:
            orchestration = self._orchestrate_answer(normalized_question, intent, context_pack, answer)
            answer.warnings.extend(orchestration["warnings"])
            if orchestration["payload"] is not None:
                answer = self._answer_composer.compose(
                    question=normalized_question,
                    intent=intent,
                    context_pack=context_pack,
                    llm_result=orchestration["payload"],
                )
                answer = self._validator.validate(answer, self._pseudo_contexts_for_validation(context_pack))
                answer = self._truth_validator.validate_chat_answer(answer, identity)

        answer.warnings = list(dict.fromkeys([sanitize_chat_text(item) for item in answer.warnings if sanitize_chat_text(item)]))
        answer.suggested_followups = answer.suggested_followups or build_followups(intent.intent)
        answer = sanitize_chat_answer(answer)

        if not answer.answer.strip() and not answer.sections:
            answer.answer = "I’m here 👋 How can I help you? You can ask about the project or just chat."
            answer.short_answer = "I’m here 👋 How can I help you?"

        if session_id and include_history:
            chat_memory.add_message(
                session_id,
                ChatMessage(
                    role="user",
                    content=normalized_question,
                    summary=normalized_question[:160],
                    intent=intent.intent,
                    referenced_files=[intent.entities.file] if intent.entities.file else [],
                    referenced_apis=[intent.entities.api_path] if intent.entities.api_path else [],
                    referenced_modules=[intent.entities.module] if intent.entities.module else [],
                ),
            )
            chat_memory.add_message(
                session_id,
                ChatMessage(
                    role="assistant",
                    content=answer.answer,
                    summary=answer.short_answer[:160],
                    intent=intent.intent,
                    referenced_files=answer.related_files[:6],
                    referenced_apis=[item.get("path", "") for item in context_pack.relevant_apis[:4] if item.get("path")],
                    referenced_modules=answer.related_nodes[:6],
                ),
            )

        return answer

    def _store_in_memory(
        self,
        session_id: Optional[str],
        include_history: bool,
        question: str,
        answer: ChatAnswer,
        intent_label: str,
    ) -> None:
        """Store a casual / unsupported exchange in chat memory."""
        if session_id and include_history:
            chat_memory.add_message(
                session_id,
                ChatMessage(
                    role="user",
                    content=question,
                    summary=question[:160],
                    intent=intent_label,
                    referenced_files=[],
                    referenced_apis=[],
                    referenced_modules=[],
                ),
            )
            chat_memory.add_message(
                session_id,
                ChatMessage(
                    role="assistant",
                    content=answer.answer,
                    summary=answer.short_answer[:160],
                    intent=intent_label,
                    referenced_files=[],
                    referenced_apis=[],
                    referenced_modules=[],
                ),
            )

    def _classify_with_memory(self, question: str, history: list[ChatMessage]) -> ChatIntentResult:
        intent = self._intent_classifier.classify(question)
        lowered = question.lower()
        if history and any(token in lowered for token in ("one", "that one", "those", "it", "them")):
            last = next((item for item in reversed(history) if item.role == "assistant"), None)
            if last:
                if last.referenced_apis and not intent.entities.api_path:
                    intent.entities.api_path = last.referenced_apis[0]
                    if intent.intent in {"risk_analysis", "general_repo_question"}:
                        intent.intent = "api_explanation"
                        intent.confidence = "medium"
                if last.referenced_modules and not intent.entities.module:
                    intent.entities.module = last.referenced_modules[0]
                if last.referenced_files and not intent.entities.file:
                    intent.entities.file = last.referenced_files[0]
        return intent

    def _build_llm_prompt(self, question: str, intent: ChatIntentResult, context_pack) -> str:
        def to_jsonable(value):
            if hasattr(value, "model_dump"):
                return to_jsonable(value.model_dump())
            if hasattr(value, "__dict__"):
                return to_jsonable(vars(value))
            if isinstance(value, dict):
                return {key: to_jsonable(item) for key, item in value.items()}
            if isinstance(value, list):
                return [to_jsonable(item) for item in value]
            return value

        payload = {
            "question": question,
            "intent": intent.intent,
            "project_identity": context_pack.project_identity,
            "architecture_summary": context_pack.architecture_summary,
            "relevant_apis": context_pack.relevant_apis,
            "relevant_modules": context_pack.relevant_modules,
            "relevant_workflow": context_pack.relevant_workflow,
            "relevant_risks": context_pack.relevant_risks,
            "relevant_test_gaps": context_pack.relevant_test_gaps,
            "relevant_onboarding_steps": context_pack.relevant_onboarding_steps,
            "selected_evidence": [
                {
                    "id": key,
                    "file": value.file,
                    "reason": value.reason,
                    "snippet": value.snippet,
                }
                for key, value in context_pack.evidence_map.items()
            ],
            "forbidden_claims": [
                "invented APIs",
                "invented files",
                "invented modules",
                "unsupported security or compliance claims",
                "raw paths or secrets",
            ],
        }
        return (
            "You are AHAL Conversational Intelligence Engine.\n"
            "Your goal is to behave like ChatGPT: natural, intelligent, context-aware.\n"
            "You are currently in REPOSITORY INTELLIGENCE MODE.\n"
            "Use only the allowed facts below.\n"
            "Return JSON with keys answer, sections, short_answer, suggested_followups, warnings.\n"
            "Each section must include title, content, bullets, evidence_ids.\n"
            "Use uncertainty when evidence is weak. NEVER show JSON errors or backend terminology in the final text.\n"
            f"{json.dumps(to_jsonable(payload), ensure_ascii=True)[:12000]}"
        )

    def _parse_llm_output(self, text: str):
        cleaned_text = text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()
        
        try:
            payload = json.loads(cleaned_text)
        except Exception:
            cleaned = sanitize_chat_text(text, "", max_length=4000)
            if not cleaned:
                return None
            return {
                "answer": cleaned,
                "short_answer": cleaned,
                "sections": [],
                "warnings": [],
                "suggested_followups": [],
            }
        if not isinstance(payload, dict):
            return None
        return payload

    def _orchestrate_answer(self, question: str, intent: ChatIntentResult, context_pack, answer: ChatAnswer) -> dict:
        deterministic_payload = {
            "text": answer.answer,
            "short_answer": answer.short_answer,
            "warnings": answer.warnings,
            "evidence_ids": [f"[E{i}]" for i, _ in enumerate(answer.evidence, start=1)],
            "evidence": [item.model_dump() for item in answer.evidence],
            "related_files": answer.related_files,
            "related_nodes": answer.related_nodes,
            "apis": context_pack.relevant_apis,
            "modules": context_pack.relevant_modules,
        }
        prompt_context = {
            "question": question,
            "intent": intent.intent,
            "fallback_text": answer.answer,
            "must_keep_warnings_in_text": False,
            "must_keep_risks_in_text": False,
        }
        orchestration = self._orchestrator.orchestrate(
            OrchestrationRequest(
                task_type="chat",
                deterministic_payload=deterministic_payload,
                prompt_context=prompt_context,
                max_rounds=1,
                require_citations=bool(answer.evidence),
            )
        )
        if orchestration.fallback_used or not orchestration.text:
            return {"payload": None, "warnings": orchestration.warnings}
        payload = self._parse_llm_output(orchestration.text)
        if payload is None:
            return {"payload": None, "warnings": orchestration.warnings + ["LLM orchestration returned non-JSON output; deterministic answer kept."]}
        return {"payload": payload, "warnings": orchestration.warnings}

    def _pseudo_contexts_for_validation(self, context_pack):
        contexts = []
        for index, evidence in enumerate(context_pack.selected_evidence, start=1):
            contexts.append(type("Context", (), {"evidence": [evidence], "context_id": f"ctx-{index}"})())
        return contexts
