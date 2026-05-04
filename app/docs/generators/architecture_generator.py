from app.docs.models import PRDSection, DocEvidence
from app.docs.utils.doc_evidence import sanitize_evidence

def _get_architecture_obj(input_obj):
    if hasattr(input_obj, "architecture"):
        return getattr(input_obj, "architecture")
    return input_obj

class ArchitectureGenerator:
    def generate(self, intelligence_result) -> PRDSection:
        arch_obj = _get_architecture_obj(intelligence_result)
        
        arch_type = getattr(arch_obj, "type", None)
        if not arch_type and isinstance(arch_obj, str):
            arch_type = arch_obj
        if not arch_type:
            arch_type = "unknown"
            
        display_type = str(arch_type).strip()
        
        frameworks = getattr(intelligence_result, "frameworks", [])
        entry_points = getattr(intelligence_result, "entry_points", [])
        
        warnings = []
        evidence = []
        
        arch_ev = getattr(arch_obj, "evidence", []) or []
        if arch_ev:
            evidence.extend(arch_ev)
            
        if display_type.lower() == "unknown":
            warnings.append("Architecture could not be determined with high confidence.")
            
        content_lines = []
        content_lines.append(f"Architecture Type: {display_type.title() if display_type.lower() != 'unknown' else 'Unknown'}")
        
        reasoning = getattr(arch_obj, "reasoning", []) or []
        if reasoning:
            reasoning_text = ", ".join(reasoning) if isinstance(reasoning, list) else str(reasoning)
            content_lines.append(f"Reasoning: {reasoning_text}")
        
        if frameworks:
            fw_names = [fw.name for fw in frameworks]
            content_lines.append(f"Primary Frameworks: {', '.join(fw_names)}")
            for fw in frameworks:
                evidence.extend(getattr(fw, "evidence", []))
                
        if entry_points:
            ep_names = [ep.file for ep in entry_points if ep.file]
            content_lines.append(f"Entry Points: {', '.join(ep_names)}")
            for ep in entry_points:
                evidence.extend(getattr(ep, "evidence", []))
                
        if not evidence:
            warnings.append("No architecture evidence detected.")
            
        sanitized_ev = sanitize_evidence(evidence)
        confidence = "high" if arch_type != "unknown" and frameworks else ("medium" if sanitized_ev else "low")
        if arch_obj and hasattr(arch_obj, "confidence"):
            confidence = arch_obj.confidence
            
        return PRDSection(
            title="Architecture",
            content="\n".join(content_lines) if content_lines else "Architecture details are not available.",
            evidence=sanitized_ev,
            confidence=confidence,
            warnings=warnings
        )
