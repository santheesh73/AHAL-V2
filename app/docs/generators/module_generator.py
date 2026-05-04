from app.docs.models import ModuleSectionItem, DocEvidence
from app.docs.utils.doc_evidence import sanitize_evidence

class ModuleGenerator:
    def generate(self, intelligence_result) -> list[ModuleSectionItem]:
        items = []
        modules = getattr(intelligence_result, "modules", [])
        
        for mod in modules:
            category = getattr(mod, "category", "unknown")
            if category == "unknown":
                continue # Avoid unknown module spam
                
            evidence = sanitize_evidence(getattr(mod, "evidence", []))
            
            # Extract files safely
            files = []
            for ev in evidence:
                if ev.file and ev.file not in files:
                    files.append(ev.file)
                    
            confidence = "high" if evidence else "low"
            
            from app.docs.utils.section_utils import safe_str
            items.append(ModuleSectionItem(
                name=safe_str(getattr(mod, "name", "Unnamed Module"), "Unnamed Module"),
                category=safe_str(category, "unknown"),
                files=files,
                description=safe_str(getattr(mod, "description", f"Module for {category}"), f"Module for {category}"),
                evidence=evidence,
                confidence=confidence
            ))
            
        return items
