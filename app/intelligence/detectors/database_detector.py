"""
AHAL AI — Database Detector (Phase 2, Step 8)

Detect databases and data stores from dependencies, connection strings, imports, and config.
Pure, deterministic, evidence-backed.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from app.intelligence.models import ConfidenceLevel, DetectedDatabase, DetectedDependency, DetectedFramework
from app.intelligence.utils.evidence import dedupe_by_key, make_evidence
from app.intelligence.utils.path_utils import iter_contents
from app.models.file_schema import ScanResult


class DatabaseDetector:
    """Detect databases from deps, connection strings, imports, and config."""

    def detect(
        self,
        scan_result: ScanResult,
        dependencies: Optional[List[DetectedDependency]] = None,
        frameworks: Optional[List[DetectedFramework]] = None,
    ) -> List[DetectedDatabase]:
        deps = dependencies or []
        fws = frameworks or []
        dep_names: Set[str] = {d.name.lower() for d in deps}
        fw_names: Set[str] = {f.name.lower() for f in fws}

        candidates: Dict[str, _DBCandidate] = {}

        # ── Phase A: dependency signals ──────────────────────────
        self._check_deps(dep_names, deps, candidates)

        # ── Phase B: framework signals ───────────────────────────
        self._check_frameworks(fw_names, fws, candidates)

        # ── Phase C: code/connection string signals ──────────────
        self._check_code(scan_result, candidates)

        return self._build_results(candidates)

    # ── Dependency checks ────────────────────────────────────────

    def _check_deps(
        self,
        dep_names: Set[str],
        deps: List[DetectedDependency],
        out: Dict[str, _DBCandidate],
    ) -> None:
        dep_db = {
            # MongoDB
            "pymongo": ("MongoDB", "direct"),
            "motor": ("MongoDB", "direct"),
            "mongoose": ("MongoDB", "orm"),
            "mongodb": ("MongoDB", "direct"),
            # PostgreSQL
            "psycopg2": ("PostgreSQL", "direct"),
            "psycopg2-binary": ("PostgreSQL", "direct"),
            "asyncpg": ("PostgreSQL", "direct"),
            "pg": ("PostgreSQL", "direct"),
            # MySQL
            "pymysql": ("MySQL", "direct"),
            "mysqlclient": ("MySQL", "direct"),
            "mysql2": ("MySQL", "direct"),
            "mysql": ("MySQL", "direct"),
            # SQLite
            "sqlite3": ("SQLite", "direct"),
            # Redis
            "redis": ("Redis", "direct"),
            "ioredis": ("Redis", "direct"),
            # Firebase
            "firebase": ("Firebase", "direct"),
            "firebase-admin": ("Firebase", "direct"),
        }

        for dep_name, (db_name, usage) in dep_db.items():
            if dep_name in dep_names:
                c = out.setdefault(db_name, _DBCandidate(db_name, usage))
                for d in deps:
                    if d.name.lower() == dep_name:
                        c.add_evidence(d.source_file, f"Dependency '{dep_name}' detected", confidence="medium")
                        break

    # ── Framework checks ─────────────────────────────────────────

    def _check_frameworks(
        self,
        fw_names: Set[str],
        fws: List[DetectedFramework],
        out: Dict[str, _DBCandidate],
    ) -> None:
        fw_db = {
            "mongodb": ("MongoDB", "direct"),
            "mongoose": ("MongoDB", "orm"),
            "postgresql": ("PostgreSQL", "direct"),
            "sqlalchemy": ("PostgreSQL", "orm"),  # Often used with PG
            "prisma": ("PostgreSQL", "orm"),
            "redis": ("Redis", "direct"),
        }

        for fw_name, (db_name, usage) in fw_db.items():
            if fw_name in fw_names:
                c = out.setdefault(db_name, _DBCandidate(db_name, usage))
                for f in fws:
                    if f.name.lower() == fw_name:
                        for e in f.evidence[:2]:
                            c.add_evidence(e.file, f"Framework '{f.name}' implies {db_name}", confidence="medium")
                        break

    # ── Code/connection string checks ────────────────────────────

    def _check_code(self, scan_result: ScanResult, out: Dict[str, _DBCandidate]) -> None:
        _code_patterns = [
            # MongoDB
            (re.compile(r"mongodb://|mongodb\+srv://"), "MongoDB", "config"),
            (re.compile(r"from\s+pymongo|import\s+pymongo|from\s+motor|import\s+motor"), "MongoDB", "direct"),
            (re.compile(r"""require\s*\(\s*['"]mongoose['"]\s*\)"""), "MongoDB", "orm"),
            # PostgreSQL
            (re.compile(r"postgres://|postgresql://"), "PostgreSQL", "config"),
            (re.compile(r"from\s+asyncpg|import\s+asyncpg|from\s+psycopg2|import\s+psycopg2"), "PostgreSQL", "direct"),
            # MySQL
            (re.compile(r"mysql://"), "MySQL", "config"),
            (re.compile(r"from\s+pymysql|import\s+pymysql"), "MySQL", "direct"),
            # SQLite
            (re.compile(r"sqlite:///|sqlite://"), "SQLite", "config"),
            (re.compile(r"import\s+sqlite3|from\s+sqlite3"), "SQLite", "direct"),
            (re.compile(r"\.sqlite\b"), "SQLite", "config"),
            # Redis
            (re.compile(r"redis://"), "Redis", "config"),
            (re.compile(r"from\s+redis\s+import|import\s+redis\b"), "Redis", "direct"),
            # Firebase
            (re.compile(r"firebase|firestore", re.IGNORECASE), "Firebase", "config"),
        ]

        for path, content in iter_contents(scan_result):
            check_content = content[:50000]
            for pattern, db_name, usage in _code_patterns:
                match = pattern.search(check_content)
                if match:
                    c = out.setdefault(db_name, _DBCandidate(db_name, usage))
                    c.usage = usage  # Upgrade usage if more specific
                    c.add_evidence(
                        path,
                        f"{db_name} detected via code pattern",
                        snippet=match.group(0)[:100],
                        confidence="high",
                    )

    # ── Build results ────────────────────────────────────────────

    def _build_results(self, candidates: Dict[str, _DBCandidate]) -> List[DetectedDatabase]:
        results: List[DetectedDatabase] = []
        for name, c in sorted(candidates.items()):
            has_code = any(e.confidence == "high" for e in c.evidence)
            confidence: ConfidenceLevel = "high" if has_code else "medium"

            results.append(DetectedDatabase(
                name=name,
                usage=c.usage,
                confidence=confidence,
                evidence=c.evidence[:10],
            ))
        return results


class _DBCandidate:
    """Internal accumulator for database signals."""

    __slots__ = ("name", "usage", "evidence")

    def __init__(self, name: str, usage: str) -> None:
        self.name = name
        self.usage = usage
        self.evidence: list = []

    def add_evidence(
        self, file: str, reason: str,
        snippet: str | None = None,
        confidence: ConfidenceLevel = "medium",
    ) -> None:
        self.evidence.append(make_evidence(file, reason, snippet, confidence))
