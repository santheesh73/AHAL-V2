"""
AHAL AI — LLM Prompt Builder (Phase 2, Step 14)

Builds a structured prompt from verified IntelligenceResult facts.
Never includes raw file contents — only detection summaries.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.intelligence.models import IntelligenceResult

_SYSTEM_PROMPT = """You are AHAL AI, a senior software architecture explainer.
You are given verified deterministic facts from a codebase intelligence engine.

Rules:
- Do not invent frameworks, files, modules, APIs, databases, or workflows.
- Only explain facts present in the JSON.
- If information is missing, say "Insufficient evidence from codebase."
- Be concise and technical.
- Return structured markdown.

Output format:
PROJECT SUMMARY:
ARCHITECTURE:
TECH STACK:
ENTRY POINTS:
MODULES:
API SURFACE:
DATABASE/STORAGE:
WORKFLOW:
RISKS / GAPS:
CONFIDENCE:"""


def build_prompt(result: IntelligenceResult) -> str:
    """
    Build a prompt from IntelligenceResult facts.
    Returns a single string combining system instructions and JSON facts.
    """
    facts = _extract_facts(result)
    facts_json = json.dumps(facts, indent=2, default=str)

    return f"""{_SYSTEM_PROMPT}

Input facts:
{facts_json}"""


def _extract_facts(result: IntelligenceResult) -> Dict[str, Any]:
    """Extract a summary of facts without raw file contents."""
    return {
        "project_type": result.project_type,
        "confidence_score": result.confidence_score,
        "evidence_count": result.evidence_count,
        "languages": [
            {"name": l.name, "file_count": l.file_count, "percentage": l.percentage, "confidence": l.confidence}
            for l in result.languages
        ],
        "dependencies": [
            {"name": d.name, "ecosystem": d.ecosystem, "category": d.category}
            for d in result.dependencies[:30]  # Cap to avoid prompt bloat
        ],
        "frameworks": [
            {"name": f.name, "category": f.category, "confidence": f.confidence}
            for f in result.frameworks
        ],
        "entry_points": [
            {"file": e.file, "type": e.type, "framework": e.framework, "confidence": e.confidence}
            for e in result.entry_points
        ],
        "api_endpoints": [
            {"method": a.method, "path": a.path, "framework": a.framework, "file": a.file}
            for a in result.api_endpoints[:20]
        ],
        "databases": [
            {"name": d.name, "usage": d.usage, "confidence": d.confidence}
            for d in result.databases
        ],
        "modules": [
            {"name": m.name, "category": m.category, "file_count": len(m.files), "confidence": m.confidence}
            for m in result.modules
        ],
        "architecture": {
            "type": result.architecture.type,
            "confidence": result.architecture.confidence,
            "reasoning": result.architecture.reasoning,
        },
        "workflow": {
            "completeness": result.workflow.completeness,
            "confidence": result.workflow.confidence,
            "steps": [
                {"order": s.order, "source": s.source, "action": s.action, "target": s.target}
                for s in result.workflow.steps
            ],
            "warnings": result.workflow.warnings,
        },
        "warnings": result.warnings,
    }
