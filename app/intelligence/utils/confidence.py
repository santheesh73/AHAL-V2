"""
AHAL AI — Confidence scoring (Phase 2)

Deterministic confidence score calculation from intelligence results.
Returns a float between 0.0 and 1.0.
"""

from __future__ import annotations

from typing import List, Sequence

from app.intelligence.models import (
    ArchitectureResult,
    ConfidenceLevel,
    DetectedAPIEndpoint,
    DetectedDatabase,
    DetectedDependency,
    DetectedEntryPoint,
    DetectedFramework,
    DetectedLanguage,
    DetectedModule,
    WorkflowResult,
)

# ── Confidence value mapping ─────────────────────────────────────

_CONF_VALUES = {"high": 1.0, "medium": 0.6, "low": 0.3}


def _conf_val(level: ConfidenceLevel) -> float:
    return _CONF_VALUES.get(level, 0.0)


def _avg_confidence(items: Sequence) -> float:
    """Average confidence of a list of items with a .confidence field."""
    if not items:
        return 0.0
    total = sum(_conf_val(getattr(i, "confidence", "low")) for i in items)
    return total / len(items)


def _has_items(items: Sequence) -> float:
    """1.0 if items exist, 0.0 otherwise."""
    return 1.0 if items else 0.0


# ── Public API ────────────────────────────────────────────────────

def calculate_confidence_score(
    languages: List[DetectedLanguage] | None = None,
    dependencies: List[DetectedDependency] | None = None,
    frameworks: List[DetectedFramework] | None = None,
    entry_points: List[DetectedEntryPoint] | None = None,
    api_endpoints: List[DetectedAPIEndpoint] | None = None,
    databases: List[DetectedDatabase] | None = None,
    modules: List[DetectedModule] | None = None,
    architecture: ArchitectureResult | None = None,
    workflow: WorkflowResult | None = None,
) -> float:
    """
    Calculate a composite confidence score from 0.0 to 1.0.

    Weights:
        languages:     0.10
        dependencies:  0.10
        frameworks:    0.20
        entry_points:  0.15
        modules:       0.15
        architecture:  0.15
        workflow:       0.15

    API endpoints and databases are bonuses (not penalized when absent).
    """
    langs       = languages or []
    deps        = dependencies or []
    fwks        = frameworks or []
    eps         = entry_points or []
    apis        = api_endpoints or []
    dbs         = databases or []
    mods        = modules or []
    arch        = architecture or ArchitectureResult()
    wf          = workflow or WorkflowResult()

    score = 0.0

    # Languages: 10% — presence + average confidence
    if langs:
        score += 0.10 * _avg_confidence(langs)

    # Dependencies: 10% — presence + average confidence
    if deps:
        score += 0.10 * _avg_confidence(deps)

    # Frameworks: 20% — presence + average confidence
    if fwks:
        score += 0.20 * _avg_confidence(fwks)

    # Entry points: 15%
    if eps:
        score += 0.15 * _avg_confidence(eps)

    # Modules: 15%
    if mods:
        score += 0.15 * _avg_confidence(mods)

    # Architecture: 15%
    score += 0.15 * _conf_val(arch.confidence)

    # Workflow: 15%
    if wf.steps:
        score += 0.15 * _avg_confidence(wf.steps)

    # Bonus: API endpoints (up to +0.05)
    if apis:
        score += min(0.05, 0.01 * len(apis))

    # Bonus: databases (up to +0.03)
    if dbs:
        score += min(0.03, 0.01 * len(dbs))

    # Clamp
    return round(max(0.0, min(1.0, score)), 3)
