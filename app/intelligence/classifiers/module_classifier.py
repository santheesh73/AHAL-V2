"""
AHAL AI — Module Classifier (Phase 2, Step 9)

Classify files into logical modules/layers by directory path signals.
Pure, deterministic, evidence-backed.
"""

from __future__ import annotations

from typing import Dict, List, Set

from app.intelligence.models import ConfidenceLevel, DetectedModule
from app.intelligence.utils.evidence import make_evidence
from app.intelligence.utils.path_utils import iter_files, normalize_repo_path, path_parts
from app.models.file_schema import ScanResult

# ── Path → Category mapping ──────────────────────────────────────

_CATEGORY_DIRS: Dict[str, str] = {
    # API
    "api": "api", "routes": "api", "controllers": "api", "endpoints": "api",
    "routers": "api", "handlers": "api", "views": "api",
    # UI
    "components": "ui", "pages": "ui", "ui": "ui", "layouts": "ui",
    "templates": "ui", "public": "ui", "static": "ui",
    # Model
    "models": "model", "entities": "model", "domain": "model",
    # Schema
    "schemas": "schema", "dto": "schema", "types": "schema",
    # Service
    "services": "service", "usecases": "service", "use_cases": "service",
    "business": "service",
    # Database
    "db": "database", "database": "database", "migrations": "database",
    "seeds": "database", "fixtures": "database",
    # Auth
    "auth": "auth", "security": "auth", "jwt": "auth",
    "authentication": "auth", "authorization": "auth",
    # Test
    "tests": "test", "test": "test", "spec": "test", "__tests__": "test",
    "specs": "test",
    # Worker
    "workers": "worker", "jobs": "worker", "tasks": "worker",
    "queues": "worker", "cron": "worker",
    # Utility
    "utils": "utility", "helpers": "utility", "lib": "utility",
    "common": "utility", "shared": "utility", "tools": "utility",
    # Config
    "config": "config", "configs": "config", "settings": "config",
    "env": "config", "envs": "config",
}


class ModuleClassifier:
    """Classify files into logical modules/layers by directory path."""

    def classify(self, scan_result: ScanResult) -> List[DetectedModule]:
        # Group files by top-level logical folder
        module_files: Dict[str, List[str]] = {}
        module_categories: Dict[str, str] = {}

        for fm in iter_files(scan_result):
            norm = normalize_repo_path(fm.path)
            parts = path_parts(norm)

            if len(parts) <= 1:
                # Root-level file — skip for module classification
                continue

            # Use the first meaningful directory
            module_name, category = self._classify_path(parts)
            module_files.setdefault(module_name, []).append(norm)

            # First match wins for category
            if module_name not in module_categories:
                module_categories[module_name] = category

        # Build results
        results: List[DetectedModule] = []
        for module_name in sorted(module_files.keys()):
            files = module_files[module_name]
            category = module_categories.get(module_name, "unknown")
            count = len(files)
            conf: ConfidenceLevel = "high" if count >= 2 else "medium"

            evidence = [
                make_evidence(
                    f, f"File in '{module_name}/' directory → {category}",
                    confidence=conf,
                )
                for f in files[:5]
            ]

            results.append(DetectedModule(
                name=module_name,
                category=category,
                files=files,
                confidence=conf,
                evidence=evidence,
            ))

        return results

    def _classify_path(self, parts: List[str]) -> tuple[str, str]:
        """
        Determine module name and category from path segments.
        Walks through segments looking for the first recognizable directory name.
        """
        # Try to find a recognized directory in the path
        for part in parts[:-1]:  # Exclude filename
            lower = part.lower()
            if lower in _CATEGORY_DIRS:
                return part, _CATEGORY_DIRS[lower]

        # No match — use the top-level directory as module name
        return parts[0], "unknown"
