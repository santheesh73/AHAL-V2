from __future__ import annotations

from typing import Any

from app.chat.models import ChatContextPack, ChatIntentResult, ChatMessage, EvidenceReference
from app.chat.utils import filter_chat_evidence, is_weak_domain_signal, sanitize_chat_path, sanitize_chat_text
from app.config import config
from app.context.smart_context_selector import SmartContextSelector
from app.utils.ignored_paths import is_ignored_path


class ChatContextPackBuilder:
    def __init__(self, selector: SmartContextSelector | None = None) -> None:
        self._selector = selector or SmartContextSelector()

    def build(
        self,
        session_id,
        question,
        intent,
        intelligence_result,
        prd_result=None,
        test_gap_result=None,
        onboarding_report=None,
        repo_index=None,
        chat_history=None,
        scan_result=None,
        graph_result=None,
        canonical_intelligence=None,
    ) -> ChatContextPack:
        max_items = max(1, int(config.scanner.chat_max_context_items))
        max_chars = max(1000, int(config.scanner.chat_max_context_chars))
        normalized_intent = intent if isinstance(intent, ChatIntentResult) else ChatIntentResult.model_validate(intent)
        warnings: list[str] = []

        canonical = canonical_intelligence or getattr(prd_result, "canonical_intelligence", None)
        project_identity = {
            "project_type": getattr(canonical, "project_type", getattr(intelligence_result, "project_type", "unknown")),
            "frameworks": list(getattr(getattr(canonical, "tech_stack", None), "frameworks", [])) or [getattr(item, "name", str(item)) for item in getattr(intelligence_result, "frameworks", [])[:6]],
            "databases": list(getattr(getattr(canonical, "tech_stack", None), "databases", [])) or [getattr(item, "name", str(item)) for item in getattr(intelligence_result, "databases", [])[:6]],
            "summary": sanitize_chat_text(getattr(canonical, "product_summary", None) or getattr(prd_result, "executive_summary", None) or getattr(prd_result, "summary", None) or ""),
            "what": sanitize_chat_text(getattr(canonical, "what", None) or ""),
            "why": sanitize_chat_text(getattr(canonical, "why", None) or ""),
            "domain": sanitize_chat_text(getattr(canonical, "product_domain", None) or ""),
            "project_name": sanitize_chat_text(getattr(canonical, "project_name", None) or ""),
        }
        architecture_summary = {
            "type": getattr(getattr(intelligence_result, "architecture", None), "type", "unknown"),
            "confidence": getattr(getattr(intelligence_result, "architecture", None), "confidence", "low"),
            "entry_points": [sanitize_chat_path(getattr(item, "file", str(item))) for item in getattr(intelligence_result, "entry_points", [])[:5]],
        }

        relevant_apis = self._select_apis(canonical, intelligence_result, normalized_intent, max_items)
        relevant_modules = self._select_modules(intelligence_result, normalized_intent, max_items)
        relevant_workflow = self._select_workflow(canonical, intelligence_result, normalized_intent)
        relevant_risks = self._select_risks(canonical, prd_result, intelligence_result, normalized_intent)
        relevant_test_gaps = self._select_test_gaps(test_gap_result, normalized_intent)
        relevant_onboarding_steps = self._select_onboarding(onboarding_report, normalized_intent)
        selected_evidence = self._select_evidence(
            normalized_intent,
            relevant_apis,
            relevant_modules,
            relevant_workflow,
            relevant_risks,
            relevant_test_gaps,
            relevant_onboarding_steps,
            scan_result,
        )
        conversation_memory = self._normalize_history(chat_history)
        selected_evidence = filter_chat_evidence(selected_evidence, limit=8)
        evidence_map = {f"E{index}": evidence for index, evidence in enumerate(selected_evidence, start=1)}

        if scan_result is not None:
            selected_context = self._selector.select(scan_result)
            warnings.extend(selected_context.warnings)
            if not selected_evidence:
                for item in selected_context.files[:4]:
                    ev = self._make_evidence("file", item.path, item.path, item.reason, item.excerpt)
                    if ev:
                        selected_evidence.append(ev)
                        if len(selected_evidence) >= 8:
                            break
                selected_evidence = filter_chat_evidence(selected_evidence, limit=8)
                evidence_map = {f"E{index}": evidence for index, evidence in enumerate(selected_evidence, start=1)}

        confidence = self._confidence_score(normalized_intent.confidence, selected_evidence, relevant_apis, relevant_modules)
        return ChatContextPack(
            session_id=str(session_id),
            question=str(question or "").strip(),
            intent=normalized_intent.intent,
            project_identity=project_identity,
            architecture_summary=architecture_summary,
            relevant_apis=relevant_apis[:max_items],
            relevant_modules=relevant_modules[:max_items],
            relevant_workflow=relevant_workflow[:max_items],
            relevant_risks=relevant_risks[:max_items],
            relevant_test_gaps=relevant_test_gaps[:max_items],
            relevant_onboarding_steps=relevant_onboarding_steps[:max_items],
            selected_evidence=selected_evidence[:8],
            conversation_memory=conversation_memory[-config.scanner.chat_max_history_messages :],
            warnings=list(dict.fromkeys(warnings)),
            confidence=confidence,
            evidence_map=evidence_map,
            max_context_chars=max_chars,
            canonical_intelligence=canonical,
        )

    def _select_apis(self, canonical_intelligence, intelligence_result, intent: ChatIntentResult, max_items: int) -> list[dict[str, Any]]:
        selected = []
        target_path = (intent.entities.api_path or "").lower()
        source_items = list(getattr(canonical_intelligence, "api_surface", []) or []) or list(getattr(intelligence_result, "api_endpoints", []) or [])
        for endpoint in source_items:
            method = str(getattr(endpoint, "method", "GET")).upper()
            path = str(getattr(endpoint, "path", "/"))
            file = sanitize_chat_path(getattr(endpoint, "source", getattr(endpoint, "file", "")))
            if target_path and target_path not in path.lower():
                continue
            selected.append({
                "method": method,
                "path": path,
                "handler": sanitize_chat_text(getattr(endpoint, "handler", getattr(endpoint, "purpose", ""))),
                "file": file,
                "framework": sanitize_chat_text(getattr(endpoint, "framework", getattr(endpoint, "source", ""))),
                "confidence": getattr(endpoint, "confidence", "medium"),
                "evidence": list(getattr(endpoint, "evidence", []) or []),
            })
        if selected:
            return selected[:max_items]
        return [
            {
                "method": str(getattr(endpoint, "method", "GET")).upper(),
                "path": str(getattr(endpoint, "path", "/")),
                "handler": sanitize_chat_text(getattr(endpoint, "handler", "")),
                "file": sanitize_chat_path(getattr(endpoint, "file", "")),
                "framework": sanitize_chat_text(getattr(endpoint, "framework", "")),
                "confidence": getattr(endpoint, "confidence", "medium"),
                "evidence": list(getattr(endpoint, "evidence", []) or []),
            }
            for endpoint in source_items[:max_items]
        ]

    def _select_modules(self, intelligence_result, intent: ChatIntentResult, max_items: int) -> list[dict[str, Any]]:
        selected = []
        target_file = (intent.entities.file or "").lower()
        target_module = (intent.entities.module or "").lower()
        for module in getattr(intelligence_result, "modules", []):
            files = [sanitize_chat_path(path) for path in getattr(module, "files", []) if sanitize_chat_path(path)]
            name = str(getattr(module, "name", "module"))
            if target_file and not any(target_file in str(path).lower() for path in getattr(module, "files", [])):
                if target_file not in name.lower():
                    continue
            if target_module and target_module not in name.lower():
                continue
            selected.append({
                "name": name,
                "category": str(getattr(module, "category", "unknown")),
                "files": files[:5],
                "confidence": getattr(module, "confidence", "medium"),
                "evidence": list(getattr(module, "evidence", []) or []),
            })
        if selected:
            return selected[:max_items]
        return [
            {
                "name": str(getattr(module, "name", "module")),
                "category": str(getattr(module, "category", "unknown")),
                "files": [sanitize_chat_path(path) for path in getattr(module, "files", []) if sanitize_chat_path(path)][:5],
                "confidence": getattr(module, "confidence", "medium"),
                "evidence": list(getattr(module, "evidence", []) or []),
            }
            for module in getattr(intelligence_result, "modules", [])[:max_items]
        ]

    def _select_workflow(self, canonical_intelligence, intelligence_result, intent: ChatIntentResult) -> list[dict[str, Any]]:
        steps = []
        canonical_steps = list(getattr(canonical_intelligence, "workflow", []) or [])
        source_steps = canonical_steps if canonical_steps else list(getattr(getattr(intelligence_result, "workflow", None), "steps", []) or [])
        for step in source_steps[:6]:
            steps.append({
                "order": getattr(step, "step", getattr(step, "order", 0)),
                "action": sanitize_chat_text(getattr(step, "description", getattr(step, "action", "Workflow step"))),
                "source": sanitize_chat_path(getattr(step, "title", getattr(step, "source", ""))),
                "target": sanitize_chat_path(getattr(step, "target", "")),
                "confidence": getattr(step, "confidence", "medium"),
                "evidence": list(getattr(step, "evidence", []) or []),
            })
        return steps

    def _select_risks(self, canonical_intelligence, prd_result, intelligence_result, intent: ChatIntentResult) -> list[dict[str, Any]]:
        items = []
        for risk in list(getattr(canonical_intelligence, "issues", []) or [])[:6]:
            title = sanitize_chat_text(getattr(risk, "title", ""))
            if not title:
                continue
            items.append({
                "title": title,
                "severity": sanitize_chat_text(getattr(risk, "severity", "medium")),
                "recommendation": sanitize_chat_text(getattr(risk, "recommendation", "")),
                "evidence": [],
            })
        if items:
            return items
        source = getattr(prd_result, "issues", None) or []
        for risk in source[:6]:
            title = sanitize_chat_text(getattr(risk, "title", None) or risk.get("title") if isinstance(risk, dict) else "")
            if not title:
                continue
            items.append({
                "title": title,
                "severity": sanitize_chat_text(getattr(risk, "severity", None) or risk.get("severity") if isinstance(risk, dict) else "medium"),
                "recommendation": sanitize_chat_text(getattr(risk, "recommendation", None) or risk.get("recommendation") if isinstance(risk, dict) else ""),
                "evidence": list(getattr(risk, "evidence", []) or risk.get("evidence", []) if isinstance(risk, dict) else []),
            })
        if items:
            return items
        return [
            {
                "title": sanitize_chat_text(item),
                "severity": "medium",
                "recommendation": "",
                "evidence": [],
            }
            for item in getattr(intelligence_result, "warnings", [])[:4]
            if sanitize_chat_text(item)
        ]

    def _select_test_gaps(self, test_gap_result, intent: ChatIntentResult) -> list[dict[str, Any]]:
        if test_gap_result is None:
            return []
        gaps = getattr(test_gap_result, "gaps", None) or getattr(test_gap_result, "items", None) or []
        result = []
        for gap in gaps[:6]:
            if isinstance(gap, dict):
                area = sanitize_chat_text(gap.get("target") or gap.get("area") or gap.get("path") or "Detected area")
                reason = sanitize_chat_text(gap.get("reason") or gap.get("gap") or "")
                test = sanitize_chat_text(gap.get("suggested_test") or gap.get("impact") or "")
                evidence = gap.get("evidence", [])
            else:
                area = sanitize_chat_text(getattr(gap, "target", None) or getattr(gap, "area", None) or "Detected area")
                reason = sanitize_chat_text(getattr(gap, "reason", None) or getattr(gap, "gap", None) or "")
                test = sanitize_chat_text(getattr(gap, "suggested_test", None) or getattr(gap, "impact", None) or "")
                evidence = list(getattr(gap, "evidence", []) or [])
            result.append({"area": area, "reason": reason, "suggested_test": test, "evidence": evidence})
        return result

    def _select_onboarding(self, onboarding_report, intent: ChatIntentResult) -> list[dict[str, Any]]:
        if onboarding_report is None:
            return []
        steps = getattr(onboarding_report, "reading_order", None) or getattr(onboarding_report, "steps", None) or []
        result = []
        for step in steps[:6]:
            if isinstance(step, dict):
                title = sanitize_chat_text(step.get("title") or step.get("path") or "Onboarding step")
                detail = sanitize_chat_text(step.get("description") or step.get("detail") or step.get("reason") or "")
                evidence = step.get("evidence", [])
            else:
                title = sanitize_chat_text(getattr(step, "title", None) or getattr(step, "path", None) or "Onboarding step")
                detail = sanitize_chat_text(getattr(step, "description", None) or getattr(step, "detail", None) or getattr(step, "reason", None) or "")
                evidence = list(getattr(step, "evidence", []) or [])
            result.append({"title": title, "detail": detail, "evidence": evidence})
        return result

    def _select_evidence(
        self,
        intent: ChatIntentResult,
        relevant_apis,
        relevant_modules,
        relevant_workflow,
        relevant_risks,
        relevant_test_gaps,
        relevant_onboarding_steps,
        scan_result,
    ) -> list[EvidenceReference]:
        result: list[EvidenceReference] = []
        seen: set[tuple[str, str, str | None, str]] = set()

        def append_evidence(evidence: EvidenceReference | None) -> None:
            if not evidence:
                return
            key = (evidence.source_type, evidence.source_id, evidence.file, evidence.reason)
            if key in seen:
                return
            seen.add(key)
            result.append(evidence)

        for collection in (
            relevant_apis,
            relevant_modules,
            relevant_workflow,
            relevant_risks,
            relevant_test_gaps,
            relevant_onboarding_steps,
        ):
            for item in collection:
                for evidence in item.get("evidence", [])[:3]:
                    append_evidence(self._normalize_existing_evidence(evidence))
                if len(result) >= 8:
                    return result[:8]

        if scan_result is not None:
            selected = self._selector.select(scan_result)
            for file_item in selected.files[:4]:
                append_evidence(self._make_evidence("file", file_item.path, file_item.path, file_item.reason, file_item.excerpt))
                if len(result) >= 8:
                    break
        return result[:8]

    def _normalize_history(self, history) -> list[ChatMessage]:
        if not history:
            return []
        result: list[ChatMessage] = []
        for item in history:
            try:
                result.append(item if isinstance(item, ChatMessage) else ChatMessage.model_validate(item))
            except Exception:
                continue
        return result

    def _normalize_existing_evidence(self, evidence) -> EvidenceReference | None:
        raw_source_type = getattr(evidence, "source_type", None) if not isinstance(evidence, dict) else evidence.get("source_type", "file")
        raw_source_id = getattr(evidence, "source_id", None) if not isinstance(evidence, dict) else evidence.get("source_id", "")
        file = sanitize_chat_path(getattr(evidence, "file", None) if not isinstance(evidence, dict) else evidence.get("file", ""))
        reason = sanitize_chat_text(getattr(evidence, "reason", None) if not isinstance(evidence, dict) else evidence.get("reason", ""))
        snippet = sanitize_chat_text(getattr(evidence, "snippet", None) if not isinstance(evidence, dict) else evidence.get("snippet", ""))
        source_id = sanitize_chat_text(raw_source_id, "")
        if is_weak_domain_signal(file) or is_weak_domain_signal(source_id) or is_weak_domain_signal(reason):
            return None
        if file and is_ignored_path(file):
            return None
        source_type = str(raw_source_type or "file")
        if source_type == "file" and not file:
            return None
        if source_type != "file" and not source_id and not file:
            return None
        return EvidenceReference(
            source_type=source_type,
            source_id=source_id or file,
            file=file or None,
            reason=reason,
            snippet=snippet or None,
            confidence=str(getattr(evidence, "confidence", None) if not isinstance(evidence, dict) else evidence.get("confidence", "medium") or "medium"),
        )

    def _make_evidence(self, source_type: str, source_id: str, file: str, reason: str, snippet: str = "") -> EvidenceReference | None:
        safe_file = sanitize_chat_path(file)
        safe_source_id = sanitize_chat_text(source_id, "")
        safe_reason = sanitize_chat_text(reason)
        if is_weak_domain_signal(safe_file) or is_weak_domain_signal(safe_source_id) or is_weak_domain_signal(safe_reason):
            return None
        if not (safe_file or safe_source_id) or not safe_reason:
            return None
        return EvidenceReference(
            source_type=source_type,
            source_id=safe_file if source_type == "file" else safe_source_id or safe_file,
            file=safe_file or None,
            reason=safe_reason,
            snippet=sanitize_chat_text(snippet) or None,
            confidence="medium",
        )

    def _confidence_score(self, intent_confidence: str, evidence: list[EvidenceReference], relevant_apis, relevant_modules) -> str:
        if intent_confidence == "high" and len(evidence) >= 2:
            return "high"
        if evidence or relevant_apis or relevant_modules:
            return "medium"
        return "low"
