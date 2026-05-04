from __future__ import annotations

from typing import Any

from app.chat.retrieval.project_purpose_extractor import ProjectPurposeExtractor
from app.code.models import CodeSessionResult
from app.docs.prd_engine import PRDEngine
from app.docs.utils.evidence_sanitizer import sanitize_payload
from app.docs.utils.production_text import clean_list, clean_sentence
from app.graph.graph_engine import KnowledgeGraphEngine
from app.intelligence.consistency_validator import OutputConsistencyValidator
from app.intelligence.intelligence_engine import IntelligenceEngine
from app.intelligence.product_identity import ProductIdentityResolver
from app.models.file_schema import ScanResult
from app.sessions.session_manager import session_manager
from app.utils.ignored_paths import is_ignored_path


_FALLBACK_TEXT = "Insufficient evidence from codebase."


def build_intelligence_schema(session_id: str, session_type: str, scan_result: ScanResult | None) -> dict[str, Any]:
    info = session_manager.get_info(session_id)
    truth_validator = OutputConsistencyValidator()
    identity_resolver = ProductIdentityResolver()
    base = {
        "session_id": session_id,
        "session_type": session_type,
        "status": getattr(info.status, "value", "completed") if info else "completed",
        "project_name": "this project",
        "project_goal": _FALLBACK_TEXT,
        "architecture_style": _FALLBACK_TEXT,
        "key_modules": [],
        "core_features": [],
        "risks": [],
        "summary": {
            "what": _FALLBACK_TEXT,
            "why": _FALLBACK_TEXT,
            "remaining": [],
            "issues": [],
        },
        "technical": {
            "tech_stack": [],
            "api_surface": [],
            "workflow": [],
            "database": [],
        },
        "evidence": [],
        "warnings": clean_list(getattr(info, "warnings", []) if info else []),
        "confidence": getattr(info, "confidence", "low") if info else "low",
    }

    if session_type == "code":
        code_result = session_manager.get_artifact(session_id, "code_result")
        if isinstance(code_result, CodeSessionResult):
            return sanitize_payload(_finalize_schema(_build_code_schema(base, code_result)))
        return sanitize_payload(_finalize_schema(base))

    if scan_result is None:
        return sanitize_payload(_finalize_schema(base))

    intelligence = IntelligenceEngine().analyze(scan_result=scan_result, session_id=session_id, include_llm_explanation=False)
    graph = KnowledgeGraphEngine().build(scan_result=scan_result, intelligence_result=intelligence, session_id=session_id)
    prd = PRDEngine().generate(scan_result=scan_result, intelligence_result=intelligence, graph_result=graph, session_id=session_id)
    purpose = ProjectPurposeExtractor().extract(getattr(scan_result, "contents", {}), intelligence)
    identity = identity_resolver.resolve(scan_result=scan_result, intelligence_result=intelligence)
    prd = truth_validator.validate_prd(prd, identity)
    base["project_name"] = identity.project_name or ("this backend service" if identity.domain == "generic_backend" else "this project")

    project_brief = getattr(prd, "project_brief", None)
    base["project_goal"] = clean_sentence(getattr(getattr(project_brief, "goal", None), "content", purpose.summary or _FALLBACK_TEXT))
    base["architecture_style"] = clean_sentence(getattr(getattr(intelligence, "architecture", None), "type", _FALLBACK_TEXT))
    base["key_modules"] = [
        {
            "name": getattr(module, "name", ""),
            "category": getattr(module, "category", ""),
            "description": clean_sentence(getattr(module, "description", getattr(module, "name", _FALLBACK_TEXT))),
        }
        for module in getattr(prd, "modules", [])[:8]
        if getattr(module, "name", "")
    ]
    base["core_features"] = clean_list(
        list(getattr(purpose, "capabilities", []) or [])
        + [f"{getattr(api, 'method', '').upper()} {getattr(api, 'path', '')}" for api in getattr(intelligence, "api_endpoints", [])[:4]]
    )
    base["risks"] = [
        {
            "title": getattr(risk, "title", ""),
            "severity": getattr(risk, "severity", "low"),
            "recommendation": clean_sentence(getattr(risk, "recommendation", _FALLBACK_TEXT)),
        }
        for risk in getattr(prd, "risks", [])[:8]
        if getattr(risk, "title", "")
    ]
    base["summary"] = {
        "what": clean_sentence(getattr(getattr(project_brief, "what", None), "content", purpose.summary or _FALLBACK_TEXT)),
        "why": clean_sentence(getattr(getattr(project_brief, "why", None), "content", _FALLBACK_TEXT)),
        "remaining": [clean_sentence(getattr(item, "description", getattr(item, "title", _FALLBACK_TEXT))) for item in getattr(project_brief, "remaining", [])[:6]],
        "issues": [clean_sentence(getattr(item, "description", getattr(item, "title", _FALLBACK_TEXT))) for item in getattr(project_brief, "issues", [])[:6]],
    }
    base["technical"] = {
        "tech_stack": clean_list(
            [getattr(item, "name", "") for item in getattr(intelligence, "languages", [])]
            + [getattr(item, "name", "") for item in getattr(intelligence, "frameworks", [])]
        ),
        "api_surface": [
            {
                "method": getattr(api, "method", "").upper(),
                "path": getattr(api, "path", ""),
                "framework": getattr(api, "framework", ""),
            }
            for api in getattr(intelligence, "api_endpoints", [])[:10]
        ],
        "workflow": [
            {
                "order": getattr(step, "order", 0),
                "action": clean_sentence(getattr(step, "action", _FALLBACK_TEXT)),
                "source": getattr(step, "source", ""),
                "target": getattr(step, "target", ""),
            }
            for step in getattr(intelligence.workflow, "steps", [])[:8]
        ],
        "database": clean_list([getattr(db, "name", "") for db in getattr(intelligence, "databases", [])]),
    }
    base["evidence"] = _collect_evidence(intelligence)
    base["warnings"] = clean_list(list(base["warnings"]) + list(getattr(prd, "warnings", []) or []) + list(getattr(intelligence, "warnings", []) or []))
    base["confidence"] = _confidence_label(getattr(intelligence, "confidence_score", 0.0))
    session_manager.set_session_metadata(session_id, confidence=base["confidence"], warnings=base["warnings"])
    return sanitize_payload(_finalize_schema(base))


