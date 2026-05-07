from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.chat.models import ChatAnswer, ChatAnswerSection, EvidenceReference

from app.utils.ignored_paths import is_ignored_path

_SECRET_PATTERNS = (
    ".env",
    ".env.example",
    "token",
    "secret",
    "credential",
    "private_key",
    "id_rsa",
    "mongodb://",
    "postgresql://",
    "mysql://",
    "redis://",
)

_NOISE_PATTERNS = (
    "ai_hallucination_detection",
    "ecommerce",
    "crm",
    "cms",
    "analytics",
    "devops",
    "chatbot",
    "detected domain signals",
    "normalized unsupported evidence",
    "unknown:",
)

_OVERVIEW_FOLLOWUPS = ["What is built?", "What APIs exist?", "What risks should I review?"]


def sanitize_chat_path(path: str) -> str:
    value = str(path or "").replace("\\", "/").strip()
    if not value:
        return ""
    lowered = value.lower()
    if is_ignored_path(lowered):
        return ""
    if any(token in lowered for token in _SECRET_PATTERNS):
        return ""
    parts = [part for part in value.split("/") if part and part not in {".", ".."}]
    if not parts:
        return ""
    useful = [
        part for part in parts
        if part.lower() not in {"users", "onedrive", "desktop", "downloads", "site-packages", "src", "app", "frontend", "backend"}
    ]
    tail = (useful or parts)[-3:]
    if len(tail) >= 2 and "." in tail[-1]:
        return "/".join(tail[-2:])
    return "/".join(tail)


