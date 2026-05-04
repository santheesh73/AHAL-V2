from __future__ import annotations

import re

from app.docs.diff_models import APIDiffItem, ModuleDiffItem, PRDDiffResult, SectionDiff
from app.docs.models import PRDResult
from app.docs.utils.production_text import clean_list, clean_sentence, join_capabilities


class PRDDiffEngine:
    def compare(
        self,
        base: PRDResult,
        target: PRDResult,
        base_session_id: str,
        target_session_id: str,
    ) -> PRDDiffResult:
        goal_diff = self._compare_goal(base, target)
        architecture_diff = self._compare_architecture(base, target)
        tech_stack_diff = self._compare_text_sections(base.tech_stack.content, target.tech_stack.content, "Tech stack")
        module_diff = self._compare_modules(base, target)
        api_diff = self._compare_apis(base, target)
        workflow_diff = self._compare_workflow(base, target)
        database_diff = self._compare_text_sections(base.databases.content, target.databases.content, "Database/storage")
        risk_diff = self._compare_risks(base, target)
        remaining_diff = self._compare_remaining(base, target)
        review_focus = self._suggest_review_focus(api_diff, module_diff, architecture_diff, database_diff, risk_diff)
        warnings = self._warning_delta(base, target)
        evidence_count = (
            len(module_diff)
            + len(api_diff)
            + len(review_focus)
            + len(goal_diff.added)
            + len(goal_diff.removed)
            + len(architecture_diff.changed)
            + len(risk_diff.added)
            + len(remaining_diff.changed)
        )
        confidence = self._overall_confidence(api_diff, module_diff, architecture_diff, risk_diff, database_diff)
        summary = self._summary(goal_diff, architecture_diff, api_diff, module_diff, risk_diff)
        return PRDDiffResult(
            base_session_id=base_session_id,
            target_session_id=target_session_id,
            summary=summary,
            project_goal_diff=goal_diff,
            architecture_diff=architecture_diff,
            tech_stack_diff=tech_stack_diff,
            module_diff=module_diff,
            api_diff=api_diff,
            workflow_diff=workflow_diff,
            database_diff=database_diff,
            risk_diff=risk_diff,
            remaining_diff=remaining_diff,
            suggested_review_focus=review_focus,
            warnings=warnings,
            confidence=confidence,
            evidence_count=evidence_count,
        )

    def to_markdown(self, diff: PRDDiffResult) -> str:
        lines = [
            "# PRD Architecture Diff",
            "",
            "## Summary",
            diff.summary,
            "",
            "## Architecture Changes",
            diff.architecture_diff.summary,
            "",
            "## API Changes",
        ]
        if diff.api_diff:
            for item in diff.api_diff:
                lines.append(f"- `{item.change_type}` `{item.method} {item.path}`: {item.summary}")
        else:
            lines.append("- No API changes detected.")
        lines.extend(["", "## Module Changes"])
        if diff.module_diff:
            for item in diff.module_diff:
                lines.append(f"- `{item.change_type}` `{item.name}` ({item.category}): {item.summary}")
        else:
            lines.append("- No module changes detected.")
        lines.extend([
            "",
            "## Workflow Changes",
            diff.workflow_diff.summary,
            "",
            "## Risk Changes",
            diff.risk_diff.summary,
            "",
            "## Suggested Review Focus",
        ])
        if diff.suggested_review_focus:
            for item in diff.suggested_review_focus:
                lines.append(f"- {item}")
        else:
            lines.append("- No special review focus detected.")
        return "\n".join(lines).strip() + "\n"

    def _compare_goal(self, base: PRDResult, target: PRDResult) -> SectionDiff:
        base_goal = self._brief_text(base, "goal")
        target_goal = self._brief_text(target, "goal")
        return self._sentence_diff(base_goal, target_goal, "Project goal")

    def _compare_architecture(self, base: PRDResult, target: PRDResult) -> SectionDiff:
        parts_base = [base.project_type, base.architecture.content]
        parts_target = [target.project_type, target.architecture.content]
        diff = self._sentence_diff(" ".join(parts_base), " ".join(parts_target), "Architecture")
        return diff

    def _compare_workflow(self, base: PRDResult, target: PRDResult) -> SectionDiff:
        base_rows = [f"{step.order}. {step.source} -> {step.action} -> {step.target or ''}".strip() for step in base.workflow]
        target_rows = [f"{step.order}. {step.source} -> {step.action} -> {step.target or ''}".strip() for step in target.workflow]
        return self._set_diff(base_rows, target_rows, "Workflow")

    def _compare_risks(self, base: PRDResult, target: PRDResult) -> SectionDiff:
        base_rows = [f"{risk.severity}:{risk.title}" for risk in base.risks]
        target_rows = [f"{risk.severity}:{risk.title}" for risk in target.risks]
        return self._set_diff(base_rows, target_rows, "Risk")

    def _compare_remaining(self, base: PRDResult, target: PRDResult) -> SectionDiff:
        base_rows = [item.title for item in getattr(getattr(base, "project_brief", None), "remaining", [])]
        target_rows = [item.title for item in getattr(getattr(target, "project_brief", None), "remaining", [])]
        diff = self._set_diff(base_rows, target_rows, "Remaining work")
        maybe_completed = [f"Possibly completed: {item}" for item in diff.removed]
        new_gaps = [f"New gap detected: {item}" for item in diff.added]
        diff.changed = clean_list(diff.changed + maybe_completed + new_gaps, max_items=20)
        diff.summary = self._section_summary("Remaining work", diff)
        return diff

    def _compare_text_sections(self, base_text: str, target_text: str, label: str) -> SectionDiff:
        return self._sentence_diff(base_text, target_text, label)

    def _compare_modules(self, base: PRDResult, target: PRDResult) -> list[ModuleDiffItem]:
        base_map = {item.name.lower(): item for item in base.modules}
        target_map = {item.name.lower(): item for item in target.modules}
        items: list[ModuleDiffItem] = []
        for key in sorted(set(base_map) | set(target_map)):
            base_item = base_map.get(key)
            target_item = target_map.get(key)
            if base_item and not target_item:
                items.append(self._module_item(base_item.name, "removed", base_item.category, base_item.description))
            elif target_item and not base_item:
                items.append(self._module_item(target_item.name, "added", target_item.category, target_item.description))
            elif base_item and target_item:
                changed = (
                    self._normalize(base_item.category) != self._normalize(target_item.category)
                    or self._normalize(base_item.description) != self._normalize(target_item.description)
                )
                if changed:
                    items.append(self._module_item(target_item.name, "modified", target_item.category, target_item.description))
        return items

    def _compare_apis(self, base: PRDResult, target: PRDResult) -> list[APIDiffItem]:
        base_map = {(item.method.upper(), item.path): item for item in base.api_endpoints}
        target_map = {(item.method.upper(), item.path): item for item in target.api_endpoints}
        items: list[APIDiffItem] = []
        for key in sorted(set(base_map) | set(target_map)):
            base_item = base_map.get(key)
            target_item = target_map.get(key)
            method, path = key
            if base_item and not target_item:
                items.append(self._api_item(method, path, "removed", "Endpoint removed from the API surface."))
            elif target_item and not base_item:
                items.append(self._api_item(method, path, "added", "Endpoint added to the API surface."))
            elif base_item and target_item:
                changed = self._normalize(base_item.description) != self._normalize(target_item.description)
                if changed:
                    items.append(self._api_item(method, path, "modified", "Endpoint behavior or description changed."))
        return items

    def _sentence_diff(self, base_text: str, target_text: str, label: str) -> SectionDiff:
        base_rows = self._sentences(base_text)
        target_rows = self._sentences(target_text)
        return self._set_diff(base_rows, target_rows, label)

    def _set_diff(self, base_rows: list[str], target_rows: list[str], label: str) -> SectionDiff:
        base_set = {self._normalize(item): item for item in base_rows if self._normalize(item)}
        target_set = {self._normalize(item): item for item in target_rows if self._normalize(item)}
        added = [target_set[key] for key in sorted(set(target_set) - set(base_set))]
        removed = [base_set[key] for key in sorted(set(base_set) - set(target_set))]
        unchanged = len(set(base_set) & set(target_set))
        changed = []
        if not added and not removed and unchanged:
            summary = f"{label} is largely unchanged between the two versions."
            confidence = "high"
        elif added or removed:
            changed = [f"{label} content changed materially between versions."]
            summary = self._section_summary(label, added=added, removed=removed, unchanged=unchanged)
            confidence = "high" if unchanged or added or removed else "medium"
        else:
            summary = f"{label} differences could not be established confidently."
            confidence = "low"
        return SectionDiff(
            added=clean_list(added, max_items=20),
            removed=clean_list(removed, max_items=20),
            changed=clean_list(changed, max_items=20),
            unchanged_count=unchanged,
            summary=clean_sentence(summary),
            confidence=confidence,
        )

    def _section_summary(self, label: str, diff: SectionDiff | None = None, added=None, removed=None, unchanged: int = 0) -> str:
        if diff is not None:
            added = diff.added
            removed = diff.removed
            unchanged = diff.unchanged_count
        added = added or []
        removed = removed or []
        parts = []
        if added:
            parts.append(f"added {len(added)} item{'s' if len(added) != 1 else ''}")
        if removed:
            parts.append(f"removed {len(removed)} item{'s' if len(removed) != 1 else ''}")
        if unchanged:
            parts.append(f"kept {unchanged} item{'s' if unchanged != 1 else ''} unchanged")
        if not parts:
            return f"{label} is unchanged."
        return f"{label} {', '.join(parts)}."

    def _warning_delta(self, base: PRDResult, target: PRDResult) -> list[str]:
        base_warnings = {self._normalize(item): item for item in base.warnings}
        target_warnings = {self._normalize(item): item for item in target.warnings}
        added = [f"New warning: {target_warnings[key]}" for key in sorted(set(target_warnings) - set(base_warnings))]
        removed = [f"Resolved warning: {base_warnings[key]}" for key in sorted(set(base_warnings) - set(target_warnings))]
        return clean_list(added + removed, max_items=20)

    def _suggest_review_focus(
        self,
        api_diff: list[APIDiffItem],
        module_diff: list[ModuleDiffItem],
        architecture_diff: SectionDiff,
        database_diff: SectionDiff,
        risk_diff: SectionDiff,
    ) -> list[str]:
        focus = []
        if api_diff:
            focus.append("Review API compatibility and update integration tests.")
        if database_diff.added or database_diff.removed or any("database" in item.category.lower() for item in module_diff):
            focus.append("Review migrations, schema compatibility, and data access tests.")
        if any("auth" in item.category.lower() for item in module_diff):
            focus.append("Review authorization boundaries and token/session behavior.")
        if architecture_diff.added or architecture_diff.removed or architecture_diff.changed:
            focus.append("Review end-to-end workflow and regression tests.")
        if any(item.change_type in {"added", "removed"} and item.category.lower() in {"config", "service"} for item in module_diff):
            focus.append("Review dependency compatibility and deployment impact.")
        if any(item.startswith("high:") or "high" in item.lower() for item in risk_diff.added + risk_diff.changed):
            focus.append("Address newly introduced high-risk gaps.")
        return clean_list(focus, max_items=10)

    def _overall_confidence(
        self,
        api_diff: list[APIDiffItem],
        module_diff: list[ModuleDiffItem],
        architecture_diff: SectionDiff,
        risk_diff: SectionDiff,
        database_diff: SectionDiff,
    ) -> str:
        if api_diff or module_diff or architecture_diff.added or architecture_diff.removed or database_diff.added or database_diff.removed:
            return "high"
        if risk_diff.added or risk_diff.removed or architecture_diff.changed:
            return "medium"
        return "low"

    def _summary(
        self,
        goal_diff: SectionDiff,
        architecture_diff: SectionDiff,
        api_diff: list[APIDiffItem],
        module_diff: list[ModuleDiffItem],
        risk_diff: SectionDiff,
    ) -> str:
        parts = []
        if goal_diff.added or goal_diff.removed or goal_diff.changed:
            parts.append("Project direction changed.")
        if architecture_diff.added or architecture_diff.removed or architecture_diff.changed:
            parts.append("Architecture changed.")
        if api_diff:
            parts.append(f"API surface changed by {len(api_diff)} endpoint update{'s' if len(api_diff) != 1 else ''}.")
        if module_diff:
            parts.append(f"Module structure changed by {len(module_diff)} module update{'s' if len(module_diff) != 1 else ''}.")
        if risk_diff.added or risk_diff.removed:
            parts.append("Risk profile changed.")
        if not parts:
            parts.append("The two PRD versions are largely unchanged.")
        return clean_sentence(" ".join(parts))

    def _module_item(self, name: str, change_type: str, category: str, description: str) -> ModuleDiffItem:
        lowered = category.lower()
        risk = "high" if lowered in {"api", "service", "database", "auth"} and change_type == "removed" else "medium" if lowered in {"api", "service", "database", "auth"} else "low"
        return ModuleDiffItem(
            name=name,
            change_type=change_type,
            category=category,
            summary=clean_sentence(description or f"Module {change_type}."),
            risk_level=risk,
        )

    def _api_item(self, method: str, path: str, change_type: str, summary: str) -> APIDiffItem:
        lower_path = path.lower()
        if any(token in lower_path for token in ["/health", "/status", "/docs"]):
            risk = "low"
        elif change_type == "removed":
            risk = "high"
        elif change_type == "modified":
            risk = "high"
        else:
            risk = "medium"
        return APIDiffItem(method=method, path=path, change_type=change_type, summary=clean_sentence(summary), risk_level=risk)

    def _brief_text(self, prd: PRDResult, field_name: str) -> str:
        brief = getattr(prd, "project_brief", None)
        section = getattr(brief, field_name, None) if brief else None
        return getattr(section, "content", "") or ""

    def _sentences(self, text: str) -> list[str]:
        cleaned = clean_sentence(text or "")
        if cleaned == "Insufficient evidence from codebase.":
            return []
        return clean_list([item.strip() for item in re.split(r"(?<=[.!?])\s+", cleaned) if item.strip()], max_items=20)

    def _normalize(self, value: str) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text