def _build_code_schema(base: dict[str, Any], code_result: CodeSessionResult) -> dict[str, Any]:
    base["project_goal"] = clean_sentence(code_result.summary)
    base["architecture_style"] = clean_sentence(f"Code snippet analysis for {code_result.language}.")
    base["key_modules"] = [
        {"name": name, "category": "class", "description": clean_sentence(f"Detected class {name}.")}
        for name in code_result.detected_classes[:8]
    ]
    base["core_features"] = clean_list(code_result.detected_functions + code_result.entrypoints)
    base["risks"] = [{"title": issue, "severity": "medium", "recommendation": "Review and validate this potential issue before production use."} for issue in code_result.issues[:6]]
    base["summary"] = {
        "what": clean_sentence(code_result.summary),
        "why": clean_sentence("This session provides quick code intelligence for a single snippet or file."),
        "remaining": clean_list(code_result.suggested_improvements),
        "issues": clean_list(code_result.issues),
    }
    base["technical"] = {
        "tech_stack": clean_list([code_result.language] + code_result.imports),
        "api_surface": [],
        "workflow": [],
        "database": [],
    }
    base["evidence"] = [{"source_id": item.source_id, "reason": clean_sentence(item.reason)} for item in code_result.evidence[:10]]
    base["warnings"] = clean_list(list(base["warnings"]) + list(code_result.warnings))
    base["confidence"] = code_result.confidence
    return base


def _collect_evidence(intelligence) -> list[dict[str, str]]:
    evidence = []
    for collection in (
        getattr(intelligence, "frameworks", []),
        getattr(intelligence, "api_endpoints", []),
        getattr(intelligence, "modules", []),
        getattr(intelligence, "databases", []),
    ):
        for item in collection:
            for ev in getattr(item, "evidence", [])[:2]:
                file_path = getattr(ev, "file", "")
                if file_path and not is_ignored_path(file_path):
                    evidence.append({"file": file_path, "reason": clean_sentence(getattr(ev, "reason", ""))})
            if len(evidence) >= 12:
                return evidence
    return evidence


def _infer_project_name(info, scan_result: ScanResult | None) -> str:
    if info and getattr(info, "source_name", ""):
        source_name = str(info.source_name)
        return source_name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or source_name
    contents = getattr(scan_result, "contents", {}) if scan_result else {}
    if isinstance(contents, dict):
        for path in contents.keys():
            if "readme" in str(path).lower():
                return "Project"
    return "Project"


def _confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _finalize_schema(value):
    if isinstance(value, dict):
        finalized = {}
        for key, item in value.items():
            finalized[str(key)] = _finalize_schema(item)
        return finalized
    if isinstance(value, list):
        return [_finalize_schema(item) for item in value if _finalize_schema(item) not in (None, "")]
    if value is None:
        return ""
    if isinstance(value, str):
        cleaned = clean_sentence(value) if value and value in {"unknown", "Unknown"} else str(value)
        lowered = cleaned.lower()
        if "magicmock" in lowered or "type='" in lowered or "confidence='" in lowered:
            return _FALLBACK_TEXT
        if is_ignored_path(cleaned):
            return ""
        return cleaned
    return value
