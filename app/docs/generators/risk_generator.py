from app.docs.models import RiskItem, DocEvidence
from app.docs.utils.doc_evidence import sanitize_evidence
from app.docs.fact_snapshot import PRDFactSnapshot, build_fact_snapshot
from app.intelligence.repository_type_classifier import is_documentation_repo_type, is_package_like_repo_type

class RiskGenerator:
    def generate(self, scan_result, intelligence_result, workflow_warnings, snapshot: PRDFactSnapshot | None = None) -> list[RiskItem]:
        risks = []
        contents = getattr(scan_result, "contents", {})
        snapshot = snapshot or build_fact_snapshot(scan_result=scan_result, intelligence_result=intelligence_result)
        if is_documentation_repo_type(snapshot.repo_type):
            if not any("readme" in k.lower() for k in contents.keys()):
                risks.append(RiskItem(
                    title="No README detected",
                    severity="high",
                    description="The repository lacks a README file, which makes the study plan or documentation harder to navigate.",
                    evidence=[],
                    recommendation="Add a README.md that explains the repository purpose and structure."
                ))
            readme_text = " ".join(str(value or "") for key, value in contents.items() if "readme" in str(key).lower()).lower()
            if "http://" in readme_text or "https://" in readme_text:
                risks.append(RiskItem(
                    title="No automated link/content validation detected",
                    severity="medium",
                    description="Documentation links or curated resources may become stale without automated validation.",
                    evidence=[],
                    recommendation="Add lightweight link or structure validation for documentation content."
                ))
            risks.append(RiskItem(
                title="Maintenance status may be unclear",
                severity="medium",
                description="Documentation and study-plan repositories can become outdated if resource freshness and maintenance expectations are not communicated.",
                evidence=[],
                recommendation="Document maintenance expectations, review cadence, and how contributors should update resources."
            ))
            return risks
        if snapshot.repo_type == "dataset":
            risks.append(RiskItem(
                title="Dataset provenance may be unclear",
                severity="medium",
                description="Dataset repositories need source, collection, and licensing clarity so consumers can use the data responsibly.",
                evidence=[],
                recommendation="Document provenance, schema, freshness, and licensing details for the dataset."
            ))
            risks.append(RiskItem(
                title="No automated schema/data validation detected",
                severity="medium",
                description="Dataset quality issues can go unnoticed without basic validation checks.",
                evidence=[],
                recommendation="Add schema or data-quality validation for the dataset where practical."
            ))
            return risks
        if snapshot.repo_type == "cli_tool":
            if not snapshot.has_tests:
                risks.append(RiskItem(
                    title="No CLI tests detected",
                    severity="high",
                    description="CLI argument parsing and command execution flows were not covered by detected tests.",
                    evidence=[],
                    recommendation="Add tests for command parsing, exit codes, and main execution paths."
                ))
            risks.append(RiskItem(
                title="Packaging/install guidance may be incomplete",
                severity="medium",
                description="CLI tools are harder to adopt when install and usage guidance is incomplete.",
                evidence=[],
                recommendation="Document installation, example commands, and expected runtime prerequisites."
            ))
            return risks
        if is_package_like_repo_type(snapshot.repo_type):
            if not snapshot.has_tests:
                risks.append(RiskItem(
                    title="No package tests detected",
                    severity="high",
                    description="Public library APIs were detected without corresponding automated test coverage evidence.",
                    evidence=[],
                    recommendation="Add tests for the exported package/library API surface."
                ))
            risks.append(RiskItem(
                title="Package consumer guidance may be incomplete",
                severity="medium",
                description="Package repositories should clearly document installation, versioning, and usage examples.",
                evidence=[],
                recommendation="Add package usage examples, versioning guidance, and consumer-facing documentation."
            ))
            return risks
        if snapshot.repo_type in {"vscode_extension", "browser_extension"}:
            risks.append(RiskItem(
                title="Extension packaging and permission review needed",
                severity="medium",
                description="Extensions need clear packaging, activation, and permission boundaries to avoid runtime surprises.",
                evidence=[],
                recommendation="Review activation events, permissions, packaging metadata, and release documentation."
            ))
            if not snapshot.has_tests:
                risks.append(RiskItem(
                    title="No extension validation detected",
                    severity="medium",
                    description="No automated validation was detected for extension behavior or packaging workflows.",
                    evidence=[],
                    recommendation="Add tests or validation for key extension commands, permissions, and packaging."
                ))
            return risks
        if snapshot.repo_type in {"ml_model_repo", "data_science_notebooks", "research_code"}:
            risks.append(RiskItem(
                title="Reproducibility may be incomplete",
                severity="medium",
                description="Analytical and ML repositories need environment, data, and evaluation clarity for reproducibility.",
                evidence=[],
                recommendation="Document environment pinning, dataset assumptions, and how to reproduce experiments or inference."
            ))
            risks.append(RiskItem(
                title="Evaluation evidence may be limited",
                severity="medium",
                description="Model or analytical quality can be difficult to judge without explicit evaluation outputs or validation steps.",
                evidence=[],
                recommendation="Add evaluation metrics, validation scripts, or example outputs where practical."
            ))
            return risks
        if snapshot.repo_type in {"template", "monorepo"}:
            risks.append(RiskItem(
                title="Template assumptions may drift",
                severity="medium",
                description="Starter repositories become less reliable when placeholders, docs, or dependency baselines fall out of date.",
                evidence=[],
                recommendation="Keep starter dependencies, setup docs, and placeholder cleanup guidance current."
            ))
            return risks
        if snapshot.repo_type in {"infrastructure", "devops_automation"}:
            risks.append(RiskItem(
                title="Secrets and environment boundaries should be reviewed",
                severity="high",
                description="Infrastructure and automation repositories can expose operational risk if secret handling or environment separation is unclear.",
                evidence=[],
                recommendation="Document secret management, environment boundaries, rollback plans, and state handling."
            ))
            return risks
        if snapshot.repo_type == "design_assets":
            risks.append(RiskItem(
                title="Asset licensing and source management may be unclear",
                severity="medium",
                description="Design repositories need clear licensing, source-of-truth, and export-format conventions.",
                evidence=[],
                recommendation="Document licensing, naming, source files, and expected export formats for assets."
            ))
            return risks
        
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
