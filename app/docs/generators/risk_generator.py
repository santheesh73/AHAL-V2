from app.docs.models import RiskItem, DocEvidence
from app.docs.utils.doc_evidence import sanitize_evidence
from app.docs.fact_snapshot import PRDFactSnapshot, build_fact_snapshot

class RiskGenerator:
    def generate(self, scan_result, intelligence_result, workflow_warnings, snapshot: PRDFactSnapshot | None = None) -> list[RiskItem]:
        risks = []
        contents = getattr(scan_result, "contents", {})
        snapshot = snapshot or build_fact_snapshot(scan_result=scan_result, intelligence_result=intelligence_result)
        
        # No README
        if not any("readme" in k.lower() for k in contents.keys()):
            risks.append(RiskItem(
                title="No README detected",
                severity="high",
                description="The project lacks a README file, making it difficult to understand the purpose and setup instructions.",
                evidence=[],
                recommendation="Add a comprehensive README.md file."
            ))
            
        # No tests
        if not snapshot.has_tests:
            risks.append(RiskItem(
                title="No tests detected",
                severity="high",
                description="No test files or directories were found in the codebase.",
                evidence=[],
                recommendation="Implement unit and integration tests."
            ))
            
        # No auth
        # IntelligenceResult doesn't have an explicit 'auth' field usually, but maybe in modules or frameworks?
        has_auth = snapshot.has_auth
        modules = getattr(intelligence_result, "modules", [])
        for mod in modules:
            if "auth" in getattr(mod, "name", "").lower() or "auth" in getattr(mod, "category", "").lower():
                has_auth = True
                break
        
        # Also check frameworks/dependencies for auth
        for dep in getattr(intelligence_result, "dependencies", []):
            if "auth" in getattr(dep, "name", "").lower() or "jwt" in getattr(dep, "name", "").lower():
                has_auth = True
                break
                
        if not has_auth:
            risks.append(RiskItem(
                title="No auth detected",
                severity="medium",
                description="No authentication or authorization modules or dependencies were explicitly detected.",
                evidence=[],
                recommendation="Ensure the application implements proper authentication if it handles sensitive data."
            ))
            
        # No database
        if not snapshot.has_database:
            description = "No persistent database/storage layer was detected. Add persistence only if the application stores sessions, user data, retrieval indexes, or audit history."
            recommendation = "Add persistence only if the application needs durable state, retrieval indexes, or audit history."
            if getattr(snapshot, "domain", None) == "healthcare":
                description += " If sensitive medical data is stored, document data handling and access controls."
                recommendation += " If sensitive medical data is stored, document data handling and access controls."
            risks.append(RiskItem(
                title="No persistent database/storage layer detected",
                severity="medium",
                description=description,
                evidence=[],
                recommendation=recommendation
            ))
            
        # Partial workflow only
        for w in workflow_warnings:
            if "partial" in w.lower():
                risks.append(RiskItem(
                    title="Partial workflow only",
                    severity="medium",
                    description=w,
                    evidence=[],
                    recommendation="Review the system workflow to ensure all components are properly connected."
                ))
                break
                
        # Unknown architecture confidence
        arch = getattr(intelligence_result, "architecture", "unknown")
        if arch == "unknown":
            risks.append(RiskItem(
                title="Unknown architecture confidence",
                severity="low",
                description="The core architecture could not be determined with high confidence.",
                evidence=[],
                recommendation="Refactor codebase structure to follow standard architectural patterns."
            ))
            
        # No deployment config
        if not snapshot.has_deployment:
            risks.append(RiskItem(
                title="No deployment config detected",
                severity="low",
                description="No common deployment configuration files (e.g. Dockerfile) were found.",
                evidence=[],
                recommendation="Add deployment configurations to standardize environments."
            ))
            
        return risks
