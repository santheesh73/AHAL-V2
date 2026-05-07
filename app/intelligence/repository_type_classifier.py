from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field


RepositoryType = Literal[
    "application",
    "backend_service",
    "frontend_app",
    "fullstack_app",
    "mobile_app",
    "cli_tool",
    "python_package",
    "npm_package",
    "component_library",
    "sdk",
    "plugin",
    "browser_extension",
    "vscode_extension",
    "ml_model_repo",
    "data_science_notebooks",
    "dataset",
    "documentation",
    "curriculum",
    "knowledge_base",
    "template",
    "infrastructure",
    "devops_automation",
    "design_assets",
    "research_code",
    "monorepo",
    "mixed",
    "unknown",
]
ConfidenceLevel = Literal["high", "medium", "low"]


class RepositoryTypeResult(BaseModel):
    repo_type: RepositoryType = "unknown"
    secondary_types: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "low"
    reasoning: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    detected_runtime: bool = False
    detected_distribution: bool = False
    detected_docs_only: bool = False


_DOC_SIGNALS = ("documentation", "handbook", "guide", "reference", "resources", "awesome list")
_CURRICULUM_SIGNALS = ("study plan", "curriculum", "interview preparation", "learning path", "syllabus", "roadmap")
_DATASET_SIGNALS = (".csv", ".parquet", ".jsonl", "dataset", "metadata.json", "data dictionary", "schema")
_ML_SIGNALS = ("model", "checkpoint", "inference", "training", "huggingface", "transformers", "pytorch", "tensorfl")
_RESEARCH_SIGNALS = ("paper", "arxiv", "experiment", "reproduc", "benchmark", "ablation")
_INFRA_SIGNALS = (".tf", "terraform", "helm", "kubernetes", "k8s", "terraform.tfstate")
_DEVOPS_SIGNALS = ("github actions", "ansible", "playbook", "pipeline", "ci/cd", "workflow automation")
_DESIGN_SIGNALS = (".fig", ".sketch", ".psd", ".ai", ".xd", "design system", "asset pack")
_TEMPLATE_SIGNALS = ("template", "starter", "boilerplate", "starter kit", "scaffold")


def is_documentation_repo_type(repo_type: str) -> bool:
    return str(repo_type or "").lower() in {"documentation", "curriculum", "knowledge_base"}


def is_package_like_repo_type(repo_type: str) -> bool:
    return str(repo_type or "").lower() in {"python_package", "npm_package", "component_library", "sdk"}


def archetype_display_name(repo_type: str) -> str:
    return str(repo_type or "unknown").replace("_", " ").strip().title()


def documentation_domain_for_repo_type(repo_type: str, explicit_description: str = "") -> str:
    lowered = str(explicit_description or "").lower()
    normalized = str(repo_type or "").lower()
    if normalized == "curriculum":
        if "software engineer" in lowered or "software engineering" in lowered:
            return "software engineering education"
        return "education"
    domain_map = {
        "documentation": "documentation",
        "knowledge_base": "knowledge base",
        "dataset": "dataset",
        "template": "developer template",
        "design_assets": "design assets",
        "research_code": "research software",
    }
    return domain_map.get(normalized, "software project")


def documentation_project_type(repo_type: str) -> str:
    normalized = str(repo_type or "").lower()
    if normalized in {
        "documentation",
        "curriculum",
        "knowledge_base",
        "dataset",
        "template",
        "design_assets",
        "research_code",
        "data_science_notebooks",
        "ml_model_repo",
        "python_package",
        "npm_package",
        "component_library",
        "sdk",
        "cli_tool",
        "browser_extension",
        "vscode_extension",
        "plugin",
        "mobile_app",
        "infrastructure",
        "devops_automation",
        "monorepo",
        "mixed",
    }:
        return normalized
    return "unknown"


def looks_like_markdown_document(path: str) -> bool:
    return bool(re.search(r"\.(md|mdx|rst|txt)$", str(path or "").lower()))