def sanitize_chat_text(value: object, fallback: str = "", max_length: int | None = 320) -> str:
    text = str(value or "").replace("\x00", " ").strip()
    if not text:
        return fallback
    lowered = text.lower()
    if any(token in lowered for token in _NOISE_PATTERNS):
        return ""
    if any(token in lowered for token in _SECRET_PATTERNS):
        return "Sensitive configuration evidence was omitted."

    text = re.sub(r"[A-Za-z]:\\Users\\[^\\\s]+\\[^,;\n]*", lambda m: sanitize_chat_path(m.group(0)) or "", text)
    text = re.sub(r"/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+){3,}", lambda m: sanitize_chat_path(m.group(0)) or "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if max_length is not None and len(text) > max_length:
        text = f"{text[: max_length - 3].rstrip()}..."
    return text or fallback


def is_weak_domain_signal(value: object) -> bool:
    lowered = str(value or "").strip().lower()
    if not lowered:
        return False
    weak_terms = {
        "ai_hallucination_detection",
        "ecommerce",
        "crm",
        "cms",
        "analytics",
        "devops",
        "chatbot",
    }
    return lowered in weak_terms or lowered.startswith("detected domain signals for ")


def _normalize_compare_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def dedupe_paragraphs(text: str, similarity_threshold: float = 0.90) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", str(text or "").strip()) if part.strip()]
    if not paragraphs:
        return ""

    result: list[str] = []
    normalized_seen: list[str] = []
    for paragraph in paragraphs:
        normalized = _normalize_compare_text(paragraph)
        if not normalized:
            continue
        if any(normalized == existing for existing in normalized_seen):
            continue
        if any(SequenceMatcher(None, normalized, existing).ratio() > similarity_threshold for existing in normalized_seen):
            continue
        normalized_seen.append(normalized)
        result.append(_collapse_repeated_sentences(paragraph))
    return "\n\n".join(result)


def _collapse_repeated_sentences(paragraph: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph.strip())
    collapsed: list[str] = []
    seen: list[str] = []
    for sentence in sentences:
        normalized = _normalize_compare_text(sentence)
        if not normalized:
            continue
        if any(
            normalized == existing or normalized in existing or existing in normalized
            for existing in seen
        ):
            continue
        seen.append(normalized)
        collapsed.append(sentence.strip())
    return " ".join(collapsed).strip()


def dedupe_sections(sections: list[ChatAnswerSection], similarity_threshold: float = 0.90) -> list[ChatAnswerSection]:
    result: list[ChatAnswerSection] = []
    seen_signatures: list[str] = []

    for section in sections:
        title = sanitize_chat_text(section.title, "").strip()
        content = dedupe_paragraphs(str(section.content or ""))
        bullets = []
        seen_bullets: set[str] = set()
        for bullet in section.bullets:
            cleaned = sanitize_chat_text(bullet, "").strip()
            key = _normalize_compare_text(cleaned)
            if not cleaned or key in seen_bullets:
                continue
            seen_bullets.add(key)
            bullets.append(cleaned)
        evidence_ids = []
        seen_evidence_ids: set[str] = set()
        for evidence_id in section.evidence_ids:
            cleaned = sanitize_chat_text(evidence_id, "").replace("[", "").replace("]", "").strip()
            key = cleaned.lower()
            if not cleaned or key in seen_evidence_ids:
                continue
            seen_evidence_ids.add(key)
            evidence_ids.append(cleaned)
        signature = _normalize_compare_text(" | ".join([title, content, *bullets]))
        if not signature:
            continue
        if any(signature == existing for existing in seen_signatures):
            continue
        if any(
            SequenceMatcher(None, signature, existing).ratio() > similarity_threshold
            or signature in existing
            or existing in signature
            for existing in seen_signatures
        ):
            continue
        seen_signatures.append(signature)
        result.append(ChatAnswerSection(title=title or "Answer", content=content, bullets=bullets, evidence_ids=evidence_ids))
    return result


def sanitize_chat_answer(answer: ChatAnswer) -> ChatAnswer:
    sections = dedupe_sections(answer.sections)
    warnings = []
    seen_warnings: set[str] = set()
    for warning in answer.warnings:
        cleaned = sanitize_chat_text(warning, "").strip()
        key = cleaned.lower()
        if not cleaned or key in seen_warnings:
            continue
        seen_warnings.add(key)
        warnings.append(cleaned)
    evidence = filter_chat_evidence(answer.evidence, limit=8)
    followups = []
    seen_followups: set[str] = set()
    for followup in answer.suggested_followups:
        cleaned = sanitize_chat_text(followup, "").strip()
        key = cleaned.lower()
        if not cleaned or key in seen_followups:
            continue
        seen_followups.add(key)
        followups.append(cleaned)
    answer.answer = sanitize_chat_text(dedupe_paragraphs(str(answer.answer or answer.short_answer or "")), answer.short_answer or "", max_length=4000)
    answer.short_answer = sanitize_chat_text(answer.short_answer or answer.answer, answer.answer)
    answer.sections = sections
    answer.warnings = warnings
    answer.evidence = evidence
    answer.related_files = list(dict.fromkeys(sanitize_chat_path(item) for item in answer.related_files if sanitize_chat_path(item)))
    answer.related_nodes = list(dict.fromkeys(sanitize_chat_text(item, "") for item in answer.related_nodes if sanitize_chat_text(item, "")))
    answer.suggested_followups = followups
    return answer


def _evidence_sort_key(evidence: EvidenceReference) -> tuple[int, int, str]:
    label = evidence_display_label(evidence).lower()
    source_type = str(evidence.source_type or "").lower()
    preferred = {
        "readme.md": 0,
        "requirements.txt": 1,
        "package.json": 2,
        "app.py": 3,
        "main.py": 4,
    }
    priority = 8
    for token, rank in preferred.items():
        if token in label:
            priority = rank
            break
    if priority == 8 and label.startswith("/"):
        priority = 5
    if priority == 8 and source_type == "api_endpoint":
        priority = 6
    if priority == 8 and evidence.file:
        priority = 7
    return (priority, 0 if evidence.file else 1, label)


def evidence_display_label(evidence: EvidenceReference) -> str:
    file_label = sanitize_chat_path(evidence.file or "")
    if file_label:
        return file_label
    source_id = sanitize_chat_text(evidence.source_id, "").strip()
    if source_id.startswith("/"):
        return source_id
    return sanitize_chat_path(source_id) or source_id


def filter_chat_evidence(items: list[EvidenceReference], limit: int = 6) -> list[EvidenceReference]:
    result: list[EvidenceReference] = []
    seen: set[str] = set()

    for evidence in sorted(items or [], key=_evidence_sort_key):
        label = evidence_display_label(evidence)
        reason = sanitize_chat_text(evidence.reason, "")
        source_id = sanitize_chat_text(evidence.source_id, "")
        if not label and not reason:
            continue
        if is_weak_domain_signal(label) or is_weak_domain_signal(source_id) or is_weak_domain_signal(reason):
            continue
        if any(is_weak_domain_signal(part.strip()) for part in re.split(r"[,;|]", reason) if part.strip()):
            continue
        key = _normalize_compare_text(label or f"{evidence.source_type}:{source_id}:{reason}")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(evidence)
        if len(result) >= limit:
            break
    return result


def is_sensitive_chat_text(value: object) -> bool:
    lowered = str(value or "").lower()
    return any(token in lowered for token in _SECRET_PATTERNS)


def build_followups(intent: str, api_paths: list[str] | None = None) -> list[str]:
    api_paths = api_paths or []
    common = {
        "project_overview": list(_OVERVIEW_FOLLOWUPS),
        "project_goal": ["What is built?", "What APIs exist?", "What should a new engineer read first?"],
        "what_is_built": ["What APIs exist?", "What remains?", "What is risky?"],
        "what_remaining": ["What is built?", "What tests should be added?", "What is risky?"],
        "api_explanation": ["What does this endpoint connect to?", "What tests cover this API?", "Which API is most risky?"],
        "architecture_explanation": ["How does the main workflow work?", "What APIs exist?", "What is risky?"],
        "workflow_explanation": ["Which APIs are involved?", "What tests should be added?", "What is risky?"],
        "file_explanation": ["How is this file used?", "What module owns this area?", "What should be changed carefully here?"],
        "module_explanation": ["What APIs depend on this module?", "What tests are missing here?", "How should a new engineer modify it?"],
        "risk_analysis": ["What tests should be added?", "Which API is most risky?", "What should a new engineer avoid first?"],
        "test_gap_question": ["Which gap matters most?", "What is risky?", "How should we add tests safely?"],
        "onboarding_question": ["What APIs exist?", "How does the main workflow work?", "What should I avoid changing first?", "What tests should be added?"],
        "change_impact_question": ["What module is affected most?", "What tests should be added?", "What workflow could break?"],
        "how_to_run": ["What does this project do?", "What is built?", "What should a new engineer read first?"],
        "how_to_modify": ["Which module owns this?", "What tests should be added?", "What is risky?"],
        "debugging_help": ["Which API is involved?", "What workflow is related?", "What file should I inspect first?"],
        "general_repo_question": ["What does this project do?", "What APIs exist?", "Explain the architecture."],
    }
    if intent == "general_repo_question":
        selected = list(_OVERVIEW_FOLLOWUPS)
    else:
        selected = list(common.get(intent, common["general_repo_question"]))
    if api_paths and intent not in {"project_overview", "general_repo_question"}:
        selected.insert(0, f"How does {api_paths[0]} work?")
    deduped: list[str] = []
    seen: set[str] = set()
    for item in selected:
        if item.lower() in seen:
            continue
        seen.add(item.lower())
        deduped.append(item)
    return deduped[:4]
