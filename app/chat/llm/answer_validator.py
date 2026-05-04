"""Validation and safety checks for chat answers."""

from __future__ import annotations

import re

from app.utils.ignored_paths import is_ignored_path
from app.chat.models import ChatAnswer
from app.chat.constants import INSUFFICIENT_EVIDENCE_MESSAGE
from app.chat.utils import sanitize_chat_text

class AnswerValidator:
    def validate(self, answer: ChatAnswer, contexts) -> ChatAnswer:
        valid_ids = self._valid_evidence_ids(contexts)
        has_context = bool(contexts)
        citations = set(re.findall(r"\[E\d+\]", answer.answer or ""))
        warnings = list(answer.warnings)

        if not has_context:
            answer.answer = INSUFFICIENT_EVIDENCE_MESSAGE
            answer.confidence = "low"
            answer.insufficient_context = True
            answer.evidence = []
            answer.warnings = warnings
            return self._sanitize(answer)

        # Ensure evidence list is non-empty if we have an answer
        if not answer.insufficient_context and not answer.evidence and has_context:
            warnings.append("Answer lacked structured evidence; confidence was downgraded.")
            answer.confidence = "low"

        if valid_ids and not citations and answer.answer != INSUFFICIENT_EVIDENCE_MESSAGE:
            if answer.evidence:
                display_ids = sorted(list(valid_ids))[:5]
                answer.answer += f" See evidence {', '.join(display_ids)}."
                citations = set(display_ids)
                warnings.append("Inline citations were repaired by appending evidence references.")
            else:
                warnings.append("Answer lacked evidence citations; confidence was downgraded.")
                answer.confidence = "low"

        unknown = sorted(citations - valid_ids)
        if unknown:
            answer.answer = INSUFFICIENT_EVIDENCE_MESSAGE
            answer.confidence = "low"
            answer.insufficient_context = True
            answer.evidence = []
            warnings.append(f"Answer cited unknown evidence IDs (rejected): {', '.join(unknown)}")
            answer.warnings = warnings
            return self._sanitize(answer)

        forbidden_patterns = ["i assume", "probably", "maybe", "i think", "must be"]
        ans_lower = (answer.answer or "").lower()
        
        has_forbidden = any(p in ans_lower for p in forbidden_patterns)
        
        if "appears to" in ans_lower and not answer.evidence:
            has_forbidden = True
            
        if "likely" in ans_lower and not answer.evidence:
            has_forbidden = True

        if has_forbidden:
            warnings.append("Answer contains speculative language; downgraded confidence.")
            answer.confidence = "low"

        medical_legal_patterns = ("guarantees", "certified", "compliant", "hipaa", "gdpr", "definitely diagnoses", "clinically accurate")
        if any(pattern in ans_lower for pattern in medical_legal_patterns):
            warnings.append("Answer contains potential medical/legal/security claims. AHAL AI provides no such guarantees.")
            answer.confidence = "low"

        if answer.insufficient_context:
            answer.confidence = "low"
            answer.evidence = []

        for section in answer.sections:
            section.title = sanitize_chat_text(section.title, "Answer")
            section.content = sanitize_chat_text(section.content, "")
            section.bullets = [sanitize_chat_text(item) for item in section.bullets if sanitize_chat_text(item)]
            section.evidence_ids = [item.replace("[", "").replace("]", "") for item in section.evidence_ids if item]

        answer.short_answer = sanitize_chat_text(answer.short_answer, answer.answer[:160] if answer.answer else "")
        answer.suggested_followups = [sanitize_chat_text(item) for item in answer.suggested_followups if sanitize_chat_text(item)]
        answer.warnings = warnings
        return self._sanitize(answer)

    def _sanitize(self, answer: ChatAnswer) -> ChatAnswer:
        # Sanitize answer text (coarse check)
        text = answer.answer or ""
        if "node_modules" in text or ".venv" in text or "site-packages" in text or "__pycache__" in text:
            answer.answer = INSUFFICIENT_EVIDENCE_MESSAGE
            answer.confidence = "low"
            answer.insufficient_context = True
            answer.warnings.append("Answer referenced ignored dependency/cache paths.")

        # Sanitize related files
        safe_files = []
        for f in answer.related_files:
            if not is_ignored_path(f):
                safe_files.append(f)
        answer.related_files = safe_files

        # Sanitize related nodes
        safe_nodes = []
        for n in answer.related_nodes:
            path_part = n.split(":", 1)[1] if ":" in n else n
            path_part = path_part.split(":")[0] if n.startswith("function:") else path_part
            if not is_ignored_path(path_part):
                safe_nodes.append(n)
        answer.related_nodes = safe_nodes

        # Sanitize evidence
        safe_evidence = []
        for ev in answer.evidence:
            if getattr(ev, "file", None) and is_ignored_path(ev.file):
                continue
            safe_evidence.append(ev)
        answer.evidence = safe_evidence
        answer.answer = sanitize_chat_text(answer.answer, INSUFFICIENT_EVIDENCE_MESSAGE, max_length=4000)

        return answer

    def _valid_evidence_ids(self, contexts) -> set[str]:
        valid: set[str] = set()
        index = 1
        for item in contexts:
            for _evidence in item.evidence:
                valid.add(f"[E{index}]")
                index += 1
        return valid
