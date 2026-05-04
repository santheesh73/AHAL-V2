from __future__ import annotations

import json

from app.config import config
from app.llm_orchestration.models import OrchestrationResult
from app.llm_orchestration.providers import GeminiProvider, LLMProvider, LocalFallbackProvider
from app.llm_orchestration.validators import OrchestrationValidator
from app.storage.serialization import sanitize_for_storage


class LLMOrchestrator:
    def __init__(
        self,
        primary_provider: LLMProvider | None = None,
        critic_provider: LLMProvider | None = None,
        validator: OrchestrationValidator | None = None,
    ) -> None:
        self._primary_provider = primary_provider or self._provider_from_name(config.scanner.llm_primary_provider)
        self._critic_provider = critic_provider or self._provider_from_name(config.scanner.llm_critic_provider)
        self._validator = validator or OrchestrationValidator()

    def orchestrate(self, request) -> OrchestrationResult:
        fallback_text = self._fallback_text(request)
        if not config.scanner.llm_orchestration_enabled:
            return self._fallback_result("disabled", fallback_text, ["LLM orchestration disabled; returned deterministic answer."])

        prompt_payload = sanitize_for_storage(dict(getattr(request, "deterministic_payload", {}) or {}))
        prompt_context = sanitize_for_storage(dict(getattr(request, "prompt_context", {}) or {}))
        primary_prompt = self._primary_prompt(request.task_type, prompt_payload, prompt_context)
        critic_prompt_schema = {"type": "object", "properties": {"passed": {"type": "boolean"}, "issues": {"type": "array", "items": {"type": "string"}}}}

        try:
            primary_result = self._primary_provider.generate(primary_prompt)
        except TimeoutError:
            return self._fallback_result(getattr(self._primary_provider, "provider_name", "unknown"), fallback_text, ["Primary LLM timed out; returned deterministic answer."])
        except Exception:
            return self._fallback_result(getattr(self._primary_provider, "provider_name", "unknown"), fallback_text, ["Primary LLM failed; returned deterministic answer."])

        candidate_text = str(primary_result.get("text", "") or "").strip()
        if not candidate_text:
            return self._fallback_result(primary_result.get("provider", getattr(self._primary_provider, "provider_name", "unknown")), fallback_text, ["Primary LLM returned empty output; returned deterministic answer."])

        critic_result = {"ok": True, "structured_output": {"passed": True, "issues": []}, "provider": getattr(self._critic_provider, "provider_name", "unknown")}
        try:
            critic_prompt = self._critic_prompt(request.task_type, prompt_payload, candidate_text)
            provider_result = self._critic_provider.generate(critic_prompt, schema=critic_prompt_schema)
            critic_result = {
                "ok": provider_result.get("ok", True),
                "structured_output": provider_result.get("structured_output") or self._critic_structured_output(provider_result.get("text", "")),
                "provider": provider_result.get("provider", getattr(self._critic_provider, "provider_name", "unknown")),
            }
        except Exception:
            critic_result = {"ok": False, "structured_output": {"passed": False, "issues": ["Critic provider error."]}, "provider": getattr(self._critic_provider, "provider_name", "unknown")}

        validation_passed, validation_warnings = self._validator.validate(request, candidate_text, critic_result)
        critic_passed = bool((critic_result.get("structured_output") or {}).get("passed", False))
        if not validation_passed or not critic_passed:
            warnings = list(validation_warnings)
            warnings.extend((critic_result.get("structured_output") or {}).get("issues", []))
            if not warnings:
                warnings.append("Orchestration validation failed; returned deterministic answer.")
            return OrchestrationResult(
                ok=False,
                text=fallback_text,
                structured_output=None,
                provider_used=primary_result.get("provider", getattr(self._primary_provider, "provider_name", "unknown")),
                critic_passed=critic_passed,
                validation_passed=validation_passed,
                fallback_used=True,
                warnings=warnings,
            )

        return OrchestrationResult(
            ok=True,
            text=candidate_text,
            structured_output=primary_result.get("structured_output"),
            provider_used=primary_result.get("provider", getattr(self._primary_provider, "provider_name", "unknown")),
            critic_passed=True,
            validation_passed=True,
            fallback_used=False,
            warnings=validation_warnings,
        )

    def _provider_from_name(self, name: str) -> LLMProvider:
        normalized = str(name or "gemini").strip().lower()
        if normalized == "gemini":
            return GeminiProvider()
        return LocalFallbackProvider()

    def _fallback_text(self, request) -> str:
        prompt_context = dict(getattr(request, "prompt_context", {}) or {})
        deterministic = dict(getattr(request, "deterministic_payload", {}) or {})
        return str(prompt_context.get("fallback_text") or deterministic.get("text") or "")

    def _fallback_result(self, provider_name: str, fallback_text: str, warnings: list[str]) -> OrchestrationResult:
        return OrchestrationResult(
            ok=False,
            text=fallback_text,
            structured_output=None,
            provider_used=provider_name,
            critic_passed=False,
            validation_passed=False,
            fallback_used=True,
            warnings=warnings,
        )

    def _primary_prompt(self, task_type: str, deterministic_payload: dict, prompt_context: dict) -> str:
        return (
            f"You are the primary narration model for AHAL task `{task_type}`.\n"
            "Rewrite the deterministic answer for clarity without inventing facts, APIs, modules, databases, frameworks, risks, or warnings.\n"
            "Preserve citations exactly when present.\n"
            f"Deterministic payload:\n{json.dumps(deterministic_payload, ensure_ascii=True)[:6000]}\n"
            f"Prompt context:\n{json.dumps(prompt_context, ensure_ascii=True)[:4000]}"
        )

    def _critic_prompt(self, task_type: str, deterministic_payload: dict, candidate_text: str) -> str:
        return (
            f"You are the critic model for AHAL task `{task_type}`.\n"
            "Return JSON with fields passed:boolean and issues:string[]. Reject unsupported claims, invented facts, dropped citations, dropped warnings, and hallucinated technologies.\n"
            f"Deterministic payload:\n{json.dumps(deterministic_payload, ensure_ascii=True)[:6000]}\n"
            f"Candidate text:\n{candidate_text[:4000]}"
        )

    def _critic_structured_output(self, text: str) -> dict:
        lowered = str(text or "").lower()
        if '"passed": false' in lowered or "fail" in lowered or "reject" in lowered:
            return {"passed": False, "issues": [str(text or "").strip() or "Critic rejected the output."]}
        return {"passed": True, "issues": []}
