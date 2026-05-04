from app.docs.models import PRDSection, DocEvidence
from app.docs.utils.doc_evidence import sanitize_evidence

class TechStackGenerator:
    def generate(self, intelligence_result) -> PRDSection:
        warnings = []
        evidence = []
        
        languages = getattr(intelligence_result, "languages", [])
        frameworks = getattr(intelligence_result, "frameworks", [])
        databases = getattr(intelligence_result, "databases", [])
        dependencies = getattr(intelligence_result, "dependencies", [])
        
        content_lines = []
        
        if languages:
            lang_names = [lang.name for lang in languages]
            content_lines.append(f"Languages: {', '.join(lang_names)}")
            for lang in languages:
                evidence.extend(lang.evidence)
        
        if frameworks:
            fw_names = [fw.name for fw in frameworks]
            content_lines.append(f"Frameworks: {', '.join(fw_names)}")
            for fw in frameworks:
                evidence.extend(fw.evidence)
                
        if databases:
            db_names = [db.name for db in databases]
            content_lines.append(f"Databases/Storage: {', '.join(db_names)}")
            for db in databases:
                evidence.extend(db.evidence)
                
        if dependencies:
            dep_names = [dep.name for dep in dependencies]
            content_lines.append(f"Key Dependencies: {', '.join(dep_names)}")
            for dep in dependencies:
                evidence.extend(dep.evidence)
                
        if not content_lines:
            warnings.append("No tech stack detected.")
            
        sanitized_ev = sanitize_evidence(evidence)
        confidence = "high" if sanitized_ev else "low"
        
        return PRDSection(
            title="Tech Stack",
            content="\n\n".join(content_lines) if content_lines else "Tech stack details are not available.",
            evidence=sanitized_ev,
            confidence=confidence,
            warnings=warnings
        )
