from __future__ import annotations

import json
import re
from typing import Optional

from pydantic import BaseModel, Field

from app.docs.models import DocEvidence
from app.docs.utils.evidence_sanitizer import sanitize_doc_evidence_list, sanitize_path, sanitize_text
from app.docs.utils.production_text import clean_list, summarize_stack
from app.intelligence.evidence_strength import DOMAIN_SIGNALS, EXPLICIT_METADATA_FILES, WEAK_TECHNICAL_SIGNALS, is_forbidden_product_identity
from app.intelligence.readme_sanitizer import (
    has_meaningful_identity_words,
    is_markup_noise_candidate,
    is_strong_identity_phrase,
    sanitize_readme_for_identity,
    sanitize_text_for_display,
)
from app.intelligence.repository_type_classifier import RepositoryTypeClassifier, documentation_domain_for_repo_type, is_documentation_repo_type


ConfidenceLevel = str


class ProductIdentity(BaseModel):
    project_name: Optional[str] = None
    project_name_confidence: ConfidenceLevel = "low"
    domain: Optional[str] = None
    domain_confidence: ConfidenceLevel = "low"
    architecture: str = "backend"
    repo_intelligence_score: int = 0
    ui_surface: list[str] = Field(default_factory=list)
    purpose_summary: str
    evidence: list[DocEvidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProductIdentityResolver:
    def resolve(self, scan_result=None, intelligence_result=None, contents: Optional[dict[str, object]] = None) -> ProductIdentity:
        contents = self._contents(scan_result, contents)
        repo_type = RepositoryTypeClassifier().classify(scan_result=scan_result, intelligence_result=intelligence_result).repo_type
        metadata = self._metadata(contents)
        evidence: list[DocEvidence] = []
        warnings: list[str] = []

        project_name, name_confidence, name_evidence = self._project_name(metadata)
        evidence.extend(name_evidence)

        domain, domain_confidence, domain_evidence = self._domain(metadata, contents, intelligence_result, repo_type)
        evidence.extend(domain_evidence)
        evidence.extend(self._dependency_evidence(intelligence_result))

        architecture = self._architecture_label(intelligence_result, contents, repo_type)
        ui_surface = self._ui_surface(contents)
        stack = summarize_stack(
            getattr(intelligence_result, "frameworks", []) if intelligence_result is not None else [],
            getattr(intelligence_result, "databases", []) if intelligence_result is not None else [],
            getattr(intelligence_result, "languages", []) if intelligence_result is not None else [],
        )
        capabilities = self._capabilities(intelligence_result)
        routes = [
            str(getattr(item, "path", "") or "").strip()
            for item in getattr(intelligence_result, "api_endpoints", []) or []
            if getattr(item, "path", None)
        ]
        repo_intelligence_score = self._repo_intelligence_score(metadata, contents, intelligence_result)
        if domain == "repository_intelligence" and repo_intelligence_score < 2:
            domain = f"generic_{architecture}" if architecture in {"frontend", "backend", "fullstack"} else "unknown"
            domain_confidence = "low"
        purpose_summary = self._purpose_summary(
            project_name=project_name,
            domain=domain,
            domain_confidence=domain_confidence,
            architecture=architecture,
            stack=stack,
            capabilities=capabilities,
            explicit_description=metadata.get("readme_description") or metadata.get("package_description") or metadata.get("pyproject_description") or "",
            ui_surface=ui_surface,
            routes=routes,
        )

        if domain_confidence == "low":
            warnings.append("Exact product purpose is not fully specified in the analyzed evidence.")
        if not project_name:
            warnings.append("Project name could not be confirmed from explicit metadata.")

        return ProductIdentity(
            project_name=project_name,
            project_name_confidence=name_confidence,
            domain=domain,
            domain_confidence=domain_confidence,
            architecture=architecture,
            repo_intelligence_score=repo_intelligence_score,
            ui_surface=ui_surface,
            purpose_summary=sanitize_text(purpose_summary),
            evidence=sanitize_doc_evidence_list(evidence),
            warnings=clean_list(warnings, max_items=8),
        )

    def _contents(self, scan_result=None, contents: Optional[dict[str, object]] = None) -> dict[str, object]:
        if isinstance(contents, dict):
            return contents
        candidate = getattr(scan_result, "contents", {}) if scan_result is not None else {}
        return candidate if isinstance(candidate, dict) else {}

    def _metadata(self, contents: dict[str, object]) -> dict[str, str]:
        metadata = {
            "readme_title": "",
            "readme_description": "",
            "package_name": "",
            "package_description": "",
            "pyproject_name": "",
            "pyproject_description": "",
            "docs_text": "",
        }
        for path, value in contents.items():
            lowered = str(path).replace("\\", "/").lower()
            text = self._to_text(value)
            if lowered.endswith("readme.md") or lowered.endswith("readme.mdx"):
                title, description = self._readme_metadata(sanitize_readme_for_identity(text))
                if lowered in {"readme.md", "readme.mdx"}:
                    metadata["readme_title"] = title
                    metadata["readme_description"] = description
                elif not metadata["readme_title"]:
                    metadata["readme_title"] = title
                    metadata["readme_description"] = description
            elif lowered.endswith("package.json"):
                try:
                    data = json.loads(text or "{}")
                except Exception:
                    data = {}
                metadata["package_name"] = sanitize_text(data.get("name", ""), fallback="")
                metadata["package_description"] = self._clean_description_candidate(data.get("description", ""))
            elif lowered.endswith("pyproject.toml"):
                metadata["pyproject_name"], metadata["pyproject_description"] = self._pyproject_metadata(text)
            elif "/docs/" in lowered or lowered.endswith((".md", ".rst")):
                metadata["docs_text"] += f" {sanitize_readme_for_identity(text)[:1200]}"
        return metadata

    def _project_name(self, metadata: dict[str, str]) -> tuple[Optional[str], str, list[DocEvidence]]:
        candidates = [
            ("README title", metadata.get("readme_title", ""), "README.md"),
            ("package.json name", metadata.get("package_name", ""), "package.json"),
            ("pyproject name", metadata.get("pyproject_name", ""), "pyproject.toml"),
        ]
        for reason, candidate, source_file in candidates:
            cleaned = self._clean_name(candidate)
            if cleaned:
                return cleaned, "high", [
                    DocEvidence(
                        source_type="file",
                        source_id=source_file,
                        file=source_file,
                        reason=f"Explicit product name found in {reason.lower()}.",
                        confidence="high",
                    )
                ]
        return None, "low", []

    def _domain(self, metadata: dict[str, str], contents: dict[str, object], intelligence_result, repo_type: str = "unknown") -> tuple[str, str, list[DocEvidence]]:
        if is_documentation_repo_type(repo_type):
            return documentation_domain_for_repo_type(repo_type, metadata.get("readme_description", "")), "high", [
                DocEvidence(
                    source_type="file",
                    source_id="README.md",
                    file="README.md",
                    reason="Repository metadata describes documentation or curriculum content.",
                    confidence="high",
                )
            ]
        docs_text = " ".join(
            [
                metadata.get("readme_title", ""),
                metadata.get("readme_description", ""),
                metadata.get("package_description", ""),
                metadata.get("pyproject_description", ""),
                metadata.get("docs_text", ""),
            ]
        ).lower()
        route_text = " ".join(
            str(getattr(item, "path", "") or "").lower()
            for item in getattr(intelligence_result, "api_endpoints", []) or []
        )
        module_text = " ".join(
            str(getattr(item, "name", "") or "").lower()
            for item in getattr(intelligence_result, "modules", []) or []
        )
        dep_text = " ".join(
            str(getattr(item, "name", "") or "").lower()
            for item in getattr(intelligence_result, "dependencies", []) or []
        )
        framework_text = " ".join(
            str(getattr(item, "name", "") or "").lower()
            for item in getattr(intelligence_result, "frameworks", []) or []
        )
        content_text = " ".join(f"{path} {self._to_text(value)[:800]}" for path, value in list(contents.items())[:20]).lower()

        scores: dict[str, int] = {}
        evidence: list[DocEvidence] = []
        for domain, signals in DOMAIN_SIGNALS.items():
            doc_hits = sum(1 for signal in signals if signal in docs_text)
            route_hits = sum(1 for signal in signals if signal in route_text)
            module_hits = sum(1 for signal in signals if signal in module_text)
            dep_hits = sum(1 for signal in signals if signal in dep_text or signal in framework_text)
            content_hits = sum(1 for signal in signals if signal in content_text)
            score = (doc_hits * 4) + (route_hits * 2) + (module_hits * 2) + (dep_hits * 2) + content_hits
            if score:
                scores[domain] = score
                evidence.append(
                    DocEvidence(
                        source_type="file",
                        source_id=domain,
                        file="README.md" if doc_hits else None,
                        reason=f"Detected domain signals for {domain.replace('_', ' ')} across docs, routes, modules, or dependencies.",
                        confidence="high" if doc_hits >= 1 and score >= 6 else "medium",
                    )
                )

        if "developer intelligence" in docs_text and any(token in route_text for token in ("/analyze", "/ask", "/summarize", "/report", "/session")):
            scores["repository_intelligence"] = max(scores.get("repository_intelligence", 0), 8)
        if any(token in docs_text for token in ("diagnosis", "medical", "healthcare")) and "/diagnose" in route_text and "/search" in route_text:
            scores["healthcare"] = max(scores.get("healthcare", 0), 8)

        has_repo_docs = any(signal in docs_text for signal in DOMAIN_SIGNALS["repository_intelligence"])
        if scores.get("repository_intelligence", 0) and not has_repo_docs and scores["repository_intelligence"] < 8:
            scores["repository_intelligence"] = 0

        best_domain = "unknown"
        best_score = 0
        for domain, score in scores.items():
            if score > best_score:
                best_domain = domain
                best_score = score

        if best_domain != "unknown":
            if best_score >= 8:
                return best_domain, "high", evidence
            if best_score >= 4:
                return best_domain, "medium", evidence

        architecture = self._architecture_label(intelligence_result, contents)
        if architecture == "fullstack":
            return "generic_fullstack", "low", evidence
        if architecture in {"backend", "frontend"}:
            return f"generic_{architecture}" if architecture != "frontend" else "unknown", "low", evidence
        return "unknown", "low", evidence

    def _architecture_label(self, intelligence_result, contents: dict[str, object], repo_type: str = "unknown") -> str:
        if is_documentation_repo_type(repo_type):
            return "unknown"
        arch = getattr(intelligence_result, "architecture", None)
        arch_type = str(getattr(arch, "type", arch or "unknown")).lower()
        if arch_type in {"frontend", "backend", "fullstack"}:
            return arch_type
        paths = " ".join(str(path).replace("\\", "/").lower() for path in contents.keys())
        framework_names = " ".join(str(getattr(item, "name", "") or "").lower() for item in getattr(intelligence_result, "frameworks", []) or [])
        has_frontend = any(token in paths or token in framework_names for token in ("frontend/", "src/pages/", "src/app/", ".tsx", ".jsx", "react", "vite", "next.js"))
        has_backend = any(token in paths or token in framework_names for token in ("fastapi", "flask", "express", "app/api/", ".py"))
        if has_frontend and has_backend:
            return "fullstack"
        if has_frontend:
            return "frontend"
        return "unknown"

    def _ui_surface(self, contents: dict[str, object]) -> list[str]:
        paths = " ".join(str(path).replace("\\", "/").lower() for path in contents.keys())
        tokens = []
        for label, pattern in (
            ("dashboard", "dashboard"),
            ("generator", "generator"),
            ("history", "history"),
            ("settings", "settings"),
            ("layout", "layout"),
            ("API service", "service"),
            ("routing", "route"),
        ):
            if pattern in paths:
                tokens.append(label)
        return clean_list(tokens, max_items=8)

    def _dependency_evidence(self, intelligence_result) -> list[DocEvidence]:
        rows: list[DocEvidence] = []
        for dep in getattr(intelligence_result, "dependencies", []) or []:
            dep_name = str(getattr(dep, "name", "") or "").strip().lower()
            if dep_name in {"openai", "langchain", "beautifulsoup4", "bs4", "requests", "playwright", "selenium"}:
                rows.append(
                    DocEvidence(
                        source_type="framework",
                        source_id=f"dep:{dep_name}",
                        file=sanitize_path(getattr(dep, "source_file", None), fallback="") or None,
                        reason=f"Dependency detected: {dep_name}",
                        confidence=getattr(dep, "confidence", "medium") if getattr(dep, "confidence", "medium") in {"high", "medium", "low"} else "medium",
                    )
                )
        return rows

    def _repo_intelligence_score(self, metadata: dict[str, str], contents: dict[str, object], intelligence_result) -> int:
        docs_text = " ".join(
            [
                metadata.get("readme_title", ""),
                metadata.get("readme_description", ""),
                metadata.get("package_description", ""),
                metadata.get("pyproject_description", ""),
                metadata.get("docs_text", ""),
            ]
        ).lower()
        module_text = " ".join(str(getattr(item, "name", "") or "").lower() for item in getattr(intelligence_result, "modules", []) or [])
        route_text = " ".join(str(getattr(item, "path", "") or "").lower() for item in getattr(intelligence_result, "api_endpoints", []) or [])
        path_text = " ".join(str(path).replace("\\", "/").lower() for path in contents.keys())
        hits = set()
        for signal in DOMAIN_SIGNALS["repository_intelligence"]:
            if signal in docs_text or signal in module_text or signal in route_text or signal in path_text:
                hits.add(signal)
        if "developer intelligence" in docs_text:
            hits.add("code intelligence")
        if "mcp" in path_text:
            hits.add("MCP tools")
        if "test_gap" in path_text or "test gap" in docs_text:
            hits.add("test gap")
        if "onboarding" in path_text or "onboarding report" in docs_text:
            hits.add("onboarding report")
        if "prd" in path_text or "prd generation" in docs_text:
            hits.add("PRD generation")
        if "architecture diff" in docs_text or "diff" in path_text:
            hits.add("architecture diff")
        return len(hits)

    def _capabilities(self, intelligence_result) -> list[str]:
        routes = [str(getattr(item, "path", "") or "") for item in getattr(intelligence_result, "api_endpoints", []) or []]
        caps = []
        for route in routes:
            lowered = route.lower()
            if lowered in WEAK_TECHNICAL_SIGNALS:
                continue
            if any(token in lowered for token in ("repo", "codebase")):
                caps.append("repository analysis")
            elif "analyze" in lowered:
                caps.append("analysis API")
            elif any(token in lowered for token in ("ask", "query", "chat")):
                caps.append("chat/query workflows")
            elif any(token in lowered for token in ("summarize", "summary")):
                caps.append("summarization")
            elif any(token in lowered for token in ("session", "history", "status")):
                caps.append("session tracking")
            elif any(token in lowered for token in ("report", "prd")):
                caps.append("report generation")
            elif any(token in lowered for token in ("claim", "verify", "citation", "source")):
                caps.append("claim verification")
            elif "diagnose" in lowered:
                caps.append("diagnosis API")
            elif any(token in lowered for token in ("checkout", "cart", "order")):
                caps.append("commerce workflows")
            elif any(token in lowered for token in ("course", "lesson", "quiz")):
                caps.append("learning workflows")
            elif any(token in lowered for token in ("invoice", "billing", "ledger")):
                caps.append("finance workflows")
        return clean_list(caps, max_items=6)

    def _purpose_summary(self, project_name: Optional[str], domain: str, domain_confidence: str, architecture: str, stack: str, capabilities: list[str], explicit_description: str, ui_surface: list[str], routes: list[str]) -> str:
        subject = project_name or ("this project" if architecture not in {"backend", "fullstack"} else f"this {architecture} service")
        explicit_description = self._clean_description_candidate(explicit_description)
        if domain == "repository_intelligence" and domain_confidence == "high":
            detail = f" The explicit product description says: {explicit_description}." if explicit_description else ""
            stack_text = f" It is built with {stack}." if stack else ""
            caps_text = f" Detected capabilities include {', '.join(capabilities[:4])}." if capabilities else ""
            return f"{subject} is a repository intelligence platform based on explicit codebase-analysis evidence in the repository metadata and routes.{stack_text}{caps_text}{detail}"
        if domain == "ai_hallucination_detection" and domain_confidence in {"high", "medium"}:
            prefix = "is" if domain_confidence == "high" else "appears to be"
            detail = f" The explicit product description says: {explicit_description}." if explicit_description else ""
            return f"{subject} {prefix} an AI hallucination detection and fact-checking backend that evaluates claims or AI-generated answers using web-sourced evidence.{detail}"
        if domain == "healthcare" and domain_confidence in {"high", "medium"}:
            if "fastapi" in stack.lower():
                return f"{subject} is an offline-first AI-assisted medical diagnosis and knowledge retrieval backend built with FastAPI. It exposes diagnosis and search APIs to support medical query workflows."
            prefix = "is" if domain_confidence == "high" else "appears to be"
            detail = f" The explicit product description says: {explicit_description}." if explicit_description else ""
            return f"{subject} {prefix} an AI-assisted healthcare backend that supports diagnosis workflows and medical query workflows.{detail}"
        domain_descriptions = {
            "ecommerce": "an e-commerce application",
            "lms": "a learning platform",
            "finance": "a finance-oriented application",
            "crm": "a CRM or business dashboard application",
            "cms": "a content management application",
            "chatbot": "an AI assistant application",
            "analytics": "an analytics platform",
            "devops": "a DevOps or automation tool",
        }
        if domain == "software engineering education":
            detail = f" The explicit product description says: {explicit_description}." if explicit_description else ""
            return f"{subject} is a study-plan repository for software engineering interview preparation and structured learning resources.{detail}"
        if domain == "documentation":
            detail = f" The explicit product description says: {explicit_description}." if explicit_description else ""
            return f"{subject} is a documentation-focused repository that organizes guides, reference material, and structured content.{detail}"
        if domain in domain_descriptions and domain_confidence in {"high", "medium"}:
            prefix = "is" if domain_confidence == "high" else "appears to be"
            detail = f" based on detected {', '.join(capabilities[:2])}" if capabilities else ""
            explicit = f" The explicit product description says: {explicit_description}." if explicit_description else ""
            return f"{subject} {prefix} {domain_descriptions[domain]}{detail}.{explicit}"
        if domain == "repository_intelligence":
            stack_text = f" It is built with {stack}." if stack else ""
            caps_text = f" Detected capabilities include {', '.join(capabilities[:4])}." if capabilities else ""
            detail = f" The explicit product description says: {explicit_description}." if explicit_description else ""
            return f"{subject} appears to be a repository intelligence application based on detected repository-analysis evidence.{stack_text}{caps_text}{detail}"
        stack_part = f" built with {stack}" if stack else ""
        if architecture == "frontend":
            ui_text = f" with {', '.join(ui_surface)} components" if ui_surface else ""
            return f"{subject} appears to be a frontend application{stack_part}{ui_text}. The exact product purpose is not fully specified in the analyzed evidence."
        if architecture == "fullstack":
            route_text = f" It exposes {routes[0]} endpoint." if routes else ""
            return f"{subject} appears to be a fullstack application{stack_part}.{route_text} The exact product purpose is not fully specified in the analyzed evidence."
        route_text = f" It exposes {routes[0]} endpoint." if routes else ""
        return f"{subject} appears to be a backend API service{stack_part}.{route_text} The exact product purpose is not fully specified in the analyzed evidence."

    def _to_text(self, value: object) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return str(value or "")

    def _readme_metadata(self, text: str) -> tuple[str, str]:
        title = ""
        description = ""
        paragraph: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not title and line.startswith("# "):
                title = sanitize_text_for_display(line[2:], fallback="")
                continue
            if not title or line.startswith(("#", "!", "[", "<", "$", ">")):
                continue
            if not line:
                if paragraph:
                    candidate = self._clean_description_candidate(" ".join(paragraph))
                    if candidate:
                        description = candidate
                        break
                    paragraph = []
                continue
            if line.startswith(("-", "*")):
                continue
            paragraph.append(line)
            candidate = self._clean_description_candidate(" ".join(paragraph))
            if candidate:
                description = candidate
                break
        if not description and paragraph:
            description = self._clean_description_candidate(" ".join(paragraph))
        return title, description

    def _pyproject_metadata(self, text: str) -> tuple[str, str]:
        name = ""
        description = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("name") and "=" in stripped and not name:
                name = sanitize_text(stripped.split("=", 1)[1].strip(" '\""), fallback="")
            if stripped.startswith("description") and "=" in stripped and not description:
                description = self._clean_description_candidate(stripped.split("=", 1)[1].strip(" '\""))
        return name, description

    def _clean_description_candidate(self, value: object) -> str:
        text = sanitize_text_for_display(str(value or ""), fallback="")
        if not text:
            return ""
        if is_markup_noise_candidate(text):
            return ""
        if not has_meaningful_identity_words(text, minimum=8) and not is_strong_identity_phrase(text):
            return ""
        return sanitize_text(text, fallback="")

    def _clean_name(self, value: str) -> Optional[str]:
        text = sanitize_text_for_display(value, fallback="").strip()
        if not text:
            return None
        if is_markup_noise_candidate(text):
            return None
        text = re.sub(r"[-_]+", " ", text)
        parts = [part for part in text.split() if part]
        if not parts:
            return None
        if len(parts) == 1 and is_forbidden_product_identity(parts[0]):
            return None
        if all(is_forbidden_product_identity(part) for part in parts):
            return None
        return " ".join(part if part.isupper() else part.capitalize() for part in parts)
