import logging
from app.config import config
from app.docs.models import PRDResult
from app.docs.llm.prd_prompt_builder import PRDPromptBuilder

logger = logging.getLogger("ahal.docs.polish")

class PRDPolishService:
    def __init__(self):
        self.prompt_builder = PRDPromptBuilder()

    def polish(self, prd_result: PRDResult, markdown: str) -> tuple[str, list[str]]:
        warnings = []
        if not config.scanner.llm_enabled:
            warnings.append("LLM disabled; returned deterministic PRD.")
            return markdown, warnings
            
        api_key = config.scanner.gemini_api_key
        if not api_key:
            warnings.append("LLM unavailable: Gemini API key missing; returned deterministic PRD.")
            return markdown, warnings

        from app.intelligence.llm.gemini_client import GeminiClient
        client = GeminiClient()
        
        prompt = self.prompt_builder.build_polish_prompt(prd_result)
        
        try:
            polished_md = client.generate(prompt, model=config.scanner.llm_model, timeout=config.scanner.llm_timeout_seconds)
            if not polished_md:
                warnings.append("LLM unavailable: Gemini API call failed; returned deterministic PRD.")
                return markdown, warnings
                
            is_valid, validation_warnings = self._validate_polished(prd_result, polished_md)
            if not is_valid:
                warnings.append("LLM polished PRD failed validation; returned deterministic PRD.")
                warnings.extend(validation_warnings)
                return markdown, warnings
                
            return polished_md, []
        except Exception as e:
            logger.error("Error during PRD polishing: %s", e)
            warnings.append("LLM unavailable: Gemini API call failed; returned deterministic PRD.")
            return markdown, warnings

    def _validate_polished(self, prd_result: PRDResult, polished_md: str) -> tuple[bool, list[str]]:
        warnings = []
        lower_md = polished_md.lower()
        
        # 1. Must contain all required sections
        required_sections = [
            "project overview", "architecture", "tech stack", "core modules",
            "api surface", "workflow", "database", "setup", "risks", "evidence summary"
        ]
        for sec in required_sections:
            if sec not in lower_md:
                warnings.append(f"Missing required section: {sec}")
                return False, warnings

        # 2. Must not contain ignored paths
        ignored_paths = ["node_modules", ".venv", "site-packages", "__pycache__", "pip/_vendor"]
        for path in ignored_paths:
            if path in lower_md:
                warnings.append(f"Contains ignored path: {path}")
                return False, warnings

        # 3. Must not contain raw model repr
        bad_reprs = ["type='", "confidence='", "reasoning=[", "evidence=[", "evidenceitem(", "architectureresult("]
        for r in bad_reprs:
            if r in lower_md:
                warnings.append(f"Contains raw model repr: {r}")
                return False, warnings

        # 4. Must not introduce obvious unsupported sections
        unsupported = ["new features", "future roadmap", "market analysis", "revenue model"]
        try:
            orig_lower = prd_result.model_dump_json().lower()
        except AttributeError:
            orig_lower = prd_result.json().lower()
            
        for u in unsupported:
            if u in lower_md and u not in orig_lower:
                warnings.append(f"Invented unsupported section: {u}")
                return False, warnings

        # 5. Preserve known API endpoints
        if prd_result.api_endpoints:
            for api in prd_result.api_endpoints:
                sig = f"{api.method} {api.path}".lower()
                if sig not in lower_md:
                    warnings.append(f"Missing known API endpoint: {sig}")
                    return False, warnings
                    
        # 6. Preserve insufficient evidence message
        # If deterministic had empty arrays, the phrase usually gets injected
        if not prd_result.modules or not prd_result.api_endpoints or not prd_result.workflow:
            if "insufficient evidence" not in lower_md:
                warnings.append("Missing insufficient evidence statement")
                return False, warnings

        return True, warnings
