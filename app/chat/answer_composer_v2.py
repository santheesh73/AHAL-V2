from __future__ import annotations

from app.chat.constants import INSUFFICIENT_EVIDENCE_MESSAGE
from app.chat.models import ChatAnswer, ChatAnswerSection, ChatContextPack
from app.chat.utils import build_followups, filter_chat_evidence, sanitize_chat_answer, sanitize_chat_text


class AnswerComposerV2:
    def compose(self, question, intent, context_pack: ChatContextPack, llm_result=None) -> ChatAnswer:
        if llm_result:
            return self._compose_from_llm(intent, context_pack, llm_result)
        return self._compose_deterministic(question, intent, context_pack)

    def _compose_deterministic(self, question, intent, context_pack: ChatContextPack) -> ChatAnswer:
        sections: list[ChatAnswerSection] = []
        evidence = filter_chat_evidence(context_pack.selected_evidence, limit=8)
        evidence_ids = list(context_pack.evidence_map.keys())[: min(3, len(context_pack.evidence_map))]
        confidence = context_pack.confidence
        intent_name = intent.intent if hasattr(intent, "intent") else str(intent)

        if not evidence and not context_pack.relevant_apis and not context_pack.relevant_modules:
            return sanitize_chat_answer(ChatAnswer(
                answer=INSUFFICIENT_EVIDENCE_MESSAGE,
                short_answer="The analyzed evidence does not fully specify this.",
                confidence="low",
                warnings=list(context_pack.warnings),
                insufficient_context=True,
                suggested_followups=build_followups("general_repo_question"),
                intent=intent_name,
                used_llm=False,
                fallback_used=True,
            ))

        direct_answer = self._direct_answer(intent_name, context_pack)
        followup_intent = intent_name
        if intent_name == "project_overview":
            sections.extend(self._overview_sections(context_pack))
        elif intent_name == "api_explanation":
            sections.extend(self._api_sections(context_pack))
        elif intent_name == "architecture_explanation":
            sections.extend(self._architecture_sections(context_pack))
        elif intent_name == "workflow_explanation":
            sections.extend(self._workflow_sections(context_pack))
        elif intent_name == "test_gap_question":
            sections.extend(self._test_gap_sections(context_pack))
        elif intent_name == "onboarding_question":
            sections.extend(self._onboarding_sections(context_pack))
        elif intent_name in {"file_explanation", "module_explanation"}:
            sections.extend(self._module_sections(context_pack, include_files=True))
        elif intent_name == "risk_analysis":
            sections.extend(self._risk_sections(context_pack))
        elif intent_name == "how_to_run":
            sections.extend(self._run_sections(context_pack))
        elif intent_name == "what_remaining":
            sections.extend(self._remaining_sections(context_pack))
        else:
            sections.extend(self._overview_sections(context_pack))
            if intent_name == "general_repo_question":
                followup_intent = "project_overview"

        answer_parts = [direct_answer]
        for section in sections:
            block = [section.title]
            if section.content:
                block.append(section.content)
            if section.bullets:
                block.extend(f"- {item}" for item in section.bullets)
            answer_parts.append("\n".join(block))

        warnings = list(dict.fromkeys([sanitize_chat_text(item) for item in context_pack.warnings if sanitize_chat_text(item)]))
        if not warnings and confidence != "high":
            warnings.append("The analyzed evidence does not fully specify every detail, so some points remain conservative.")

        return sanitize_chat_answer(ChatAnswer(
            answer="\n\n".join(part for part in answer_parts if part).strip(),
            short_answer=direct_answer,
            sections=sections,
            confidence=confidence,
            evidence=evidence,
            related_files=sorted({ev.file for ev in evidence if ev.file}),
            related_nodes=[item["name"] for item in context_pack.relevant_modules[:4] if item.get("name")],
            warnings=warnings,
            insufficient_context=False,
            suggested_followups=build_followups(followup_intent, [item.get("path", "") for item in context_pack.relevant_apis if item.get("path")]),
            intent=intent_name,
            used_llm=False,
            fallback_used=True,
        ))

    def _compose_from_llm(self, intent, context_pack: ChatContextPack, llm_result) -> ChatAnswer:
        sections = []
        for item in llm_result.get("sections", []) or []:
            sections.append(
                ChatAnswerSection(
                    title=sanitize_chat_text(item.get("title"), "Answer"),
                    content=sanitize_chat_text(item.get("content"), ""),
                    bullets=[sanitize_chat_text(bullet) for bullet in item.get("bullets", []) if sanitize_chat_text(bullet)],
                    evidence_ids=[str(ev).replace("[", "").replace("]", "") for ev in item.get("evidence_ids", []) if str(ev).strip()],
                )
            )
        return sanitize_chat_answer(ChatAnswer(
            answer=sanitize_chat_text(llm_result.get("answer"), INSUFFICIENT_EVIDENCE_MESSAGE),
            short_answer=sanitize_chat_text(llm_result.get("short_answer"), ""),
            sections=sections,
            confidence=context_pack.confidence,
            evidence=filter_chat_evidence(context_pack.selected_evidence, limit=8),
            related_files=sorted({ev.file for ev in context_pack.selected_evidence if ev.file}),
            related_nodes=[item["name"] for item in context_pack.relevant_modules[:4] if item.get("name")],
            warnings=[sanitize_chat_text(item) for item in llm_result.get("warnings", []) if sanitize_chat_text(item)],
            insufficient_context=False,
            suggested_followups=[sanitize_chat_text(item) for item in llm_result.get("suggested_followups", []) if sanitize_chat_text(item)],
            intent=intent.intent if hasattr(intent, "intent") else str(intent),
            used_llm=True,
            fallback_used=False,
        ))

    def _direct_answer(self, intent_name: str, context_pack: ChatContextPack) -> str:
        identity_summary = context_pack.project_identity.get("summary") or ""
        architecture_type = context_pack.architecture_summary.get("type", "unknown")
        uncertainty = self._uncertainty_sentence(context_pack)
        if intent_name == "project_goal":
            if identity_summary:
                return identity_summary
            return "The analyzed evidence suggests a developer-facing code intelligence workflow, but the exact business goal is only partially specified."
        if intent_name in {"project_overview", "general_repo_question"}:
            if identity_summary:
                if uncertainty and uncertainty.lower() not in identity_summary.lower():
                    return f"{identity_summary.rstrip('.')}." + f" {uncertainty}"
                return identity_summary
            fallback = "This project appears to include detected APIs, modules, and service structure."
            if uncertainty:
                return f"{fallback} {uncertainty}"
            return fallback
        if intent_name == "what_is_built":
            capabilities = []
            if context_pack.relevant_apis:
                capabilities.append("backend API workflows")
            if context_pack.relevant_modules:
                capabilities.append("structured modules and service layers")
            if context_pack.relevant_onboarding_steps:
                capabilities.append("onboarding guidance")
            if context_pack.relevant_test_gaps:
                capabilities.append("test-gap analysis")
            if capabilities:
                return f"This repo already appears to include {', '.join(capabilities[:4])}."
            return "This repo has detected implementation evidence, but the full built surface is only partially specified."
        if intent_name == "api_explanation":
            if context_pack.relevant_apis:
                api = context_pack.relevant_apis[0]
                return f"{api['method']} {api['path']} appears to be a detected API endpoint in this project."
            return "The analyzed evidence shows API-related structure, but the requested endpoint is not strongly specified."
        if intent_name == "architecture_explanation":
            return f"This project appears to use a {architecture_type} architecture based on the detected frameworks, modules, and entry points."
        if intent_name == "workflow_explanation":
            return "The main workflow can be explained from the detected entry points, APIs, and inferred execution steps."
        if intent_name == "test_gap_question":
            return "The highest-priority gaps are the areas where detected workflows lack corresponding test coverage evidence."
        if intent_name == "onboarding_question":
            return "A new engineer should start with the top entry points, API routes, and workflow-critical modules."
        if intent_name == "how_to_run":
            return "The safest way to run this project is to follow detected setup artifacts and entry points only where evidence exists."
        if intent_name == "risk_analysis":
            return "The main issues are the areas with important behavior but weaker validation, coverage, or workflow certainty."
        if intent_name in {"file_explanation", "module_explanation"}:
            return "The requested file or module can be explained from its detected role, related APIs, and nearby evidence."
        if intent_name == "what_remaining":
            return "Remaining work appears to include unresolved areas that should be confirmed from docs and tests."
        if identity_summary:
            return identity_summary
        return "This project appears to be a codebase with detected APIs, modules, and workflow evidence, but some details remain uncertain."

    def _overview_sections(self, context_pack: ChatContextPack) -> list[ChatAnswerSection]:
        sections: list[ChatAnswerSection] = []
        evidence_ids = list(context_pack.evidence_map.keys())[:3]
        what_it_is_bits = []
        project_type = sanitize_chat_text(context_pack.project_identity.get("project_type"), "")
        frameworks = [sanitize_chat_text(item, "") for item in context_pack.project_identity.get("frameworks", [])[:4] if sanitize_chat_text(item, "")]
        if project_type and project_type != "unknown":
            what_it_is_bits.append(f"Project type: {project_type}.")
        if frameworks:
            what_it_is_bits.append(f"Frameworks: {', '.join(frameworks)}.")
        if what_it_is_bits:
            sections.append(ChatAnswerSection(title="What it is", bullets=what_it_is_bits, evidence_ids=evidence_ids))

        architecture_bits = []
        architecture_type = sanitize_chat_text(context_pack.architecture_summary.get("type"), "")
        if architecture_type and architecture_type != "unknown":
            architecture_bits.append(f"Architecture type: {architecture_type}.")
        entry_points = [item for item in context_pack.architecture_summary.get("entry_points", [])[:3] if item]
        if entry_points:
            architecture_bits.append(f"Entry points: {', '.join(entry_points)}.")
        if context_pack.relevant_modules:
            architecture_bits.append(f"Modules: {', '.join(item['name'] for item in context_pack.relevant_modules[:4])}.")
        if architecture_bits:
            sections.append(ChatAnswerSection(title="Detected architecture", bullets=architecture_bits, evidence_ids=evidence_ids))

        if context_pack.relevant_apis:
            api_bullets = []
            for item in context_pack.relevant_apis[:4]:
                api_bullets.append(f"{item['method']} {item['path']}")
            sections.append(ChatAnswerSection(title="Key API", bullets=api_bullets, evidence_ids=evidence_ids))

        uncertainty = self._uncertainty_sentence(context_pack)
        if uncertainty:
            sections.append(ChatAnswerSection(title="What is uncertain", content=uncertainty, evidence_ids=evidence_ids))
        return sections

    def _api_sections(self, context_pack: ChatContextPack) -> list[ChatAnswerSection]:
        sections = []
        if context_pack.relevant_apis:
            api = context_pack.relevant_apis[0]
            bullets = [
                f"Handler: {api['handler'] or 'Not explicitly detected'}",
                f"Source: {api['file'] or 'Not explicitly detected'}",
                f"Framework: {api['framework'] or 'Not explicitly detected'}",
            ]
            sections.append(ChatAnswerSection(title="Endpoint", content=f"{api['method']} {api['path']}", bullets=bullets, evidence_ids=["E1"]))
        if context_pack.relevant_workflow:
            sections.append(ChatAnswerSection(title="Related Workflow", bullets=[item["action"] for item in context_pack.relevant_workflow[:3]], evidence_ids=["E2"]))
        return sections

    def _architecture_sections(self, context_pack: ChatContextPack) -> list[ChatAnswerSection]:
        bullets = []
        if context_pack.project_identity.get("frameworks"):
            bullets.append(f"Frameworks: {', '.join(context_pack.project_identity['frameworks'][:4])}")
        if context_pack.project_identity.get("databases"):
            bullets.append(f"Databases / storage: {', '.join(context_pack.project_identity['databases'][:4])}")
        if context_pack.relevant_modules:
            bullets.append(f"Important modules: {', '.join(item['name'] for item in context_pack.relevant_modules[:4])}")
        return [ChatAnswerSection(title="Architecture", bullets=bullets, evidence_ids=list(context_pack.evidence_map.keys())[:3])]

    def _workflow_sections(self, context_pack: ChatContextPack) -> list[ChatAnswerSection]:
        bullets = [f"{item['order']}. {item['action']}" for item in context_pack.relevant_workflow[:6]]
        return [ChatAnswerSection(title="Workflow Steps", bullets=bullets, evidence_ids=list(context_pack.evidence_map.keys())[:3])]

    def _test_gap_sections(self, context_pack: ChatContextPack) -> list[ChatAnswerSection]:
        bullets = [
            f"{item['area']}: {item['reason'] or 'Missing targeted test coverage evidence.'}"
            for item in context_pack.relevant_test_gaps[:5]
        ]
        return [ChatAnswerSection(title="Highest-Priority Gaps", bullets=bullets, evidence_ids=list(context_pack.evidence_map.keys())[:3])]

    def _onboarding_sections(self, context_pack: ChatContextPack) -> list[ChatAnswerSection]:
        bullets = [f"{item['title']}: {item['detail']}" for item in context_pack.relevant_onboarding_steps[:5]]
        return [ChatAnswerSection(title="First 30 Minutes", bullets=bullets, evidence_ids=list(context_pack.evidence_map.keys())[:3])]

    def _module_sections(self, context_pack: ChatContextPack, include_files: bool = False) -> list[ChatAnswerSection]:
        bullets = []
        for item in context_pack.relevant_modules[:4]:
            detail = f"{item['name']} ({item['category']})"
            if include_files and item.get("files"):
                detail += f" -> {', '.join(item['files'][:3])}"
            bullets.append(detail)
        return [ChatAnswerSection(title="Related Modules", bullets=bullets, evidence_ids=list(context_pack.evidence_map.keys())[:3])]

    def _risk_sections(self, context_pack: ChatContextPack) -> list[ChatAnswerSection]:
        bullets = []
        for item in context_pack.relevant_risks[:5]:
            label = item.get("title", "Detected risk")
            recommendation = item.get("recommendation", "")
            bullets.append(f"{label}{f' — {recommendation}' if recommendation else ''}")
        return [ChatAnswerSection(title="Detected Risks", bullets=bullets, evidence_ids=list(context_pack.evidence_map.keys())[:3])]

    def _run_sections(self, context_pack: ChatContextPack) -> list[ChatAnswerSection]:
        bullets = []
        entry_points = context_pack.architecture_summary.get("entry_points", [])
        if entry_points:
            bullets.append(f"Start by inspecting entry points such as {', '.join(entry_points[:3])}.")
        if context_pack.project_identity.get("frameworks"):
            bullets.append(f"Detected frameworks: {', '.join(context_pack.project_identity['frameworks'][:4])}.")
        if not bullets:
            bullets.append("The analyzed evidence does not include a reliable run command, so setup should be confirmed from README or manifest files.")
        return [ChatAnswerSection(title="Run Guidance", bullets=bullets, evidence_ids=list(context_pack.evidence_map.keys())[:3])]

    def _remaining_sections(self, context_pack: ChatContextPack) -> list[ChatAnswerSection]:
        bullets = [item.get("title", "") for item in context_pack.relevant_risks[:4] if item.get("title")]
        if not bullets:
            bullets = ["The analyzed evidence does not clearly enumerate remaining work, so unresolved areas should be confirmed from docs and tests."]
        return [ChatAnswerSection(title="Remaining Caveats", bullets=bullets, evidence_ids=list(context_pack.evidence_map.keys())[:3])]

    def _uncertainty_sentence(self, context_pack: ChatContextPack) -> str:
        summary = sanitize_chat_text(context_pack.project_identity.get("summary"), "")
        lowered = summary.lower()
        if "exact product purpose is not fully specified" in lowered:
            return "The exact product purpose is not fully specified in the analyzed evidence."
        if context_pack.confidence != "high":
            return "The exact product purpose is not fully specified in the analyzed evidence."
        return ""
