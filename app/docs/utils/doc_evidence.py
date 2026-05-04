from app.docs.models import DocEvidence
from app.docs.utils.evidence_sanitizer import sanitize_evidence_reason, sanitize_path, sanitize_text
from app.utils.ignored_paths import is_ignored_path
from app.utils.evidence_types import normalize_evidence_source_type

def sanitize_evidence(evidence_list, warnings: list[str] | None = None) -> list[DocEvidence]:
    """Convert and sanitize evidence to DocEvidence, filtering ignored paths."""
    sanitized = []
    if not evidence_list:
        return sanitized
        
    for ev in evidence_list:
        file_path = sanitize_path(getattr(ev, "file", None), fallback="")
        if file_path and is_ignored_path(file_path):
            continue
            
        source_id = sanitize_text(getattr(ev, "source_id", None), fallback="unknown")
        source_type = getattr(ev, "source_type", "unknown")
        
        # Additional node checking
        if source_id and ":" in source_id:
            prefix, payload = source_id.split(":", 1)
            if prefix in ("file", "module", "entrypoint", "function"):
                path_part = payload.split(":")[0] if prefix == "function" else payload
                if is_ignored_path(path_part):
                    continue
        elif source_type == "file" and source_id and is_ignored_path(source_id):
            continue
            
        normalized_type, changed = normalize_evidence_source_type(
            source_type,
            file=file_path,
            source_id=source_id,
        )
        if changed and warnings is not None:
            warnings.append(
                f"Normalized unsupported evidence source_type '{source_type}' to '{normalized_type}'."
            )
        try:
            sanitized.append(DocEvidence(
                source_type=normalized_type,
                source_id=source_id or "unknown",
                file=file_path or None,
                reason=sanitize_evidence_reason(getattr(ev, "reason", "Detected")),
                snippet=getattr(ev, "snippet", None),
                confidence=getattr(ev, "confidence", "medium")
            ))
        except Exception:
            if warnings is not None:
                warnings.append(
                    f"Skipped invalid evidence item for source '{source_id or 'unknown'}'."
                )
    return sanitized
