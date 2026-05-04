from app.docs.models import PRDSection, DocEvidence
from app.docs.utils.doc_evidence import sanitize_evidence
from app.docs.fact_snapshot import PRDFactSnapshot, build_fact_snapshot

class DatabaseGenerator:
    def generate(self, intelligence_result, snapshot: PRDFactSnapshot | None = None) -> PRDSection:
        warnings = []
        evidence = []
        snapshot = snapshot or build_fact_snapshot(intelligence_result=intelligence_result)
        
        databases = getattr(intelligence_result, "databases", [])
        
        content_lines = []
        
        if databases or snapshot.has_database:
            for db in databases:
                content_lines.append(f"Database/Storage: {getattr(db, 'name', 'Unknown')}")
                evidence.extend(getattr(db, "evidence", []))
            if not databases and snapshot.database_names:
                content_lines.append(f"Database/Storage evidence detected: {', '.join(snapshot.database_names)}")
        else:
            content_lines.append("No database/storage layer detected from provided codebase evidence.")
            warnings.append("No database detected.")
            
        sanitized_ev = sanitize_evidence(evidence)
        confidence = "high" if sanitized_ev else "low"
        
        return PRDSection(
            title="Databases",
            content="\n".join(content_lines),
            evidence=sanitized_ev,
            confidence=confidence,
            warnings=warnings
        )
