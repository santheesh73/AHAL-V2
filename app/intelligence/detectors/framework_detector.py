"""
AHAL AI — Framework Detector (Phase 2, Step 5)

Detect frameworks from dependencies, imports, config files, and code patterns.
Pure, deterministic, evidence-backed.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from app.intelligence.models import ConfidenceLevel, DetectedDependency, DetectedFramework
from app.intelligence.utils.evidence import dedupe_by_key, make_evidence
from app.intelligence.utils.path_utils import content_for, extension, filename, iter_contents, iter_files
from app.models.file_schema import ScanResult


class FrameworkDetector:
    """Detect frameworks from deps, imports, configs, and code patterns."""

    def detect(
        self,
        scan_result: ScanResult,
        dependencies: Optional[List[DetectedDependency]] = None,
    ) -> List[DetectedFramework]:
        deps = dependencies or []
        dep_names: Set[str] = {d.name.lower() for d in deps}

        candidates: Dict[str, _FrameworkCandidate] = {}

        # ── Phase A: dependency signals ──────────────────────────
        self._check_deps(dep_names, deps, candidates)

        # ── Phase B: file/config signals ─────────────────────────
        self._check_files(scan_result, candidates)

        # ── Phase C: code/import signals ─────────────────────────
        self._check_code(scan_result, candidates)

        # ── Build results ────────────────────────────────────────
        return self._build_results(candidates)

    # ── Dependency checks ────────────────────────────────────────

    def _check_deps(
        self,
        dep_names: Set[str],
        deps: List[DetectedDependency],
        out: Dict[str, _FrameworkCandidate],
    ) -> None:
        dep_fw = {
            # Frontend
            "react": ("React", "frontend"),
            "react-dom": ("React", "frontend"),
            "next": ("Next.js", "frontend"),
            "vue": ("Vue", "frontend"),
            "@angular/core": ("Angular", "frontend"),
            "angular": ("Angular", "frontend"),
            "svelte": ("Svelte", "frontend"),
            "vite": ("Vite", "tooling"),
            # Backend
            "fastapi": ("FastAPI", "backend"),
            "flask": ("Flask", "backend"),
            "django": ("Django", "backend"),
            "express": ("Express", "backend"),
            "@nestjs/core": ("NestJS", "backend"),
            "nestjs": ("NestJS", "backend"),
            "spring-boot": ("Spring Boot", "backend"),
            "laravel/framework": ("Laravel", "backend"),
            # Database
            "pymongo": ("MongoDB", "database"),
            "motor": ("MongoDB", "database"),
            "mongoose": ("MongoDB", "database"),
            "psycopg2": ("PostgreSQL", "database"),
            "psycopg2-binary": ("PostgreSQL", "database"),
            "asyncpg": ("PostgreSQL", "database"),
            "pg": ("PostgreSQL", "database"),
            "redis": ("Redis", "database"),
            "ioredis": ("Redis", "database"),
            # ORM
            "sqlalchemy": ("SQLAlchemy", "orm"),
            "prisma": ("Prisma", "orm"),
            "@prisma/client": ("Prisma", "orm"),
            "typeorm": ("TypeORM", "orm"),
            "sequelize": ("Sequelize", "orm"),
            "mongoose": ("Mongoose", "orm"),
        }

        for dep_name, (fw_name, category) in dep_fw.items():
            if dep_name in dep_names:
                c = out.setdefault(fw_name, _FrameworkCandidate(fw_name, category))
                # Find the matching dep for evidence
                for d in deps:
                    if d.name.lower() == dep_name:
                        c.add_evidence(d.source_file, f"Dependency '{dep_name}' detected", confidence="medium")
                        break

    # ── File/config checks ───────────────────────────────────────

    def _check_files(self, scan_result: ScanResult, out: Dict[str, _FrameworkCandidate]) -> None:
        for fm in iter_files(scan_result):
            fname = filename(fm.path).lower()
            parts_lower = fm.path.lower().replace("\\", "/")

            # Next.js config
            if fname in ("next.config.js", "next.config.ts", "next.config.mjs"):
                c = out.setdefault("Next.js", _FrameworkCandidate("Next.js", "frontend"))
                c.add_evidence(fm.path, "Next.js config file found", confidence="high")

            # Angular config
            if fname == "angular.json":
                c = out.setdefault("Angular", _FrameworkCandidate("Angular", "frontend"))
                c.add_evidence(fm.path, "angular.json found", confidence="high")

            # Vite config
            if fname in ("vite.config.js", "vite.config.ts", "vite.config.mjs"):
                c = out.setdefault("Vite", _FrameworkCandidate("Vite", "tooling"))
                c.add_evidence(fm.path, "Vite config file found", confidence="high")

            # .vue files → Vue
            if extension(fm.path) == ".vue":
                c = out.setdefault("Vue", _FrameworkCandidate("Vue", "frontend"))
                c.add_evidence(fm.path, ".vue component file", confidence="high")

            # Django manage.py
            if fname == "manage.py":
                content = content_for(scan_result, fm.path)
                if content and "django" in content.lower():
                    c = out.setdefault("Django", _FrameworkCandidate("Django", "backend"))
                    c.add_evidence(fm.path, "Django manage.py found", confidence="high")

            # Django settings.py
            if fname == "settings.py" and "django" in parts_lower:
                c = out.setdefault("Django", _FrameworkCandidate("Django", "backend"))
                c.add_evidence(fm.path, "Django settings.py found", confidence="medium")

            # Prisma schema
            if fname == "schema.prisma" or "prisma/schema.prisma" in parts_lower:
                c = out.setdefault("Prisma", _FrameworkCandidate("Prisma", "orm"))
                c.add_evidence(fm.path, "Prisma schema file found", confidence="high")

            # Laravel artisan
            if fname == "artisan":
                c = out.setdefault("Laravel", _FrameworkCandidate("Laravel", "backend"))
                c.add_evidence(fm.path, "Laravel artisan file found", confidence="high")

    # ── Code/import checks ───────────────────────────────────────

    def _check_code(self, scan_result: ScanResult, out: Dict[str, _FrameworkCandidate]) -> None:
        _code_patterns = [
            # FastAPI
            (re.compile(r"from\s+fastapi\s+import|import\s+fastapi"), "FastAPI", "backend", "FastAPI import"),
            (re.compile(r"FastAPI\s*\("), "FastAPI", "backend", "FastAPI() instantiation"),
            # Flask
            (re.compile(r"from\s+flask\s+import|import\s+flask"), "Flask", "backend", "Flask import"),
            (re.compile(r"Flask\s*\(\s*__name__\s*\)"), "Flask", "backend", "Flask(__name__) instantiation"),
            # Django
            (re.compile(r"from\s+django\s+|import\s+django"), "Django", "backend", "Django import"),
            # Express
            (re.compile(r"""require\s*\(\s*['"]express['"]\s*\)"""), "Express", "backend", "require('express')"),
            (re.compile(r"""import\s+express\s+from\s+['"]express['"]"""), "Express", "backend", "import express"),
            # NestJS
            (re.compile(r"NestFactory"), "NestJS", "backend", "NestFactory reference"),
            # React
            (re.compile(r"""from\s+['"]react['"]|import\s+React"""), "React", "frontend", "React import"),
            # Vue
            (re.compile(r"""from\s+['"]vue['"]|import\s+.*\s+from\s+['"]vue['"]"""), "Vue", "frontend", "Vue import"),
            # Spring Boot
            (re.compile(r"@SpringBootApplication"), "Spring Boot", "backend", "@SpringBootApplication annotation"),
            # SQLAlchemy
            (re.compile(r"from\s+sqlalchemy\s+|import\s+sqlalchemy"), "SQLAlchemy", "orm", "SQLAlchemy import"),
            # Mongoose
            (re.compile(r"""require\s*\(\s*['"]mongoose['"]\s*\)|from\s+['"]mongoose['"]"""), "Mongoose", "orm", "Mongoose import"),
            # MongoDB connection strings
            (re.compile(r"mongodb://|mongodb\+srv://"), "MongoDB", "database", "MongoDB connection string"),
            # PostgreSQL connection strings
            (re.compile(r"postgres://|postgresql://"), "PostgreSQL", "database", "PostgreSQL connection string"),
        ]

        for path, content in iter_contents(scan_result):
            # Skip very long files to avoid regex cost
            check_content = content[:50000]
            for pattern, fw_name, category, reason in _code_patterns:
                match = pattern.search(check_content)
                if match:
                    c = out.setdefault(fw_name, _FrameworkCandidate(fw_name, category))
                    snippet = match.group(0)[:100]
                    c.add_evidence(path, reason, snippet=snippet, confidence="high")

    # ── Build results ────────────────────────────────────────────

    def _build_results(self, candidates: Dict[str, _FrameworkCandidate]) -> List[DetectedFramework]:
        results: List[DetectedFramework] = []
        for name, c in sorted(candidates.items()):
            has_code = any(e.confidence == "high" for e in c.evidence)
            has_dep = any("ependency" in e.reason or "ependenc" in e.reason for e in c.evidence)

            if has_code and has_dep:
                confidence: ConfidenceLevel = "high"
            elif has_code:
                confidence = "high"
            elif has_dep:
                confidence = "medium"
            else:
                confidence = "low"

            results.append(DetectedFramework(
                name=name,
                category=c.category,
                confidence=confidence,
                evidence=c.evidence[:10],
            ))
        return results


class _FrameworkCandidate:
    """Internal accumulator for framework signals."""

    __slots__ = ("name", "category", "evidence")

    def __init__(self, name: str, category: str) -> None:
        self.name = name
        self.category = category
        self.evidence: list = []

    def add_evidence(
        self, file: str, reason: str,
        snippet: str | None = None,
        confidence: ConfidenceLevel = "medium",
    ) -> None:
        self.evidence.append(make_evidence(file, reason, snippet, confidence))
