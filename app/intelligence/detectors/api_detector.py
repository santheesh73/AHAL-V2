"""
AHAL AI — API Detector (Phase 2, Step 7)

Detect HTTP API endpoints from code patterns.
Pure, deterministic, evidence-backed.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from app.intelligence.models import ConfidenceLevel, DetectedAPIEndpoint, DetectedFramework
from app.intelligence.utils.evidence import dedupe_by_key, make_evidence
from app.intelligence.utils.path_utils import extension, iter_contents
from app.models.file_schema import ScanResult

# ── Route patterns ───────────────────────────────────────────────

# FastAPI: @app.get("/path"), @router.post("/path")
_FASTAPI_PATTERN = re.compile(
    r"""@(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)

# Flask: @app.route("/path", methods=["GET"]), @blueprint.route("/path")
_FLASK_ROUTE_PATTERN = re.compile(
    r"""@(?:app|blueprint|bp)\s*\.\s*route\s*\(\s*['"]([^'"]+)['"](?:.*?methods\s*=\s*\[([^\]]*)\])?""",
    re.IGNORECASE | re.DOTALL,
)

# Express: app.get("/path", ...), router.post("/path", ...)
_EXPRESS_PATTERN = re.compile(
    r"""(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)

# Django: path("url/", view), re_path(r"^url/$", view)
_DJANGO_PATTERN = re.compile(
    r"""(?:path|re_path)\s*\(\s*[r]?['"]([^'"]+)['"]""",
    re.IGNORECASE,
)

# Handler function: def func_name( or async def func_name(
_HANDLER_PATTERN = re.compile(r"""(?:async\s+)?def\s+(\w+)\s*\(""")


class APIDetector:
    """Detect HTTP API endpoints from code patterns in ScanResult."""

    def detect(
        self,
        scan_result: ScanResult,
        frameworks: Optional[List[DetectedFramework]] = None,
    ) -> List[DetectedAPIEndpoint]:
        fw_names: Set[str] = {f.name.lower() for f in (frameworks or [])}
        results: List[DetectedAPIEndpoint] = []

        for path, content in iter_contents(scan_result):
            ext = extension(path)
            check_content = content[:100000]  # Limit regex scope
            lines = check_content.splitlines()

            # ── FastAPI routes ───────────────────────────────────
            if ext in (".py",) or "fastapi" in fw_names:
                self._detect_fastapi(path, check_content, lines, results)

            # ── Flask routes ─────────────────────────────────────
            if ext in (".py",) or "flask" in fw_names:
                self._detect_flask(path, check_content, lines, results)

            # ── Express routes ───────────────────────────────────
            if ext in (".js", ".ts", ".mjs") or "express" in fw_names:
                self._detect_express(path, check_content, lines, results)

            # ── Django routes ────────────────────────────────────
            if ext in (".py",) or "django" in fw_names:
                self._detect_django(path, check_content, lines, results)

        return dedupe_by_key(results, lambda e: (e.method, e.path, e.file))

    # ── FastAPI ──────────────────────────────────────────────────

    def _detect_fastapi(
        self, path: str, content: str, lines: List[str], results: List[DetectedAPIEndpoint],
    ) -> None:
        for match in _FASTAPI_PATTERN.finditer(content):
            method = match.group(1).upper()
            route_path = match.group(2)
            handler = self._find_handler_after(content, match.end())
            results.append(DetectedAPIEndpoint(
                method=method,
                path=route_path,
                framework="FastAPI",
                file=path,
                handler=handler,
                confidence="high",
                evidence=[make_evidence(
                    path,
                    f"FastAPI route: {method} {route_path}",
                    snippet=match.group(0)[:100],
                    confidence="high",
                )],
            ))

    # ── Flask ────────────────────────────────────────────────────

    def _detect_flask(
        self, path: str, content: str, lines: List[str], results: List[DetectedAPIEndpoint],
    ) -> None:
        for match in _FLASK_ROUTE_PATTERN.finditer(content):
            route_path = match.group(1)
            methods_str = match.group(2)

            if methods_str:
                methods = re.findall(r"['\"](\w+)['\"]", methods_str)
            else:
                methods = ["GET"]

            handler = self._find_handler_after(content, match.end())

            for method in methods:
                results.append(DetectedAPIEndpoint(
                    method=method.upper(),
                    path=route_path,
                    framework="Flask",
                    file=path,
                    handler=handler,
                    confidence="high",
                    evidence=[make_evidence(
                        path,
                        f"Flask route: {method.upper()} {route_path}",
                        snippet=match.group(0)[:100],
                        confidence="high",
                    )],
                ))

    # ── Express ──────────────────────────────────────────────────

    def _detect_express(
        self, path: str, content: str, lines: List[str], results: List[DetectedAPIEndpoint],
    ) -> None:
        # Skip Python files for Express (avoid FastAPI false positives)
        if path.endswith(".py"):
            return

        for match in _EXPRESS_PATTERN.finditer(content):
            method = match.group(1).upper()
            route_path = match.group(2)
            results.append(DetectedAPIEndpoint(
                method=method,
                path=route_path,
                framework="Express",
                file=path,
                handler=None,
                confidence="high",
                evidence=[make_evidence(
                    path,
                    f"Express route: {method} {route_path}",
                    snippet=match.group(0)[:100],
                    confidence="high",
                )],
            ))

    # ── Django ───────────────────────────────────────────────────

    def _detect_django(
        self, path: str, content: str, lines: List[str], results: List[DetectedAPIEndpoint],
    ) -> None:
        for match in _DJANGO_PATTERN.finditer(content):
            route_path = match.group(1)
            results.append(DetectedAPIEndpoint(
                method="UNKNOWN",
                path=route_path,
                framework="Django",
                file=path,
                handler=None,
                confidence="medium",
                evidence=[make_evidence(
                    path,
                    f"Django URL pattern: {route_path}",
                    snippet=match.group(0)[:100],
                    confidence="medium",
                )],
            ))

    # ── Handler extraction ───────────────────────────────────────

    def _find_handler_after(self, content: str, pos: int) -> Optional[str]:
        """Find the next def/async def after a decorator match."""
        remaining = content[pos:pos + 500]
        match = _HANDLER_PATTERN.search(remaining)
        if match:
            return match.group(1)
        return None
