from typing import Literal
from app.chat.models import EvidenceReference

def compute_chat_confidence(
    evidence: list[EvidenceReference],
    has_purpose: bool = False,
    has_architecture: bool = False,
    has_framework: bool = False,
    has_entrypoint: bool = False,
    has_api: bool = False,
    has_workflow: bool = False,
    insufficient_context: bool = False,
) -> Literal["high", "medium", "low"]:
    """
    Computes a deterministic, unified confidence score for Phase 4 chat answers.
    """
    if insufficient_context or not evidence:
        return "low"

    # Count project-level intelligence features
    features = [
        has_purpose,
        has_architecture,
        has_framework,
        has_entrypoint,
        has_api,
        has_workflow
    ]
    count = sum(features)

    # General project context rule: 3+ features -> high, 2+ features -> medium
    if count >= 3:
        return "high"
    elif count >= 2:
        return "medium"

    # Fallback to evidence quality (e.g. for specific file queries)
    high_count = sum(1 for e in evidence[:5] if getattr(e, "confidence", "low") == "high")
    medium_count = sum(1 for e in evidence[:5] if getattr(e, "confidence", "low") == "medium")
    
    if high_count >= 2:
        return "high"
    if high_count >= 1 or medium_count >= 2:
        return "medium"
        
    return "low"
