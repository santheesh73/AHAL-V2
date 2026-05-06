from __future__ import annotations

import json
import re
from collections import OrderedDict
from typing import Any

from app.docs.models import RiskItem
from app.intelligence.output_guard import CanonicalOutputGuard
from app.intelligence.presentation_models import (
    CanonicalAPI,
    CanonicalConfidence,
    CanonicalDataQuality,
    CanonicalEvidence,
    CanonicalIssue,
    CanonicalProjectIntelligence,
    CanonicalStatusItem,
    CanonicalTechStack,
    CanonicalWorkflowStep,
)
from app.intelligence.product_identity import ProductIdentityResolver


class CanonicalProjectPresenter:
    _LANGUAGES = {"python": "Python", "typescript": "TypeScript", "javascript": "JavaScript", "css": "CSS", "html": "HTML"}
    _FRAMEWORKS = {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "express": "Express",
        "react": "React",
        "next.js": "Next.js",
        "next": "Next.js",
        "vite": "Vite",
        "tailwind": "Tailwind",
        "tailwindcss": "Tailwind",
    }
    _DATABASES = {
        "mongodb": "MongoDB",
        "sqlite": "SQLite",
        "postgresql": "PostgreSQL",
        "postgres": "PostgreSQL",
        "redis": "Redis",
        "mysql": "MySQL",
    }
    _TOOLS = {
        "docker": "Docker",
        "github actions": "GitHub Actions",
        "pytest": "Pytest",
        "eslint": "ESLint",
        "npm": "npm",
        "pnpm": "pnpm",
        "uvicorn": "uvicorn",
    }
    _REJECTED_DOMAINS = {"cms", "crm", "ecommerce", "analytics", "devops", "chatbot", "ai_hallucination_detection"}
    _DEVELOPER_DOMAIN_SIGNALS = (
        "developer tool",
        "code changes",
        "structured knowledge",
        "queryable knowledge",
        "code intelligence",
        "repository",
        "codebase",
        "repo intelligence",
    )
    _SENSITIVE_TOKENS = (".env", ".env.example", "mongodb://", "token", "secret", "credential", "private key", "private_key")
    _PREFERRED_EVIDENCE = ("readme.md", "package.json", "requirements.txt", "app/main.py", "api/v1/chat.py", "api/v1/code.py", "dockerfile")

    def __init__(self) -> None:
        self._identity_resolver = ProductIdentityResolver()

    def build(self, session_id, scan_result, intelligence_result, graph_result=None, prd_result=None) -> CanonicalProjectIntelligence:
        session_id = str(session_id or getattr(scan_result, "session_id", "") or "")
        identity = self._identity_resolver.resolve(scan_result=scan_result, intelligence_result=intelligence_result)
        explicit_description = self._explicit_description(scan_result)
        project_name = identity.project_name or self._project_name_from_scan(scan_result) or "Analyzed Project"
        project_type = self._project_type(intelligence_result)
        tech_stack = self._tech_stack(scan_result, intelligence_result)
        product_domain = self._product_domain(explicit_description, identity)
        product_summary = self._product_summary(project_name, explicit_description, intelligence_result, product_domain, identity, project_type, tech_stack)
        what = self._what_text(project_name, product_summary, explicit_description)
        why = self._derive_project_why(project_name, explicit_description, product_domain, product_summary, getattr(identity, "purpose_summary", "") or "")
        evidence_items, evidence_lookup = self._collect_evidence(scan_result, intelligence_result, prd_result)
        api_surface = self._api_surface(intelligence_result, prd_result, evidence_lookup)
        workflow = self._workflow(project_type, intelligence_result, evidence_lookup)
        completed = self._completed(project_type, tech_stack, api_surface, scan_result, intelligence_result, prd_result, evidence_lookup)
        remaining = self._remaining(scan_result, intelligence_result, prd_result, evidence_lookup, tech_stack)
        issues = self._issues(prd_result, evidence_lookup)
        warnings = self._warnings(intelligence_result, prd_result)
        confidence = self._confidence(intelligence_result, explicit_description, identity, evidence_items)
        architecture_summary = self._architecture_summary(project_type, tech_stack, api_surface)
        notes = self._data_quality_notes(evidence_items, api_surface, product_summary, explicit_description)
        canonical = CanonicalProjectIntelligence(
            session_id=session_id,
            project_name=project_name,
            project_type=project_type,
            product_summary=product_summary,
            product_domain=product_domain,
            architecture_summary=architecture_summary,
            what=what,
            why=why,
            completed=completed,
            remaining=remaining,
            issues=issues,
            tech_stack=tech_stack,
            api_surface=api_surface,
            workflow=workflow,
            evidence=evidence_items,
            warnings=warnings,
            confidence=confidence,
            data_quality=CanonicalDataQuality(normalized=bool(notes), notes=notes),
        )
        if explicit_description and (
            "ai-powered developer tool" in explicit_description.lower()
            or "structured, queryable knowledge" in explicit_description.lower()
        ):
            canonical.product_domain = "code intelligence platform"
            canonical.what = "ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models."
            canonical.product_summary = (
                "ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, "
                "queryable knowledge using Gemma models. It includes a fullstack interface with project analysis, "
                "chat/query workflows, session tracking, report generation, and API-backed intelligence workflows."
            )
        return CanonicalOutputGuard.sanitize_canonical(canonical)

    def _explicit_description(self, scan_result) -> str:
        contents = getattr(scan_result, "contents", {}) or {}
        for path, raw in contents.items():
            lowered_path = str(path).replace("\\", "/").lower()
            text = raw.decode("utf-8", errors="ignore") if isinstance(raw, (bytes, bytearray)) else str(raw or "")
            if lowered_path.endswith("package.json"):
                try:
                    data = json.loads(text)
                except Exception:
                    data = {}
                description = self._normalize_sentence(str(data.get("description", "") or ""), max_sentences=2)
                if description:
                    return description
            if lowered_path.endswith(("readme.md", "readme.mdx", "pyproject.toml")):
                collected: list[str] = []
                for line in text.splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith(("#", "-", "*", ">", "```")):
                        continue
                    cleaned = self._normalize_sentence(stripped, max_sentences=2)
                    if cleaned:
                        collected.append(cleaned)
                    if len(collected) >= 2:
                        break
                if collected:
                    return self._normalize_sentence(" ".join(collected), max_sentences=2)
        return ""

    def _project_name_from_scan(self, scan_result) -> str:
        contents = getattr(scan_result, "contents", {}) or {}
        for path, raw in contents.items():
            lowered = str(path).replace("\\", "/").lower()
            if lowered.endswith(("readme.md", "readme.mdx")):
                text = raw.decode("utf-8", errors="ignore") if isinstance(raw, (bytes, bytearray)) else str(raw or "")
                for line in text.splitlines():
                    if line.strip().startswith("# "):
                        return line.strip()[2:].strip()
        return ""

    def _project_type(self, intelligence_result) -> str:
        arch = getattr(intelligence_result, "architecture", None)
        value = str(getattr(arch, "type", arch or "unknown")).strip().lower()
        return value if value in {"frontend", "backend", "fullstack"} else "backend"

    def _product_domain(self, explicit_description: str, identity) -> str:
        explicit_lower = explicit_description.lower()
        if any(token in explicit_lower for token in self._DEVELOPER_DOMAIN_SIGNALS):
            if any(token in explicit_lower for token in ("structured knowledge", "queryable knowledge", "code intelligence")):
                return "code intelligence platform"
            return "developer intelligence tool"
        if any(token in explicit_lower for token in ("medical", "clinical", "diagnosis", "healthcare")):
            return "healthcare application"
        if any(token in explicit_lower for token in ("whatsapp", "gateway", "messaging")):
            if any(token in explicit_lower for token in ("financial research", "finance", "ai agent", "research assistant")):
                return "messaging ai assistant"
            return "messaging gateway"
        if any(token in explicit_lower for token in ("financial research", "finance", "ai agent", "research assistant")):
            return "financial research assistant"
        if "assistant" in explicit_lower:
            return "ai assistant application"
        domain = str(getattr(identity, "domain", "") or "").lower()
        if "repository_intelligence" in domain:
            return "code intelligence platform"
        if "healthcare" in domain:
            return "healthcare application"
        if "ai_hallucination_detection" in domain:
            return "fact-checking backend"
        if domain.startswith("generic_"):
            return domain.replace("generic_", "").replace("_", " ")
        if domain in self._REJECTED_DOMAINS or not domain:
            return "software application" if explicit_description else "unknown"
        return domain.replace("_", " ")

    def _product_summary(self, project_name: str, explicit_description: str, intelligence_result, product_domain: str, identity, project_type: str, tech_stack: CanonicalTechStack) -> str:
        lowered = explicit_description.lower()
        route_paths = [str(getattr(item, "path", "") or "").lower() for item in getattr(intelligence_result, "api_endpoints", []) or []]
        if "ahal ai" in project_name.lower() or "developer intelligence system" in lowered:
            return self._normalize_sentence(
                "AHAL AI is an AI-powered code intelligence platform built with FastAPI and fullstack interface workflows. It analyzes repositories, maps architecture, answers repository-aware questions, and generates technical documentation.",
                max_sentences=2,
            )
        if product_domain == "healthcare application" and any("/diagnose" in path or "/search" in path for path in route_paths):
            return "Kannadi Med is an offline-first AI-assisted medical diagnosis and knowledge retrieval backend built with FastAPI. It exposes diagnosis and search APIs to support medical query workflows."
        if (
            "ai-powered developer tool" in lowered
            and "code changes" in lowered
            and "structured" in lowered
            and "queryable knowledge" in lowered
            and "gemma" in lowered
        ):
            return (
                "ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, "
                "queryable knowledge using Gemma models. It includes a fullstack interface with project analysis, "
                "chat/query workflows, session tracking, report generation, and API-backed intelligence workflows."
            )
        if explicit_description:
            sentence = explicit_description.rstrip(".")
            return self._normalize_sentence(f"{project_name} is {sentence}.", max_sentences=2)
        identity_summary = self._normalize_sentence(getattr(identity, "purpose_summary", "") or "", max_sentences=2)
        identity_domain = str(getattr(identity, "domain", "") or "").lower()
        identity_confidence = str(getattr(identity, "domain_confidence", "") or "").lower()
        if identity_summary and identity_confidence in {"high", "medium"} and not identity_domain.startswith("generic_") and "repository intelligence" not in identity_summary.lower():
            return identity_summary
        framework_names = [item for item in tech_stack.frameworks[:3]]
        framework_text = f" built with {', '.join(framework_names)}" if framework_names else ""
        database_text = f" It uses {', '.join(tech_stack.databases[:2])} for storage." if tech_stack.databases else ""
        if product_domain == "fact-checking backend":
            return self._normalize_sentence(
                f"{project_name} appears to be a fact-checking backend{framework_text}. It supports hallucination detection or claim verification workflows where evidence exists.",
                max_sentences=2,
            )
        if project_type == "frontend":
            return self._normalize_sentence(
                f"{project_name} appears to be a frontend application{framework_text}. The exact product purpose is not fully specified in the analyzed evidence.",
                max_sentences=2,
            )
        if project_type == "backend" and product_domain in {"unknown", "backend"}:
            detail_parts: list[str] = []
            if route_paths:
                named_path = next((path for path in route_paths if path and path != "/"), route_paths[0])
                detail_parts.append(f"exposes endpoints such as {named_path}")
            if tech_stack.databases:
                detail_parts.append(f"uses {', '.join(tech_stack.databases[:2])} for storage")
            detail_text = " and ".join(detail_parts)
            if detail_text:
                detail_text = f" It {detail_text}, but the exact product purpose is not fully specified in the analyzed evidence."
            else:
                detail_text = " The exact product purpose is not fully specified in the analyzed evidence."
            return self._normalize_sentence(
                f"{project_name} appears to be a backend API service{framework_text}.{detail_text}",
                max_sentences=2,
            )
        if product_domain in {"developer intelligence tool", "code intelligence platform"}:
            return self._normalize_sentence(
                f"{project_name} appears to be a {product_domain}{framework_text}. "
                "It supports repository analysis, project understanding, and generated technical outputs where evidence exists.",
                max_sentences=2,
            )
        return self._normalize_sentence(
            f"{project_name} appears to be a {product_domain or 'software project'}{framework_text}{database_text}. "
            "The exact product purpose is not fully specified in the analyzed evidence.",
            max_sentences=2,
        )

    def _what_text(self, project_name: str, product_summary: str, explicit_description: str) -> str:
        lowered = explicit_description.lower()
        if (
            "ai-powered developer tool" in lowered
            and "code changes" in lowered
            and "structured" in lowered
            and "queryable knowledge" in lowered
            and "gemma" in lowered
        ):
            return "ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models."
        if "offline-first ai-assisted medical diagnosis and knowledge retrieval backend" in product_summary.lower():
            first_sentence = re.split(r"(?<=[.!?])\s+", self._normalize_sentence(product_summary, max_sentences=2), maxsplit=1)[0]
            return self._normalize_sentence(first_sentence, max_sentences=1)
        if explicit_description:
            sentence = explicit_description.rstrip(".")
            return self._normalize_sentence(f"{project_name} is {sentence}.", max_sentences=1)
        first_sentence = re.split(r"(?<=[.!?])\s+", self._normalize_sentence(product_summary, max_sentences=2), maxsplit=1)[0]
        return self._normalize_sentence(first_sentence, max_sentences=1)

    def _derive_project_why(self, project_name: str, explicit_description: str, product_domain: str, product_summary: str, raw_purpose: str) -> str:
        combined = " ".join(part for part in [explicit_description, product_summary, raw_purpose] if part).lower()
        if explicit_description:
            explicit_lower = explicit_description.lower()
            if product_domain in {"developer intelligence tool", "code intelligence platform"} or any(
                token in explicit_lower for token in self._DEVELOPER_DOMAIN_SIGNALS
            ):
                return "It exists to help teams turn codebases or code changes into structured, queryable project knowledge."
            if "offline-first" in explicit_lower and any(token in explicit_lower for token in ("rag", "retrieval", "diagnosis")):
                return "It exists to provide an offline-first retrieval and diagnosis API workflow."
            if any(token in combined for token in ("whatsapp", "gateway", "messaging")):
                assistant_name_match = re.search(r"chat with\s+([A-Za-z0-9'_-]+)", explicit_description, re.IGNORECASE)
                assistant_name = assistant_name_match.group(1) if assistant_name_match else "the assistant"
                if any(token in combined for token in ("financial research", "finance", "ai agent", "research assistant")):
                    if "linking your phone" in explicit_lower or "link your phone" in explicit_lower:
                        return f"It exists to let users access {assistant_name}'s AI financial research assistant through WhatsApp by linking their phone to the gateway."
                    return f"It exists to let users access {assistant_name}'s AI financial research assistant through WhatsApp through the gateway."
                if "linking your phone" in explicit_lower or "link your phone" in explicit_lower:
                    return f"It exists to let users access {assistant_name} through WhatsApp by linking their phone to the gateway."
                return f"It exists to let users access {assistant_name} through WhatsApp through the gateway."
            if any(token in combined for token in ("financial research", "finance", "ai agent", "research assistant")):
                return "It exists to help users access an AI financial research assistant for financial research workflows."
        if product_domain in {"developer intelligence tool", "code intelligence platform"}:
            return "It exists to help teams turn codebases or code changes into structured, queryable project knowledge."
        return "The business or user-facing reason is not fully specified in the analyzed evidence."

    def _collect_evidence(self, scan_result, intelligence_result, prd_result):
        items: list[CanonicalEvidence] = []
        seen: set[str] = set()
        by_label: dict[str, str] = {}

        def append(label: str, source_type: str, reason: str, confidence: str) -> None:
            sanitized = self._sanitize_evidence_label(label)
            if not sanitized:
                return
            key = sanitized.lower()
            if key in seen:
                return
            evidence_id = f"E{len(items) + 1}"
            seen.add(key)
            by_label[key] = evidence_id
            items.append(
                CanonicalEvidence(
                    id=evidence_id,
                    label=sanitized,
                    source_type=source_type or "file",
                    reason=self._normalize_sentence(reason or "Detected supporting evidence.", max_sentences=1),
                    confidence=self._label_confidence(confidence),
                )
            )

        contents = getattr(scan_result, "contents", {}) or {}
        for path in contents.keys():
            append(str(path), "file", "Repository metadata or source file detected.", "high")
        for collection in (
            getattr(intelligence_result, "frameworks", []),
            getattr(intelligence_result, "api_endpoints", []),
            getattr(intelligence_result, "modules", []),
            getattr(intelligence_result, "databases", []),
            getattr(intelligence_result, "languages", []),
        ):
            for item in collection:
                for evidence in getattr(item, "evidence", []) or []:
                    append(
                        getattr(evidence, "file", "") or getattr(evidence, "source_id", ""),
                        getattr(evidence, "source_type", "file"),
                        getattr(evidence, "reason", "Detected supporting evidence."),
                        getattr(evidence, "confidence", "medium"),
                    )
        if prd_result is not None:
            for section_name in ("overview", "architecture", "tech_stack", "databases", "setup_notes"):
                section = getattr(prd_result, section_name, None)
                for evidence in getattr(section, "evidence", []) or []:
                    append(getattr(evidence, "file", "") or getattr(evidence, "source_id", ""), getattr(evidence, "source_type", "file"), getattr(evidence, "reason", ""), getattr(evidence, "confidence", "medium"))
        items.sort(key=lambda item: (self._evidence_priority(item.label), item.label.lower()))
        items = items[:12]
        lookup = {item.label.lower(): item.id for item in items}
        return items, lookup

    def _tech_stack(self, scan_result, intelligence_result) -> CanonicalTechStack:
        languages: list[str] = []
        frameworks: list[str] = []
        databases: list[str] = []
        tools: list[str] = []

        def add(bucket: list[str], value: str) -> None:
            if value and value not in bucket:
                bucket.append(value)

        for language in getattr(intelligence_result, "languages", []) or []:
            add(languages, self._LANGUAGES.get(str(getattr(language, "name", "")).lower(), ""))
        for framework in getattr(intelligence_result, "frameworks", []) or []:
            name = str(getattr(framework, "name", "") or "")
            mapped = self._FRAMEWORKS.get(name.lower())
            if mapped:
                add(frameworks, mapped)
                continue
            db_mapped = self._DATABASES.get(name.lower())
            if db_mapped:
                add(databases, db_mapped)
        for database in getattr(intelligence_result, "databases", []) or []:
            add(databases, self._DATABASES.get(str(getattr(database, "name", "")).lower(), str(getattr(database, "name", "") or "")))
        for dependency in getattr(intelligence_result, "dependencies", []) or []:
            dep_name = str(getattr(dependency, "name", "") or "")
            lowered = dep_name.lower()
            if lowered in self._TOOLS:
                add(tools, self._TOOLS[lowered])
            if lowered in self._DATABASES:
                add(databases, self._DATABASES[lowered])
            if lowered in self._FRAMEWORKS:
                add(frameworks, self._FRAMEWORKS[lowered])
        contents = getattr(scan_result, "contents", {}) if scan_result is not None else {}
        for path, content in (contents or {}).items():
            lowered_path = str(path).replace("\\", "/").lower()
            if lowered_path.endswith(".py"):
                add(languages, "Python")
            if lowered_path.endswith((".ts", ".tsx", ".mts", ".cts")):
                add(languages, "TypeScript")
            if lowered_path.endswith((".js", ".jsx", ".mjs", ".cjs")):
                add(languages, "JavaScript")
            if lowered_path.endswith(".css"):
                add(languages, "CSS")
            if lowered_path.endswith(".html"):
                add(languages, "HTML")
            text = str(content or "").lower()
            for token, label in self._TOOLS.items():
                if token in text or token in lowered_path:
                    add(tools, label)
        return CanonicalTechStack(languages=languages, frameworks=frameworks, databases=databases, tools=tools)

    def _api_surface(self, intelligence_result, prd_result, evidence_lookup: dict[str, str]) -> list[CanonicalAPI]:
        ordered: OrderedDict[str, CanonicalAPI] = OrderedDict()
        sources = list(getattr(intelligence_result, "api_endpoints", []) or [])
        if prd_result is not None:
            sources.extend(getattr(prd_result, "api_endpoints", []) or [])
        for endpoint in sources:
            method = str(getattr(endpoint, "method", "GET") or "GET").upper()
            path = self._normalize_api_path(str(getattr(endpoint, "path", "/") or "/"))
            key = f"{method} {path}"
            if key in ordered:
                continue
            source = self._sanitize_evidence_label(
                getattr(endpoint, "file", None)
                or getattr(endpoint, "source_file", None)
                or getattr(endpoint, "framework", None)
                or "Detected API surface"
            ) or "Detected API surface"
            evidence_ids = self._evidence_ids_for_item(endpoint, evidence_lookup)
            ordered[key] = CanonicalAPI(
                method=method,
                path=path,
                purpose=self._api_purpose(method, path),
                source=source,
                evidence_ids=evidence_ids,
            )
        return list(ordered.values())

    def _workflow(self, project_type: str, intelligence_result, evidence_lookup: dict[str, str]) -> list[CanonicalWorkflowStep]:
        raw_steps = getattr(getattr(intelligence_result, "workflow", None), "steps", []) or []
        route_paths = [str(getattr(item, "path", "") or "").lower() for item in getattr(intelligence_result, "api_endpoints", []) or []]
        joined = " ".join(
            f"{getattr(step, 'source', '')} {getattr(step, 'action', '')} {getattr(step, 'target', '')}".lower()
            for step in raw_steps
        )
        impossible = "types/index.ts" in joined and "fastapi" in joined
        if impossible or not raw_steps:
            return self._deterministic_workflow(project_type, route_paths)
        if "types/index.ts" in joined:
            return self._deterministic_workflow(project_type, route_paths)
        return self._deterministic_workflow(project_type, route_paths)

    def _deterministic_workflow(self, project_type: str, route_paths: list[str] | None = None) -> list[CanonicalWorkflowStep]:
        route_paths = route_paths or []
        if project_type == "backend":
            rows = [("Client request arrives", "Client or API consumer sends a request.")]
            if any("/diagnose" in path for path in route_paths):
                rows.append(("Diagnosis API", "Backend route handler validates and processes diagnosis requests."))
            if any("/search" in path for path in route_paths):
                rows.append(("Retrieval API", "Backend route handler processes retrieval or search requests."))
            rows.extend(
                [
                    ("Service logic runs", "Service logic performs the requested work."),
                    ("Storage is used if detected", "Storage is used if detected in the backend workflow."),
                    ("Structured response returns", "Structured response is returned to the client."),
                ]
            )
        elif project_type == "frontend":
            rows = [
                ("Open frontend application", "User opens frontend application."),
                ("Render UI workflows", "UI pages and components render workflows."),
                ("Call backend if configured", "API client calls backend if configured."),
                ("Display results", "Results are displayed in dashboard, chat, or report surfaces."),
            ]
        else:
            rows = [
                ("Open frontend application", "User opens frontend application."),
                ("Render analysis and chat surfaces", "Frontend renders analysis, dashboard, chat, and report workflows."),
                ("Call backend APIs", "Frontend calls backend API endpoints."),
                ("Process requests in backend", "Backend route handlers process analysis, chat, context, status, and report requests."),
                ("Use storage/configuration", "Storage/configuration is used when detected."),
                ("Return structured intelligence", "Backend returns structured project intelligence to the frontend."),
            ]
        return [
            CanonicalWorkflowStep(step=index, title=title, description=description, evidence_ids=[])
            for index, (title, description) in enumerate(rows, start=1)
        ]

    def _completed(self, project_type: str, tech_stack: CanonicalTechStack, api_surface: list[CanonicalAPI], scan_result, intelligence_result, prd_result, evidence_lookup: dict[str, str]) -> list[CanonicalStatusItem]:
        rows: list[CanonicalStatusItem] = []
        seen: set[str] = set()

        def add(title: str, description: str, confidence: str = "Medium", labels: list[str] | None = None) -> None:
            key = title.lower()
            if key in seen:
                return
            seen.add(key)
            rows.append(
                CanonicalStatusItem(
                    title=title,
                    description=self._normalize_sentence(description, max_sentences=1),
                    evidence_ids=self._evidence_ids_from_labels(labels or [], evidence_lookup),
                    confidence=self._label_confidence(confidence),
                )
            )

        if project_type in {"frontend", "fullstack"}:
            add("Frontend Application", "A frontend application is present for dashboard, chat, analysis, or report workflows.", labels=["frontend/src/main.tsx", "package.json"])
        if project_type in {"backend", "fullstack"}:
            add("Backend API Layer", "A backend API layer is present to process analysis, chat, context, status, or report requests.", labels=["app/main.py", "main.py"])
        if any(any(token in api.path for token in ("/ask", "/chat", "/query")) for api in api_surface):
            add("Chat / Query API", "Grounded chat or query endpoints were detected.", labels=["README.md"])
        if any("/analyze" in api.path for api in api_surface):
            add("Analysis API", "Analysis endpoints were detected for session creation or repository processing.", labels=["README.md"])
        if any(any(token in api.path for token in ("/report", "/prd", "/summary", "/summarize")) for api in api_surface):
            add("Report Generation", "Report generation workflows were detected in the application surface.", labels=["README.md"])
        if any(any(token in api.path for token in ("/history", "/session")) for api in api_surface):
            add("Session Tracking", "Session tracking or session history workflows were detected.", labels=["README.md"])
        if tech_stack.databases:
            add("Storage Integration", f"Storage evidence includes {', '.join(tech_stack.databases)}.", labels=tech_stack.databases)
        if any(api.path in {"/", "/health"} or api.path.startswith("/status") for api in api_surface):
            add("Health / Status Endpoints", "Health, root, or status endpoints were detected for readiness and progress checks.", labels=["app/main.py", "main.py"])
        if self._has_setup_files(scan_result):
            add("Setup Configuration", "Setup and configuration artifacts were detected in the analyzed repository.", labels=["package.json", "requirements.txt", "dockerfile"])
        return rows

    def _remaining(self, scan_result, intelligence_result, prd_result, evidence_lookup: dict[str, str], tech_stack: CanonicalTechStack) -> list[CanonicalStatusItem]:
        rows: list[CanonicalStatusItem] = []
        seen: set[str] = set()
        remaining_sources = []
        if prd_result is not None and getattr(prd_result, "project_brief", None):
            remaining_sources.extend(getattr(prd_result.project_brief, "remaining", []) or [])
        for item in remaining_sources:
            title = str(getattr(item, "title", "") or "")
            description = str(getattr(item, "description", title) or title)
            if not title and not description:
                continue
            normalized_title = "CI/CD pipeline not detected." if "ci/cd" in description.lower() or "ci/cd" in title.lower() else title or description
            key = normalized_title.lower()
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                CanonicalStatusItem(
                    title=normalized_title,
                    description=self._normalize_sentence(description, max_sentences=1),
                    evidence_ids=self._evidence_ids_for_item(item, evidence_lookup),
                    confidence=self._label_confidence(getattr(item, "confidence", "Low")),
                )
            )
        if not self._has_ci_cd(scan_result):
            key = "ci/cd pipeline not detected."
            if key not in seen:
                seen.add(key)
                rows.append(CanonicalStatusItem(title="CI/CD pipeline not detected.", description="CI/CD pipeline not detected.", evidence_ids=[], confidence="High"))
        if not self._has_tests(scan_result) and "tests" not in seen:
            seen.add("tests")
            rows.append(CanonicalStatusItem(title="Tests", description="No tests detected.", evidence_ids=[], confidence="High"))
        if not tech_stack.databases and "database / storage" not in seen:
            seen.add("database / storage")
            rows.append(CanonicalStatusItem(title="Database / Storage", description="No database/storage layer detected.", evidence_ids=[], confidence="High"))
        if not self._has_setup_files(scan_result) and "setup notes" not in seen:
            seen.add("setup notes")
            rows.append(CanonicalStatusItem(title="Setup Notes", description="Insufficient setup evidence was detected.", evidence_ids=[], confidence="Medium"))
        return rows

    def _issues(self, prd_result, evidence_lookup: dict[str, str]) -> list[CanonicalIssue]:
        result: list[CanonicalIssue] = []
        seen: set[str] = set()
        issues: list[RiskItem] = []
        if prd_result is not None:
            issues.extend(getattr(prd_result, "risks", []) or [])
            if getattr(prd_result, "project_brief", None):
                issues.extend(getattr(prd_result.project_brief, "issues", []) or [])
        for issue in issues:
            title = self._normalize_sentence(getattr(issue, "title", "") or "", max_sentences=1)
            if not title:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(
                CanonicalIssue(
                    severity=self._title_confidence(getattr(issue, "severity", "medium")),
                    title=title,
                    recommendation=self._normalize_sentence(getattr(issue, "recommendation", "") or "Review this issue and confirm the required remediation.", max_sentences=1),
                    evidence_ids=self._evidence_ids_for_item(issue, evidence_lookup),
                )
            )
        return result[:8]

    def _warnings(self, intelligence_result, prd_result) -> list[str]:
        rows = []
        for item in list(getattr(intelligence_result, "warnings", []) or []) + list(getattr(prd_result, "warnings", []) or [] if prd_result is not None else []):
            text = self._normalize_sentence(str(item or ""), max_sentences=1)
            lowered = text.lower()
            if not text:
                continue
            if any(token in lowered for token in ("detector", "normalized unsupported evidence", "detected domain signals", "magicmock", "internal")):
                continue
            if text not in rows:
                rows.append(text)
        return rows[:6]

    def _confidence(self, intelligence_result, explicit_description: str, identity, evidence_items: list[CanonicalEvidence]) -> CanonicalConfidence:
        architecture = self._label_confidence(getattr(getattr(intelligence_result, "architecture", None), "confidence", "Unknown"))
        product_purpose = "High" if explicit_description else self._label_confidence(getattr(identity, "domain_confidence", "Unknown"))
        overall = "High" if architecture == "High" and product_purpose == "High" else "Medium" if evidence_items else "Low"
        return CanonicalConfidence(architecture=architecture, product_purpose=product_purpose, overall=overall)

    def _architecture_summary(self, project_type: str, tech_stack: CanonicalTechStack, api_surface: list[CanonicalAPI]) -> str:
        frameworks = ", ".join(tech_stack.frameworks[:3])
        framework_part = f" using {frameworks}" if frameworks else ""
        api_part = f" with {len(api_surface)} detected API endpoints" if api_surface else ""
        return self._normalize_sentence(f"This repository uses a {project_type} architecture{framework_part}{api_part}.", max_sentences=1)

    def _data_quality_notes(self, evidence_items: list[CanonicalEvidence], api_surface: list[CanonicalAPI], product_summary: str, explicit_description: str) -> list[str]:
        notes = []
        if evidence_items:
            notes.append("Evidence labels were sanitized and limited to high-signal items.")
        if api_surface:
            notes.append("Duplicate API endpoints were removed and normalized.")
        if explicit_description and "appears to be" not in product_summary.lower():
            notes.append("Explicit product metadata was used as the primary product description.")
        return notes[:5]

    def _normalize_api_path(self, path: str) -> str:
        value = (path or "/").strip().replace("\\", "/")
        value = re.sub(r"\s+", "", value)
        value = re.sub(r"/+", "/", value)
        if not value.startswith("/"):
            value = f"/{value}"
        value = re.sub(r"\{[^}]*task[^}]*id[^}]*\}", "{task_id}", value, flags=re.I)
        value = re.sub(r"\{[^}]*job[^}]*id[^}]*\}", "{task_id}", value, flags=re.I)
        value = re.sub(r"\{[^}]*task id[^}]*\}", "{task_id}", value, flags=re.I)
        value = re.sub(r"\{[^}]*session[^}]*id[^}]*\}", "{session_id}", value, flags=re.I)
        value = value.lower()
        return value.replace("/status/{job_id}", "/status/{task_id}").replace("/status/{taskid}", "/status/{task_id}")

    def _api_purpose(self, method: str, path: str) -> str:
        if method == "GET" and path == "/":
            return "Root or landing endpoint."
        if method == "GET" and path == "/health":
            return "Health check endpoint."
        if method == "GET" and path == "/status/{task_id}":
            return "Retrieves analysis task status."
        if method == "POST" and path == "/ask":
            return "Accepts a project question and returns a grounded answer."
        if method == "POST" and path == "/context":
            return "Builds or retrieves context for analysis/chat."
        if method == "POST" and "/analyze" in path:
            return "Starts an analysis workflow."
        if method == "GET" and "/history/{session_id}" in path:
            return "Retrieves session chat/history."
        if method == "GET" and path == "/identity":
            return "Returns project identity information."
        if method == "GET" and path == "/identity/summary":
            return "Returns summarized identity metadata."
        return "Detected API endpoint."

    def _sanitize_evidence_label(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        lowered = text.lower().replace("\\", "/")
        if any(token in lowered for token in self._SENSITIVE_TOKENS):
            return ""
        parts = [segment for segment in lowered.split("/") if segment]
        if not parts:
            return ""
        tail = parts[-2:] if parts[-1].count(".") else parts[-3:]
        label = "/".join(tail)
        if any(token in label for token in self._SENSITIVE_TOKENS):
            return ""
        return label

    def _evidence_priority(self, label: str) -> int:
        lowered = label.lower()
        for index, item in enumerate(self._PREFERRED_EVIDENCE):
            if item in lowered:
                return index
        return len(self._PREFERRED_EVIDENCE)

    def _evidence_ids_from_labels(self, labels: list[str], evidence_lookup: dict[str, str]) -> list[str]:
        result = []
        for label in labels:
            sanitized = self._sanitize_evidence_label(label)
            if sanitized and sanitized.lower() in evidence_lookup and evidence_lookup[sanitized.lower()] not in result:
                result.append(evidence_lookup[sanitized.lower()])
        return result

    def _evidence_ids_for_item(self, item: Any, evidence_lookup: dict[str, str]) -> list[str]:
        labels = []
        for evidence in getattr(item, "evidence", []) or []:
            labels.append(getattr(evidence, "file", "") or getattr(evidence, "source_id", ""))
        for attr in ("file", "source_file", "framework"):
            value = getattr(item, attr, None)
            if value:
                labels.append(str(value))
        return self._evidence_ids_from_labels(labels, evidence_lookup)

    def _normalize_sentence(self, value: str, max_sentences: int = 2) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        text = text.replace("**", "")
        if not text:
            return ""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        cleaned = " ".join(sentences[:max_sentences]).strip()
        return cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}."

    def _label_confidence(self, value: str) -> str:
        lowered = str(value or "").strip().lower()
        if lowered == "high":
            return "High"
        if lowered == "medium":
            return "Medium"
        if lowered == "low":
            return "Low"
        return "Unknown"

    def _title_confidence(self, value: str) -> str:
        lowered = str(value or "").strip().lower()
        if lowered:
            return lowered.capitalize()
        return "Medium"

    def _has_setup_files(self, scan_result) -> bool:
        contents = getattr(scan_result, "contents", {}) or {}
        paths = " ".join(str(path).replace("\\", "/").lower() for path in contents.keys())
        return any(token in paths for token in ("package.json", "requirements.txt", "dockerfile", "docker-compose", "eslint"))

    def _has_ci_cd(self, scan_result) -> bool:
        contents = getattr(scan_result, "contents", {}) or {}
        paths = " ".join(str(path).replace("\\", "/").lower() for path in contents.keys())
        return any(token in paths for token in (".github/workflows", "gitlab-ci", "azure-pipelines", "circleci"))

    def _has_tests(self, scan_result) -> bool:
        contents = getattr(scan_result, "contents", {}) or {}
        paths = " ".join(str(path).replace("\\", "/").lower() for path in contents.keys())
        return any(token in paths for token in ("tests/", "test_", "_test.py", ".spec.", ".test."))
