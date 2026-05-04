"""Deterministic context retrieval from scan, intelligence, and graph data."""

from __future__ import annotations

import os

from app.chat.models import EvidenceReference, RetrievedContext
from app.utils.ignored_paths import is_ignored_path

_DEPENDENCY_CONFIG_FILES = {
    "package.json", "requirements.txt", "pyproject.toml", "poetry.lock", "pipfile", "go.mod", "cargo.toml",
}
_PROJECT_ROOT_FILES = {"readme.md", "package.json", "requirements.txt", "pyproject.toml", "main.py", "app.py"}


class ContextRetriever:
    def retrieve(
        self,
        question: str,
        classification,
        scan_result,
        intelligence_result,
        max_items: int = 20,
    ) -> list[RetrievedContext]:
        category = classification.category
        question_text = (question or "").strip()
        question_lc = question_text.lower()
        entities = [entity.lower() for entity in classification.entities]

        items: list[RetrievedContext] = []
        items.extend(self._summary_context(scan_result, intelligence_result))
        items.extend(self._architecture_context(intelligence_result))
        items.extend(self._framework_context(intelligence_result))
        items.extend(self._entrypoint_context(intelligence_result))
        items.extend(self._module_context(intelligence_result))
        items.extend(self._workflow_context(intelligence_result))
        items.extend(self._api_context(intelligence_result))
        items.extend(self._database_context(intelligence_result))
        items.extend(self._dependency_context(intelligence_result))
        items.extend(self._root_file_context(scan_result))
        if category == "file" or entities:
            items.extend(self._file_context(scan_result, question_lc, entities))

        filtered: list[RetrievedContext] = []
        for item in items:
            if self._is_ignored_context(item):
                continue
            if category != "general" and item.category != category and item.category != "general":
                if not self._matches_entities(item, entities) and category not in item.keywords:
                    continue
            if category == "file" and item.source_type != "file" and not self._matches_entities(item, entities):
                continue
            filtered.append(item)

        if not filtered:
            filtered = [item for item in items if not self._is_ignored_context(item) and self._matches_question(item, question_lc, entities)]
        if not filtered and category == "general":
            filtered = [item for item in items if item.context_id in {"project-summary", "architecture-summary"}]

        return filtered[:max_items]

    def _architecture_context(self, intelligence_result) -> list[RetrievedContext]:
        architecture = getattr(intelligence_result, "architecture", None)
        if architecture is None:
            return []
        evidence = [self._from_phase2_evidence("framework", f"architecture:{architecture.type}", ev) for ev in architecture.evidence]
        evidence = [ev for ev in evidence if ev.reason != "Ignored evidence path removed"]
        content_lines = [f"Project type: {architecture.type}", f"Confidence: {architecture.confidence}"]
        if architecture.reasoning:
            content_lines.append("Reasoning: " + "; ".join(architecture.reasoning[:5]))
        return [
            RetrievedContext(
                context_id="architecture-summary",
                title="Architecture Summary",
                content="\n".join(content_lines),
                source_type="framework",
                source_id=f"architecture:{architecture.type}",
                confidence=architecture.confidence,
                category="architecture",
                keywords=["architecture", architecture.type, "overview", "structure"],
                evidence=evidence,
            )
        ]

    def _framework_context(self, intelligence_result) -> list[RetrievedContext]:
        items: list[RetrievedContext] = []
        for framework in getattr(intelligence_result, "frameworks", []) or []:
            evidence = [self._from_phase2_evidence("framework", framework.name, ev) for ev in framework.evidence]
            evidence = [ev for ev in evidence if ev.reason != "Ignored evidence path removed"]
            if not evidence:
                continue
            items.append(
                RetrievedContext(
                    context_id=f"framework-{framework.name.lower()}",
                    title=f"Framework {framework.name}",
                    content=f"Framework {framework.name} detected in category {framework.category}",
                    source_type="framework",
                    source_id=framework.name,
                    confidence=framework.confidence,
                    category="general",
                    keywords=["framework", framework.name.lower(), framework.category.lower()],
                    evidence=evidence,
                )
            )
        return items

    def _entrypoint_context(self, intelligence_result) -> list[RetrievedContext]:
        items: list[RetrievedContext] = []
        for entry in getattr(intelligence_result, "entry_points", []) or []:
            if is_ignored_path(entry.file):
                continue
            evidence = [self._from_phase2_evidence("file", entry.file, ev) for ev in entry.evidence]
            evidence = [ev for ev in evidence if ev.reason != "Ignored evidence path removed"]
            if not evidence:
                continue
            items.append(
                RetrievedContext(
                    context_id=f"entrypoint-{entry.file}",
                    title=f"Entrypoint {entry.file}",
                    content=f"Entrypoint {entry.file} classified as {entry.type}" + (f" using {entry.framework}" if entry.framework else ""),
                    source_type="file",
                    source_id=entry.file,
                    file=entry.file,
                    confidence=entry.confidence,
                    category="general",
                    keywords=["entrypoint", entry.file.lower(), entry.type.lower(), (entry.framework or "").lower()],
                    evidence=evidence,
                )
            )
        return items

    def _workflow_context(self, intelligence_result) -> list[RetrievedContext]:
        workflow = getattr(intelligence_result, "workflow", None)
        if workflow is None:
            return []
        items: list[RetrievedContext] = []
        for step in workflow.steps:
            evidence = [self._from_phase2_evidence("file", f"workflow:{step.order}", ev) for ev in step.evidence]
            evidence = [ev for ev in evidence if ev.reason != "Ignored evidence path removed"]
            items.append(
                RetrievedContext(
                    context_id=f"workflow-step-{step.order}",
                    title=f"Workflow Step {step.order}",
                    content=f"{step.source} -> {step.action}" + (f" -> {step.target}" if step.target else ""),
                    source_type="graph_node",
                    source_id=f"workflow:{step.order}",
                    file=evidence[0].file if evidence else None,
                    confidence=step.confidence,
                    category="workflow",
                    keywords=["workflow", "flow", "execution", step.source.lower(), (step.target or "").lower()],
                    evidence=evidence,
                )
            )
        return items

    def _api_context(self, intelligence_result) -> list[RetrievedContext]:
        items: list[RetrievedContext] = []
        for endpoint in getattr(intelligence_result, "api_endpoints", []) or []:
            if is_ignored_path(endpoint.file):
                continue
            evidence = [self._from_phase2_evidence("api_endpoint", f"{endpoint.method}:{endpoint.path}", ev) for ev in endpoint.evidence]
            evidence = [ev for ev in evidence if ev.reason != "Ignored evidence path removed"]
            content = f"{endpoint.method} {endpoint.path} in {endpoint.file}"
            if endpoint.handler:
                content += f" handled by {endpoint.handler}"
            items.append(
                RetrievedContext(
                    context_id=f"api-{endpoint.method.lower()}-{endpoint.path}",
                    title=f"API {endpoint.method} {endpoint.path}",
                    content=content,
                    source_type="api_endpoint",
                    source_id=f"{endpoint.method}:{endpoint.path}",
                    file=endpoint.file,
                    confidence=endpoint.confidence,
                    category="api",
                    keywords=["api", "endpoint", "route", endpoint.method.lower(), endpoint.path.lower()],
                    evidence=evidence,
                )
            )
        return items

    def _database_context(self, intelligence_result) -> list[RetrievedContext]:
        items: list[RetrievedContext] = []
        for database in getattr(intelligence_result, "databases", []) or []:
            evidence = [self._from_phase2_evidence("database", database.name, ev) for ev in database.evidence]
            evidence = [ev for ev in evidence if ev.reason != "Ignored evidence path removed"]
            items.append(
                RetrievedContext(
                    context_id=f"database-{database.name.lower()}",
                    title=f"Database {database.name}",
                    content=f"{database.name} usage detected as {database.usage}",
                    source_type="database",
                    source_id=database.name,
                    file=evidence[0].file if evidence else None,
                    confidence=database.confidence,
                    category="database",
                    keywords=["database", "db", database.name.lower(), database.usage.lower()],
                    evidence=evidence,
                )
            )
        return items

    def _module_context(self, intelligence_result) -> list[RetrievedContext]:
        items: list[RetrievedContext] = []
        for module in getattr(intelligence_result, "modules", []) or []:
            evidence = [self._from_phase2_evidence("module", module.name, ev) for ev in module.evidence]
            evidence = [ev for ev in evidence if ev.reason != "Ignored evidence path removed"]
            content = f"Module {module.name} ({module.category})"
            allowed_files = [path for path in module.files if not is_ignored_path(path)]
            if allowed_files:
                content += f" contains files: {', '.join(allowed_files[:5])}"
            items.append(
                RetrievedContext(
                    context_id=f"module-{module.name}",
                    title=f"Module {module.name}",
                    content=content,
                    source_type="module",
                    source_id=module.name,
                    confidence=module.confidence,
                    category="module",
                    keywords=["module", "layer", "service", module.name.lower(), module.category.lower()],
                    evidence=evidence,
                )
            )
        return items

    def _dependency_context(self, intelligence_result) -> list[RetrievedContext]:
        items: list[RetrievedContext] = []
        for dep in getattr(intelligence_result, "dependencies", []) or []:
            source_file = getattr(dep, "source_file", "")
            if is_ignored_path(source_file) or os.path.basename(source_file).lower() not in _DEPENDENCY_CONFIG_FILES:
                continue
            evidence = [self._from_phase2_evidence("framework", dep.name, ev) for ev in dep.evidence]
            evidence = [ev for ev in evidence if ev.reason != "Ignored evidence path removed"]
            items.append(
                RetrievedContext(
                    context_id=f"dependency-{dep.ecosystem}-{dep.name}",
                    title=f"Dependency {dep.name}",
                    content=f"{dep.name} ({dep.ecosystem}) declared in {dep.source_file}",
                    source_type="framework",
                    source_id=dep.name,
                    file=dep.source_file,
                    confidence=dep.confidence,
                    category="dependency",
                    keywords=["dependency", "package", "library", dep.name.lower(), dep.ecosystem.lower()],
                    evidence=evidence,
                )
            )
        return items

    def _root_file_context(self, scan_result) -> list[RetrievedContext]:
        items: list[RetrievedContext] = []
        for path, content in (getattr(scan_result, "contents", {}) or {}).items():
            if is_ignored_path(path):
                continue
            basename = os.path.basename(path).lower()
            if basename not in _PROJECT_ROOT_FILES:
                continue
            snippet = self._make_snippet(content)
            items.append(
                RetrievedContext(
                    context_id=f"project-file-{path}",
                    title=f"Project file {path}",
                    content=f"Project file {path}\nSnippet:\n{snippet}",
                    source_type="file",
                    source_id=path,
                    file=path,
                    confidence="high",
                    category="general",
                    keywords=["project", "config", basename],
                    evidence=[
                        EvidenceReference(
                            source_type="file",
                            source_id=path,
                            file=path,
                            reason="Project root/config file scanned in Phase 1",
                            snippet=snippet,
                            confidence="high",
                        )
                    ],
                )
            )
        return items

    def _file_context(self, scan_result, question_lc: str, entities: list[str]) -> list[RetrievedContext]:
        items: list[RetrievedContext] = []
        for path, content in (getattr(scan_result, "contents", {}) or {}).items():
            path_lc = path.lower()
            if is_ignored_path(path_lc):
                continue
            if entities and not any(entity in path_lc for entity in entities) and path_lc not in question_lc:
                continue
            snippet = self._make_snippet(content)
            items.append(
                RetrievedContext(
                    context_id=f"file-{path}",
                    title=f"File {path}",
                    content=f"File path: {path}\nSnippet:\n{snippet}",
                    source_type="file",
                    source_id=path,
                    file=path,
                    confidence="high",
                    category="file",
                    keywords=["file", "where", path_lc],
                    evidence=[
                        EvidenceReference(
                            source_type="file",
                            source_id=path,
                            file=path,
                            reason="Phase 1 scanned file content",
                            snippet=snippet,
                            confidence="high",
                        )
                    ],
                )
            )
        return items

    def _summary_context(self, scan_result, intelligence_result) -> list[RetrievedContext]:
        framework_names = ", ".join(item.name for item in getattr(intelligence_result, "frameworks", [])[:5]) or "none detected"
        module_names = ", ".join(item.name for item in getattr(intelligence_result, "modules", [])[:5]) or "none detected"
        entry_points = ", ".join(item.file for item in getattr(intelligence_result, "entry_points", [])[:5] if not is_ignored_path(item.file)) or "none detected"
        architecture = getattr(getattr(intelligence_result, "architecture", None), "type", "unknown")
        evidence = [
            self._from_phase2_evidence("framework", f"architecture:{architecture}", ev)
            for ev in getattr(getattr(intelligence_result, "architecture", None), "evidence", [])
        ]
        evidence = [ev for ev in evidence if ev.reason != "Ignored evidence path removed"]
        return [
            RetrievedContext(
                context_id="project-summary",
                title="Project Summary",
                content=(
                    f"Architecture: {architecture}\n"
                    f"Files scanned: {len([f for f in getattr(scan_result, 'files', []) or [] if not is_ignored_path(getattr(f, 'path', ''))])}\n"
                    f"Frameworks: {framework_names}\n"
                    f"Entry points: {entry_points}\n"
                    f"Modules: {module_names}"
                ),
                source_type="framework",
                source_id="project-summary",
                confidence="medium",
                category="general",
                keywords=["project", "general", "overview"],
                evidence=evidence,
            )
        ]

    def _from_phase2_evidence(self, source_type: str, source_id: str, ev) -> EvidenceReference:
        file = getattr(ev, "file", None)
        if file and is_ignored_path(file):
            return EvidenceReference(
                source_type=source_type,
                source_id=source_id,
                reason="Ignored evidence path removed",
                confidence="low",
            )
        return EvidenceReference(
            source_type=source_type,
            source_id=source_id,
            file=file,
            reason=getattr(ev, "reason", ""),
            snippet=self._make_snippet(getattr(ev, "snippet", None)),
            confidence=getattr(ev, "confidence", "medium"),
        )

    def _matches_question(self, item: RetrievedContext, question_lc: str, entities: list[str]) -> bool:
        haystacks = [item.title.lower(), item.content.lower(), item.source_id.lower(), *(keyword.lower() for keyword in item.keywords)]
        return any(part and part in " ".join(haystacks) for part in entities) or any(
            keyword and keyword in question_lc for keyword in item.keywords
        )

    def _matches_entities(self, item: RetrievedContext, entities: list[str]) -> bool:
        blob = " ".join([item.title.lower(), item.content.lower(), item.source_id.lower(), item.file.lower() if item.file else ""])
        return any(entity in blob for entity in entities)

    def _make_snippet(self, text: str | None, limit: int = 240) -> str | None:
        if not text:
            return None
        compact = text.strip()
        if len(compact) <= limit:
            return compact
        return compact[:limit].rstrip() + "..."

    def _is_ignored_context(self, item: RetrievedContext) -> bool:
        if item.file and is_ignored_path(item.file):
            return True
        if item.source_type == "file" and is_ignored_path(item.source_id):
            return True
        item.evidence = [ev for ev in item.evidence if not (ev.file and is_ignored_path(ev.file))]
        return False
