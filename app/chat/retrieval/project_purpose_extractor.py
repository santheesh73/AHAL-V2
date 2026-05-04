"""Project purpose extraction backed by the universal product identity resolver."""

from __future__ import annotations

from app.chat.models import EvidenceReference, ProjectPurpose
from app.docs.utils.production_text import clean_list
from app.intelligence.product_identity import ProductIdentityResolver
from app.utils.evidence_types import normalize_evidence_source_type


class ProjectPurposeExtractor:
    """Deterministically extracts purpose with conservative domain confidence."""

    def __init__(self):
        self._resolver = ProductIdentityResolver()

    def extract(self, contents: dict[str, bytes], intelligence_result=None) -> ProjectPurpose:
        identity = self._resolver.resolve(contents=contents, intelligence_result=intelligence_result)
        purpose = ProjectPurpose(
            title=identity.project_name,
            domain=identity.domain,
            summary=identity.purpose_summary,
            capabilities=self._capabilities(identity.domain, intelligence_result),
            warnings=list(identity.warnings),
            confidence=identity.domain_confidence,
        )
        purpose.evidence = [
            self._to_evidence_reference(item)
            for item in identity.evidence
        ]
        for dep in getattr(intelligence_result, "dependencies", []) or []:
            dep_name = str(getattr(dep, "name", "") or "").strip().lower()
            if not dep_name:
                continue
            if dep_name in {"openai", "langchain", "beautifulsoup4", "bs4", "requests", "playwright", "selenium"}:
                purpose.evidence.append(
                    EvidenceReference(
                        source_type="framework",
                        source_id=f"dep:{dep_name}",
                        file=getattr(dep, "source_file", None),
                        reason=f"Dependency detected: {dep_name}",
                        snippet=None,
                        confidence=getattr(dep, "confidence", "medium"),
                    )
                )
        return purpose

    def _capabilities(self, domain: str | None, intelligence_result) -> list[str]:
        caps = []
        for endpoint in getattr(intelligence_result, "api_endpoints", []) or []:
            route = str(getattr(endpoint, "path", "") or "").lower()
            if domain == "repository_intelligence":
                if any(token in route for token in ("repo", "codebase", "analyze", "report", "test-gap", "onboarding", "prd", "ask", "summarize", "session")):
                    caps.append(route)
            elif domain == "ai_hallucination_detection":
                if any(token in route for token in ("verify", "fact", "claim", "citation", "source", "search")):
                    caps.append(route)
            elif domain == "healthcare":
                if any(token in route for token in ("diagnose", "search", "patient")):
                    caps.append(route)
        return clean_list(caps, max_items=6)

    def _to_evidence_reference(self, item) -> EvidenceReference:
        normalized, _ = normalize_evidence_source_type(
            getattr(item, "source_type", "file"),
            file=getattr(item, "file", None),
            source_id=getattr(item, "source_id", None),
        )
        return EvidenceReference(
            source_type=normalized,
            source_id=getattr(item, "source_id", "unknown"),
            file=getattr(item, "file", None),
            reason=getattr(item, "reason", "Detected product identity evidence."),
            snippet=None,
            confidence=getattr(item, "confidence", "medium"),
        )