class RepositoryTypeClassifier:
    def classify(self, scan_result=None, intelligence_result=None, product_identity=None) -> RepositoryTypeResult:
        contents = getattr(scan_result, "contents", {}) or {}
        all_paths = [str(path or "").replace("\\", "/") for path in contents.keys()]
        path_text = " ".join(path.lower() for path in all_paths)
        docs_text = self._collect_docs_text(contents)
        package_json = self._package_json(contents)
        pyproject_text = self._file_text(contents, "pyproject.toml")
        readme_title = self._readme_title(contents)

        architecture = str(getattr(getattr(intelligence_result, "architecture", None), "type", "") or "").lower()
        frameworks = [str(getattr(item, "name", item) or "").lower() for item in getattr(intelligence_result, "frameworks", []) or []]
        dependencies = [str(getattr(item, "name", item) or "").lower() for item in getattr(intelligence_result, "dependencies", []) or []]
        api_count = len(getattr(intelligence_result, "api_endpoints", []) or [])
        entry_points = [str(getattr(item, "file", "") or "").lower() for item in getattr(intelligence_result, "entry_points", []) or []]

        detected_runtime = bool(api_count or entry_points or architecture in {"frontend", "backend", "fullstack", "cli", "microservices"})
        detected_distribution = bool(package_json or pyproject_text or any(path.endswith(("setup.py", "setup.cfg")) for path in all_paths))
        markdown_paths = [path for path in all_paths if looks_like_markdown_document(path)]
        code_paths = [path for path in all_paths if path.lower().endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs", ".rb", ".php", ".ipynb"))]
        detected_docs_only = bool(markdown_paths and not code_paths and not detected_runtime)
        evidence_ids = self._evidence_ids(all_paths)

        scores: dict[str, int] = {}
        reasons: dict[str, list[str]] = {}

        def score(repo_type: str, points: int, reason: str) -> None:
            scores[repo_type] = scores.get(repo_type, 0) + points
            reasons.setdefault(repo_type, []).append(reason)

        combined_runtime_text = " ".join(frameworks + dependencies + entry_points)

        if architecture == "fullstack":
            score("fullstack_app", 8, "Architecture classifier detected a fullstack runtime.")
        if architecture == "backend":
            score("backend_service", 8, "Architecture classifier detected a backend runtime.")
        if architecture == "frontend":
            score("frontend_app", 8, "Architecture classifier detected a frontend runtime.")
        if architecture == "cli":
            score("cli_tool", 10, "Architecture classifier detected a CLI runtime.")
        if architecture == "library":
            score("python_package", 6, "Architecture classifier detected a library/package pattern.")
        if "console_scripts" in pyproject_text.lower() or "[project.scripts]" in pyproject_text.lower() or any(token in docs_text for token in ("command-line tool", "cli tool", "command line tool")):
            score("cli_tool", 12, "CLI packaging or command-line documentation was detected.")

        if any(token in combined_runtime_text for token in ("fastapi", "flask", "django", "express", "nestjs", "spring")) or api_count:
            score("backend_service", 6, "Backend framework or HTTP API evidence was detected.")
        if any(token in combined_runtime_text for token in ("react", "next", "vite", "vue", "angular", "svelte")):
            score("frontend_app", 6, "Frontend framework evidence was detected.")
        if scores.get("backend_service") and scores.get("frontend_app"):
            score("fullstack_app", 5, "Both frontend and backend evidence were detected.")

        mobile_tokens = ("androidmanifest.xml", "ios/", "xcodeproj", "react-native", "flutter")
        mobile_detected = any(token in path_text or token in docs_text for token in mobile_tokens) or bool(re.search(r"\bexpo\b", docs_text))
        if mobile_detected:
            score("mobile_app", 10, "Mobile application files or frameworks were detected.")

        if package_json and package_json.get("engines", {}).get("vscode"):
            score("vscode_extension", 12, "VS Code extension metadata was detected in package.json.")
        if package_json and package_json.get("contributes", {}).get("commands"):
            score("vscode_extension", 4, "VS Code contributed commands were detected.")
        if any(path.endswith("manifest.json") for path in all_paths):
            manifest_text = self._file_text(contents, "manifest.json").lower()
            if any(token in manifest_text for token in ('"manifest_version"', '"background"', '"content_scripts"', '"permissions"')):
                score("browser_extension", 12, "Browser extension manifest signals were detected.")
        if any(token in path_text for token in ("plugin.json", ".codex-plugin", "/plugins/")):
            score("plugin", 10, "Plugin manifest or plugin directory structure was detected.")

        if self._has_python_package_signals(all_paths, pyproject_text, docs_text):
            score("python_package", 10, "Python packaging metadata was detected.")
        if package_json and any(key in package_json for key in ("main", "module", "exports", "types", "typings")):
            score("npm_package", 8, "npm package distribution metadata was detected.")
        if package_json and (package_json.get("peerDependencies", {}).get("react") or "src/components" in path_text):
            score("component_library", 10, "Component-library style packaging and React component structure were detected.")
        if package_json and any(key in package_json for key in ("main", "module", "exports", "types", "typings")) and not any(
            token in combined_runtime_text for token in ("react", "next", "vite", "vue", "angular", "svelte")
        ) and not any(path.endswith((".tsx", ".jsx")) or "src/pages" in path for path in all_paths):
            score("npm_package", 4, "Package export metadata was stronger than standalone frontend application evidence.")
        if any(token in docs_text or token in path_text for token in ("sdk", "client", "openapi", "generated client")):
            score("sdk", 8, "SDK/client distribution signals were detected.")

        curriculum_detected = any(token in docs_text for token in _CURRICULUM_SIGNALS)
        documentation_detected = any(token in docs_text for token in _DOC_SIGNALS)
        if curriculum_detected and not detected_runtime:
            score("curriculum", 12, "Curriculum or study-plan language was detected without runtime evidence.")
        if documentation_detected and not detected_runtime:
            score("documentation", 10, "Documentation-focused language was detected without runtime evidence.")
        if any(token in docs_text for token in ("knowledge base", "kb", "reference")) and not detected_runtime:
            score("knowledge_base", 10, "Knowledge-base style documentation was detected without runtime evidence.")
        if detected_docs_only and not curriculum_detected:
            score("documentation", 5, "Repository is dominated by documentation files with no runtime evidence.")

        if any(token in docs_text or token in path_text for token in _DATASET_SIGNALS):
            score("dataset", 10, "Dataset files or metadata signals were detected.")
        if any(token in docs_text or token in path_text for token in _ML_SIGNALS):
            score("ml_model_repo", 8, "ML/model repository signals were detected.")
        if any(path.lower().endswith(".ipynb") for path in all_paths):
            score("data_science_notebooks", 8, "Notebook files were detected.")
        if any(token in docs_text or token in path_text for token in _RESEARCH_SIGNALS):
            score("research_code", 7, "Research-oriented signals were detected.")
        if any(token in docs_text or token in path_text for token in _INFRA_SIGNALS):
            score("infrastructure", 10, "Infrastructure-as-code signals were detected.")
        if any(token in docs_text or token in path_text for token in _DEVOPS_SIGNALS):
            score("devops_automation", 7, "DevOps automation signals were detected.")
        if any(token in docs_text or token in path_text for token in _DESIGN_SIGNALS):
            score("design_assets", 10, "Design or asset-source signals were detected.")
        if any(token in docs_text for token in _TEMPLATE_SIGNALS):
            score("template", 9, "Starter/template language was detected.")
        if package_json and package_json.get("workspaces"):
            score("monorepo", 8, "Package workspaces were detected.")
        if any(token in path_text for token in ("/packages/", "/apps/", "/services/")) and len({path.split("/")[0] for path in all_paths if "/" in path}) >= 2:
            score("monorepo", 5, "Repository layout suggests multiple packaged subprojects.")

        # avoid over-classifying docs when runtime/package evidence exists
        if detected_runtime or detected_distribution:
            scores["documentation"] = max(0, scores.get("documentation", 0) - 6)
            scores["curriculum"] = max(0, scores.get("curriculum", 0) - 6)
        if detected_distribution and not any(
            token in combined_runtime_text for token in ("react", "next", "vite", "vue", "angular", "svelte")
        ) and not any(path.endswith((".tsx", ".jsx")) or "src/pages" in path for path in all_paths):
            scores["frontend_app"] = max(0, scores.get("frontend_app", 0) - 4)

        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if not ordered:
            return RepositoryTypeResult(
                repo_type="unknown",
                secondary_types=[],
                confidence="low",
                reasoning=["Repository type could not be determined confidently from the available evidence."],
                evidence_ids=evidence_ids,
                detected_runtime=detected_runtime,
                detected_distribution=detected_distribution,
                detected_docs_only=detected_docs_only,
            )

        top_type, top_score = ordered[0]
        secondary = [name for name, score_value in ordered[1:4] if score_value >= max(4, top_score - 3) and name != top_type]
        if len(secondary) >= 2 and top_score - ordered[1][1] <= 1 and top_score < 10:
            top_type = "mixed"
            secondary = [name for name, score_value in ordered[:4] if score_value >= 4]

        confidence: ConfidenceLevel
        if top_score >= 12:
            confidence = "high"
        elif top_score >= 7:
            confidence = "medium"
        else:
            confidence = "low"

        return RepositoryTypeResult(
            repo_type=top_type,  # type: ignore[arg-type]
            secondary_types=secondary,
            confidence=confidence,
            reasoning=clean_reasoning(reasons.get(top_type, []), ordered),
            evidence_ids=evidence_ids,
            detected_runtime=detected_runtime,
            detected_distribution=detected_distribution,
            detected_docs_only=detected_docs_only,
        )

    def _collect_docs_text(self, contents: dict[str, object]) -> str:
        chunks: list[str] = []
        for path, value in contents.items():
            lowered = str(path).replace("\\", "/").lower()
            if lowered.endswith(("readme.md", "readme.mdx", "package.json", "pyproject.toml", "manifest.json")) or "/docs/" in lowered:
                chunks.append(self._to_text(value)[:5000])
        return " ".join(chunks).lower()

    def _package_json(self, contents: dict[str, object]) -> dict[str, object]:
        for path, value in contents.items():
            if str(path).replace("\\", "/").lower().endswith("package.json"):
                try:
                    return json.loads(self._to_text(value) or "{}")
                except Exception:
                    return {}
        return {}

    def _readme_title(self, contents: dict[str, object]) -> str:
        for path, value in contents.items():
            lowered = str(path).replace("\\", "/").lower()
            if lowered in {"readme.md", "readme.mdx"}:
                for line in self._to_text(value).splitlines():
                    if line.strip().startswith("# "):
                        return line.strip()[2:].strip()
        return ""

    def _file_text(self, contents: dict[str, object], name: str) -> str:
        for path, value in contents.items():
            if str(path).replace("\\", "/").lower().endswith(name.lower()):
                return self._to_text(value)
        return ""

    def _evidence_ids(self, paths: list[str]) -> list[str]:
        preferred = []
        for path in paths:
            lowered = path.lower()
            if any(token in lowered for token in ("readme.md", "package.json", "pyproject.toml", "manifest.json", "main.tf", "docker-compose", "setup.py")):
                preferred.append(path.split("/")[-1] if "/" in path else path)
        if not preferred and paths:
            preferred = [path.split("/")[-1] if "/" in path else path for path in paths[:4]]
        deduped: list[str] = []
        for item in preferred:
            if item not in deduped:
                deduped.append(item)
        return deduped[:4]

    def _has_python_package_signals(self, paths: list[str], pyproject_text: str, docs_text: str) -> bool:
        path_text = " ".join(path.lower() for path in paths)
        return bool(
            "setup.py" in path_text
            or "setup.cfg" in path_text
            or "[project]" in pyproject_text.lower()
            or "[tool.poetry]" in pyproject_text.lower()
            or "console_scripts" in pyproject_text.lower()
            or "python package" in docs_text
        )

    def _to_text(self, value: object) -> str:
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8", errors="ignore")
        return str(value or "")


def clean_reasoning(primary: list[str], ordered: list[tuple[str, int]]) -> list[str]:
    rows = list(dict.fromkeys(primary))
    if ordered:
        rows.append(f"Top archetype score: {ordered[0][0]} ({ordered[0][1]}).")
    return rows[:6]
