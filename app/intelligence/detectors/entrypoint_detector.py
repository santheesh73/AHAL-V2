"""
AHAL AI — Entry Point Detector (Phase 2, Step 6)

Detect application entry points from filenames, content patterns, and framework context.
Pure, deterministic, evidence-backed.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from app.intelligence.models import ConfidenceLevel, DetectedEntryPoint, DetectedFramework
from app.intelligence.utils.evidence import dedupe_by_key, make_evidence
from app.intelligence.utils.path_utils import content_for, filename, iter_files, normalize_repo_path
from app.models.file_schema import ScanResult

# ── Known entrypoint patterns ────────────────────────────────────

_BACKEND_ENTRIES: Dict[str, str] = {
    "main.py": "backend",
    "app.py": "backend",
    "server.py": "backend",
    "wsgi.py": "backend",
    "asgi.py": "backend",
    "index.js": "backend",
    "server.js": "backend",
    "main.ts": "backend",
    "server.ts": "backend",
    "index.ts": "backend",
    "manage.py": "backend",
}

_FRONTEND_PATTERNS: List[str] = [
    "src/main.tsx",
    "src/main.jsx",
    "src/main.ts",
    "src/main.js",
    "src/index.tsx",
    "src/index.jsx",
    "src/index.ts",
    "src/index.js",
    "pages/_app.tsx",
    "pages/_app.jsx",
    "pages/_app.ts",
    "pages/_app.js",
    "app/layout.tsx",
    "app/layout.jsx",
    "app/layout.ts",
    "app/layout.js",
    "index.html",
]


class EntryPointDetector:
    """Detect application entry points from ScanResult."""

    def detect(
        self,
        scan_result: ScanResult,
        frameworks: Optional[List[DetectedFramework]] = None,
    ) -> List[DetectedEntryPoint]:
        fw_names: Set[str] = {f.name.lower() for f in (frameworks or [])}
        results: List[DetectedEntryPoint] = []

        for fm in iter_files(scan_result):
            norm = normalize_repo_path(fm.path)
            fname = filename(fm.path).lower()

            # ── Frontend patterns ────────────────────────────────
            if norm in _FRONTEND_PATTERNS or norm.lower() in [p.lower() for p in _FRONTEND_PATTERNS]:
                ep_type = "frontend"
                fw = self._match_framework(norm, fw_names)
                conf: ConfidenceLevel = "high" if fw else "medium"
                results.append(DetectedEntryPoint(
                    file=norm,
                    type=ep_type,
                    framework=fw,
                    confidence=conf,
                    evidence=[make_evidence(norm, f"Frontend entry point pattern: {fname}", confidence=conf)],
                ))
                continue

            # ── Backend patterns ─────────────────────────────────
            if fname in _BACKEND_ENTRIES:
                ep_type = _BACKEND_ENTRIES[fname]
                fw = self._match_backend_framework(scan_result, norm, fw_names)
                conf = "high" if fw else "medium"
                results.append(DetectedEntryPoint(
                    file=norm,
                    type=ep_type,
                    framework=fw,
                    confidence=conf,
                    evidence=[make_evidence(norm, f"Backend entry point: {fname}", confidence=conf)],
                ))
                continue

            # ── Config entry points (package.json scripts, Dockerfile) ─
            if fname == "package.json":
                self._check_package_scripts(scan_result, norm, results, fw_names)
            elif fname == "dockerfile":
                self._check_dockerfile(scan_result, norm, results)

        return dedupe_by_key(results, lambda e: (e.file, e.type))

    # ── Helpers ──────────────────────────────────────────────────

    def _match_framework(self, path: str, fw_names: Set[str]) -> Optional[str]:
        """Match a frontend entrypoint to a known frontend framework."""
        if any(fw in fw_names for fw in ("react", "next.js")):
            if path.endswith((".tsx", ".jsx")):
                return "React"
        if "vue" in fw_names:
            return "Vue"
        if "angular" in fw_names:
            return "Angular"
        if "svelte" in fw_names:
            return "Svelte"
        return None

    def _match_backend_framework(
        self,
        scan_result: ScanResult,
        path: str,
        fw_names: Set[str],
    ) -> Optional[str]:
        """Match a backend entrypoint to a framework by checking content."""
        content = content_for(scan_result, path)
        if not content:
            # Still match by framework presence
            for fw in ("fastapi", "flask", "django", "express", "nestjs"):
                if fw in fw_names:
                    return fw.title() if fw != "nestjs" else "NestJS"
            return None

        lower = content[:10000].lower()
        if "fastapi" in lower and "fastapi" in fw_names:
            return "FastAPI"
        if "flask" in lower and "flask" in fw_names:
            return "Flask"
        if "django" in lower and "django" in fw_names:
            return "Django"
        if "express" in lower and "express" in fw_names:
            return "Express"
        # Fallback: check content without requiring framework detection
        if "fastapi" in lower:
            return "FastAPI"
        if "flask" in lower:
            return "Flask"
        if "django" in lower:
            return "Django"
        if "express" in lower:
            return "Express"
        return None

    def _check_package_scripts(
        self,
        scan_result: ScanResult,
        path: str,
        results: List[DetectedEntryPoint],
        fw_names: Set[str],
    ) -> None:
        """Check package.json scripts for entry points."""
        import json
        content = content_for(scan_result, path)
        if not content:
            return
        try:
            data = json.loads(content)
            scripts = data.get("scripts", {})
            if isinstance(scripts, dict):
                for key in ("start", "dev", "serve", "build"):
                    if key in scripts:
                        results.append(DetectedEntryPoint(
                            file=path,
                            type="config",
                            framework=None,
                            confidence="medium",
                            evidence=[make_evidence(
                                path,
                                f'package.json script "{key}": "{scripts[key]}"',
                                snippet=f'"{key}": "{scripts[key]}"',
                                confidence="medium",
                            )],
                        ))
                        break  # Only record one config entrypoint per package.json
        except Exception:
            pass

    def _check_dockerfile(
        self,
        scan_result: ScanResult,
        path: str,
        results: List[DetectedEntryPoint],
    ) -> None:
        """Check Dockerfile for CMD/ENTRYPOINT."""
        content = content_for(scan_result, path)
        if not content:
            return
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.upper().startswith("CMD ") or stripped.upper().startswith("ENTRYPOINT "):
                results.append(DetectedEntryPoint(
                    file=path,
                    type="config",
                    framework=None,
                    confidence="medium",
                    evidence=[make_evidence(
                        path,
                        f"Dockerfile {stripped.split()[0]} directive",
                        snippet=stripped[:120],
                        confidence="medium",
                    )],
                ))
                return  # Only one per Dockerfile
