from app.docs.models import APISectionItem, DocEvidence
from app.docs.utils.doc_evidence import sanitize_evidence

class APIGenerator:
    def generate(self, intelligence_result) -> list[APISectionItem]:
        items = []
        endpoints = getattr(intelligence_result, "api_endpoints", [])
        
        for ep in endpoints:
            evidence = sanitize_evidence(getattr(ep, "evidence", []))
            
            source_file = None
            for ev in evidence:
                if ev.file:
                    source_file = ev.file
                    break
                    
            confidence = "high" if evidence else "low"
            
            from app.docs.utils.section_utils import safe_str
            items.append(APISectionItem(
                method=safe_str(getattr(ep, "method", "UNKNOWN"), "UNKNOWN").upper(),
                path=safe_str(getattr(ep, "path", "unknown"), "unknown"),
                framework=safe_str(getattr(ep, "framework", "unknown"), "unknown"),
                source_file=source_file,
                handler=safe_str(getattr(ep, "handler", None), None),
                description=safe_str(getattr(ep, "description", "API Endpoint"), "API Endpoint"),
                evidence=evidence,
                confidence=confidence
            ))
            
        return items
