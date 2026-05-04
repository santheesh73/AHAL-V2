"""
AHAL AI — Dependency Detector (Phase 2, Step 4)

Parse dependencies from manifest files.
Pure, deterministic, evidence-backed.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Set, Tuple

from app.intelligence.models import ConfidenceLevel, DetectedDependency
from app.intelligence.utils.evidence import dedupe_by_key, make_evidence
from app.intelligence.utils.path_utils import content_for, filename, iter_files
from app.models.file_schema import ScanResult

# ── Category classification ───────────────────────────────────────

_CATEGORY_MAP: Dict[str, str] = {
    # Frontend
    "react": "frontend", "react-dom": "frontend", "vue": "frontend",
    "angular": "frontend", "@angular/core": "frontend", "@angular/common": "frontend",
    "next": "frontend", "nuxt": "frontend", "svelte": "frontend",
    "vite": "frontend", "webpack": "tooling", "parcel": "tooling",
    "tailwindcss": "frontend", "bootstrap": "frontend",
    # Backend
    "fastapi": "backend", "flask": "backend", "django": "backend",
    "express": "backend", "nestjs": "backend", "@nestjs/core": "backend",
    "spring-boot": "backend", "gin": "backend", "actix-web": "backend",
    "koa": "backend", "hapi": "backend", "starlette": "backend",
    "uvicorn": "backend", "gunicorn": "backend",
    # Database
    "pymongo": "database", "motor": "database", "mongoose": "database",
    "mongodb": "database", "pg": "database", "psycopg2": "database",
    "psycopg2-binary": "database", "asyncpg": "database",
    "mysql": "database", "mysql2": "database", "pymysql": "database",
    "mysqlclient": "database", "sqlite3": "database",
    "redis": "database", "ioredis": "database",
    "firebase": "database", "firebase-admin": "database",
    # ORM
    "sqlalchemy": "orm", "prisma": "orm", "@prisma/client": "orm",
    "typeorm": "orm", "sequelize": "orm", "drizzle-orm": "orm",
    "tortoise-orm": "orm", "peewee": "orm", "alembic": "orm",
    # Testing
    "pytest": "testing", "jest": "testing", "vitest": "testing",
    "mocha": "testing", "chai": "testing", "unittest": "testing",
    "cypress": "testing", "playwright": "testing",
    # Tooling
    "eslint": "tooling", "prettier": "tooling", "black": "tooling",
    "ruff": "tooling", "mypy": "tooling", "isort": "tooling",
    "babel": "tooling", "typescript": "tooling",
}


def _categorize(name: str) -> str:
    lower = name.lower().strip()
    return _CATEGORY_MAP.get(lower, "unknown")


class DependencyDetector:
    """Detect dependencies from manifest/config files in ScanResult."""

    def detect(self, scan_result: ScanResult) -> List[DetectedDependency]:
        deps: List[DetectedDependency] = []

        for fm in iter_files(scan_result):
            fname = filename(fm.path).lower()
            content = content_for(scan_result, fm.path)
            if content is None:
                continue

            try:
                if fname == "package.json":
                    deps.extend(self._parse_package_json(content, fm.path))
                elif fname == "requirements.txt":
                    deps.extend(self._parse_requirements_txt(content, fm.path))
                elif fname == "pyproject.toml":
                    deps.extend(self._parse_pyproject_toml(content, fm.path))
                elif fname == "pipfile":
                    deps.extend(self._parse_pipfile(content, fm.path))
                elif fname == "go.mod":
                    deps.extend(self._parse_go_mod(content, fm.path))
                elif fname == "cargo.toml":
                    deps.extend(self._parse_cargo_toml(content, fm.path))
                elif fname == "composer.json":
                    deps.extend(self._parse_composer_json(content, fm.path))
                elif fname == "gemfile":
                    deps.extend(self._parse_gemfile(content, fm.path))
                elif fname in ("pom.xml", "build.gradle"):
                    deps.extend(self._parse_jvm_build(content, fm.path, fname))
            except Exception:
                continue

        return dedupe_by_key(deps, lambda d: (d.name.lower(), d.ecosystem))

    # ── Parsers ──────────────────────────────────────────────────

    def _parse_package_json(self, content: str, path: str) -> List[DetectedDependency]:
        out: List[DetectedDependency] = []
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, Exception):
            return out

        for section in ("dependencies", "devDependencies", "peerDependencies"):
            dep_dict = data.get(section)
            if not isinstance(dep_dict, dict):
                continue
            for name in dep_dict:
                out.append(DetectedDependency(
                    name=str(name),
                    ecosystem="npm",
                    source_file=path,
                    category=_categorize(name),
                    confidence="high",
                    evidence=[make_evidence(
                        file=path,
                        reason=f"Listed in {section}",
                        snippet=f'"{name}": "{dep_dict[name]}"',
                        confidence="high",
                    )],
                ))
        return out

    def _parse_requirements_txt(self, content: str, path: str) -> List[DetectedDependency]:
        out: List[DetectedDependency] = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            # Extract name before version specifiers
            match = re.match(r"^([A-Za-z0-9_][A-Za-z0-9_.+-]*)", line)
            if match:
                name = match.group(1)
                out.append(DetectedDependency(
                    name=name,
                    ecosystem="pip",
                    source_file=path,
                    category=_categorize(name),
                    confidence="high",
                    evidence=[make_evidence(
                        file=path,
                        reason="Listed in requirements.txt",
                        snippet=line[:120],
                        confidence="high",
                    )],
                ))
        return out

    def _parse_pyproject_toml(self, content: str, path: str) -> List[DetectedDependency]:
        out: List[DetectedDependency] = []
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("["):
                in_deps = "dependencies" in stripped.lower()
                continue
            if in_deps and stripped and not stripped.startswith("#"):
                # "name>=version" or "name" or name = "version"
                match = re.match(r'^"?([A-Za-z0-9_][A-Za-z0-9_.+-]*)', stripped)
                if match:
                    name = match.group(1)
                    out.append(DetectedDependency(
                        name=name,
                        ecosystem="pip",
                        source_file=path,
                        category=_categorize(name),
                        confidence="medium",
                        evidence=[make_evidence(
                            file=path,
                            reason="Listed in pyproject.toml dependencies",
                            snippet=stripped[:120],
                            confidence="medium",
                        )],
                    ))
        return out

    def _parse_pipfile(self, content: str, path: str) -> List[DetectedDependency]:
        out: List[DetectedDependency] = []
        in_packages = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("["):
                in_packages = "packages" in stripped.lower()
                continue
            if in_packages and "=" in stripped and not stripped.startswith("#"):
                name = stripped.split("=")[0].strip().strip('"').strip("'")
                if name:
                    out.append(DetectedDependency(
                        name=name,
                        ecosystem="pip",
                        source_file=path,
                        category=_categorize(name),
                        confidence="medium",
                        evidence=[make_evidence(path, "Listed in Pipfile", stripped[:120], "medium")],
                    ))
        return out

    def _parse_go_mod(self, content: str, path: str) -> List[DetectedDependency]:
        out: List[DetectedDependency] = []
        in_require = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("require ("):
                in_require = True
                continue
            if in_require and stripped == ")":
                in_require = False
                continue
            if stripped.startswith("require ") and "(" not in stripped:
                parts = stripped.split()
                if len(parts) >= 2:
                    name = parts[1]
                    out.append(DetectedDependency(
                        name=name, ecosystem="go", source_file=path,
                        category=_categorize(name.split("/")[-1]),
                        confidence="high",
                        evidence=[make_evidence(path, "Listed in go.mod require", stripped[:120], "high")],
                    ))
            elif in_require and stripped and not stripped.startswith("//"):
                parts = stripped.split()
                if parts:
                    name = parts[0]
                    out.append(DetectedDependency(
                        name=name, ecosystem="go", source_file=path,
                        category=_categorize(name.split("/")[-1]),
                        confidence="high",
                        evidence=[make_evidence(path, "Listed in go.mod require block", stripped[:120], "high")],
                    ))
        return out

    def _parse_cargo_toml(self, content: str, path: str) -> List[DetectedDependency]:
        out: List[DetectedDependency] = []
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("["):
                in_deps = stripped.lower() in ("[dependencies]", "[dev-dependencies]", "[build-dependencies]")
                continue
            if in_deps and "=" in stripped and not stripped.startswith("#"):
                name = stripped.split("=")[0].strip()
                if name and not name.startswith("["):
                    out.append(DetectedDependency(
                        name=name, ecosystem="cargo", source_file=path,
                        category=_categorize(name),
                        confidence="high",
                        evidence=[make_evidence(path, "Listed in Cargo.toml [dependencies]", stripped[:120], "high")],
                    ))
        return out

    def _parse_composer_json(self, content: str, path: str) -> List[DetectedDependency]:
        out: List[DetectedDependency] = []
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, Exception):
            return out
        for section in ("require", "require-dev"):
            dep_dict = data.get(section)
            if not isinstance(dep_dict, dict):
                continue
            for name, version in dep_dict.items():
                if name == "php":
                    continue
                out.append(DetectedDependency(
                    name=str(name), ecosystem="composer", source_file=path,
                    category=_categorize(name.split("/")[-1]),
                    confidence="high",
                    evidence=[make_evidence(path, f"Listed in composer.json {section}", f'"{name}": "{version}"', "high")],
                ))
        return out

    def _parse_gemfile(self, content: str, path: str) -> List[DetectedDependency]:
        out: List[DetectedDependency] = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            match = re.match(r"""gem\s+['"]([^'"]+)['"]""", stripped)
            if match:
                name = match.group(1)
                out.append(DetectedDependency(
                    name=name, ecosystem="rubygems", source_file=path,
                    category=_categorize(name),
                    confidence="high",
                    evidence=[make_evidence(path, "Listed in Gemfile", stripped[:120], "high")],
                ))
        return out

    def _parse_jvm_build(self, content: str, path: str, fname: str) -> List[DetectedDependency]:
        out: List[DetectedDependency] = []
        ecosystem = "maven" if fname == "pom.xml" else "gradle"

        if fname == "pom.xml":
            # Extract artifactIds from <dependency><artifactId>...</artifactId>
            for match in re.finditer(r"<artifactId>\s*([^<]+?)\s*</artifactId>", content):
                name = match.group(1)
                out.append(DetectedDependency(
                    name=name, ecosystem=ecosystem, source_file=path,
                    category=_categorize(name),
                    confidence="high",
                    evidence=[make_evidence(path, "Listed in pom.xml", name, "high")],
                ))
        else:
            # Gradle: implementation 'group:artifact:version' or implementation "group:artifact:version"
            for match in re.finditer(r"""(?:implementation|api|compile|testImplementation)\s+['"]([^'"]+)['"]""", content):
                dep_str = match.group(1)
                parts = dep_str.split(":")
                name = parts[1] if len(parts) >= 2 else parts[0]
                out.append(DetectedDependency(
                    name=name, ecosystem=ecosystem, source_file=path,
                    category=_categorize(name),
                    confidence="high",
                    evidence=[make_evidence(path, "Listed in build.gradle", dep_str[:120], "high")],
                ))
        return out
