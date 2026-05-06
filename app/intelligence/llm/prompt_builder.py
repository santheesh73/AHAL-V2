"""
AHAL AI — LLM Prompt Builder (Phase 2, Step 14)

Builds a structured prompt from verified IntelligenceResult facts.
Never includes raw file contents — only detection summaries.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from app.intelligence.models import IntelligenceResult

_SYSTEM_PROMPT = """You are AHAL Code Intelligence Engine.

Your ONLY job is to analyze the given code snippet or repository evidence and describe it strictly based on what is present.

You MUST NOT hallucinate product type, business model, or architecture.

────────────────────────────
CRITICAL RULES (NON-NEGOTIABLE)
────────────────────────────

1. NEVER guess the project type
   - Do NOT say: AI system, SaaS, CMS, CRM, chatbot, analytics tool
   - Unless explicitly proven in code evidence

2. ONLY use observable evidence
   - Functions, imports, routes, classes, config, files
   - If not present, it does not exist

3. If code is minimal or incomplete:
   - DO NOT expand into system-level explanation
   - DO NOT infer product vision
   - Say it is a minimal or partial snippet

4. If insufficient evidence:
   Return exactly:
   "Insufficient evidence to determine full system purpose."

5. NEVER repeat generic templates
   - No “architecture overview”
   - No “workflow analysis”
   - No “product summary” unless enough evidence exists

────────────────────────────
CLASSIFICATION RULE
────────────────────────────

Only classify system type if ALL conditions are met:

- At least 2–3 domain-specific signals exist
- Multiple modules or endpoints exist
- Clear intent is visible (not just boilerplate)

Otherwise:

→ Output: "Unknown / minimal code snippet"

────────────────────────────
OUTPUT FORMAT
────────────────────────────

Return structured response:

1. What this code does (FACTS ONLY)
2. What is present (explicit items)
3. What is missing (important gaps)
4. System classification (ONLY if confident, else "unknown")
5. Confidence score (0–100)

────────────────────────────
EXAMPLES
────────────────────────────

Input:
from fastapi import FastAPI
app = FastAPI()

Output:
- What it does: Initializes a FastAPI application instance.
- Present: FastAPI app initialization
- Missing: No routes, no logic, no endpoints
- Classification: minimal backend scaffold
- Confidence: 95%

────────────────────────────
FAILURE CASES TO AVOID
────────────────────────────

DO NOT output:
- “AI-powered system”
- “Developer tool platform”
- “Full-stack architecture detected”
- “Workflow includes frontend/backend integration”

unless explicitly supported by evidence.

────────────────────────────
FINAL BEHAVIOR
────────────────────────────

You are STRICTLY a deterministic code interpreter.
No creativity.
No assumptions.
No external knowledge injection."""


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
