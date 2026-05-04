from app.docs.models import PRDSection, DocEvidence
from app.docs.utils.doc_evidence import sanitize_evidence
from app.chat.retrieval.project_purpose_extractor import ProjectPurposeExtractor
from app.docs.fact_snapshot import PRDFactSnapshot, build_fact_snapshot

class SetupGenerator:
    def generate(self, scan_result, snapshot: PRDFactSnapshot | None = None) -> PRDSection:
        warnings = []
        evidence = []
        content_lines = []
        snapshot = snapshot or build_fact_snapshot(scan_result=scan_result)
        
        contents = getattr(scan_result, "contents", {})
        
        # Check standard files
        if "requirements.txt" in contents:
            content_lines.append("- Python dependencies detected via requirements.txt.")
            evidence.append(DocEvidence(
                source_type="file",
                source_id="requirements.txt",
                file="requirements.txt",
                reason="Found requirements.txt",
                confidence="high"
            ))
            
        if "package.json" in contents:
            content_lines.append("- Node.js dependencies detected via package.json.")
            evidence.append(DocEvidence(
                source_type="file",
                source_id="package.json",
                file="package.json",
                reason="Found package.json",
                confidence="high"
            ))
            
        if "Dockerfile" in contents:
            content_lines.append("- Docker configuration detected.")
            evidence.append(DocEvidence(
                source_type="file",
                source_id="Dockerfile",
                file="Dockerfile",
                reason="Found Dockerfile",
                confidence="high"
            ))
            
        if "pyproject.toml" in contents:
            content_lines.append("- Python project configuration detected via pyproject.toml.")
            evidence.append(DocEvidence(
                source_type="file",
                source_id="pyproject.toml",
                file="pyproject.toml",
                reason="Found pyproject.toml",
                confidence="high"
            ))
            
        # Check README for setup
        for k, v in contents.items():
            if "readme" in k.lower():
                text = v.decode("utf-8", errors="ignore") if isinstance(v, bytes) else str(v or "")
                # Just flag that README exists, we won't try to parse setup sections exactly without LLM here,
                # but we can check if "install" or "setup" or "run" is in it
                if any(word in text.lower() for word in ["install", "setup", "run", "start", "build"]):
                    content_lines.append("- Setup or installation instructions detected in README.")
                    evidence.append(DocEvidence(
                        source_type="file",
                        source_id=k,
                        file=k,
                        reason="Setup instructions found in README",
                        confidence="medium"
                    ))
                break
                
        if not content_lines and snapshot.has_setup:
            content_lines.append("Setup-related files were detected, but detailed run instructions were limited in the analyzed evidence.")
        elif not content_lines:
            content_lines.append("Insufficient setup evidence.")
            warnings.append("No setup files or instructions detected.")
            
        sanitized_ev = sanitize_evidence(evidence)
        confidence = "high" if sanitized_ev else "low"
        
        return PRDSection(
            title="Setup Notes",
            content="\n".join(content_lines),
            evidence=sanitized_ev,
            confidence=confidence,
            warnings=warnings
        )
