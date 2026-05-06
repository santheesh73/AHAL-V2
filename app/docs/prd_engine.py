import logging
from typing import Optional

from app.docs.models import PRDResult, PRDSection
from app.docs.generators.overview_generator import OverviewGenerator
from app.docs.generators.architecture_generator import ArchitectureGenerator
from app.docs.generators.tech_stack_generator import TechStackGenerator
from app.docs.generators.module_generator import ModuleGenerator
from app.docs.generators.workflow_generator import WorkflowGenerator
from app.docs.generators.api_generator import APIGenerator
from app.docs.generators.database_generator import DatabaseGenerator
from app.docs.generators.setup_generator import SetupGenerator
from app.docs.generators.risk_generator import RiskGenerator
from app.docs.generators.project_brief_generator import ProjectBriefGenerator
from app.docs.fact_snapshot import build_fact_snapshot
from app.intelligence.canonical_presenter import CanonicalProjectPresenter
from app.intelligence.consistency_validator import OutputConsistencyValidator
from app.intelligence.output_guard import CanonicalOutputGuard
from app.intelligence.product_identity import ProductIdentityResolver

logger = logging.getLogger(__name__)


def _safe_confidence_for_prd(value: str) -> str:
    lowered = str(value or "").lower()
    return lowered if lowered in {"high", "medium", "low"} else "low"

class PRDEngine:
    def __init__(self):
        self.overview_gen = OverviewGenerator()
        self.arch_gen = ArchitectureGenerator()
        self.tech_gen = TechStackGenerator()
        self.mod_gen = ModuleGenerator()
        self.workflow_gen = WorkflowGenerator()
        self.api_gen = APIGenerator()
        self.db_gen = DatabaseGenerator()
        self.setup_gen = SetupGenerator()
        self.risk_gen = RiskGenerator()
        self.brief_gen = ProjectBriefGenerator()
        self.canonical_presenter = CanonicalProjectPresenter()
        self.identity_resolver = ProductIdentityResolver()
        self.validator = OutputConsistencyValidator()

    def generate(
        self,
        scan_result,
        intelligence_result,
        graph_result,
        session_id: Optional[str] = None
    ) -> PRDResult:
        logger.info("Generating PRD", extra={"session_id": session_id})
        
        warnings = []
        identity = self.identity_resolver.resolve(scan_result=scan_result, intelligence_result=intelligence_result)
        snapshot = build_fact_snapshot(scan_result=scan_result, intelligence_result=intelligence_result, product_identity=identity)
        canonical = self.canonical_presenter.build(
            session_id=session_id or getattr(scan_result, "session_id", ""),
            scan_result=scan_result,
            intelligence_result=intelligence_result,
            graph_result=graph_result,
            prd_result=None,
        )
        
        # 1. overview
        try:
            overview = self.overview_gen.generate(scan_result, intelligence_result, canonical_intelligence=canonical)
            warnings.extend(overview.warnings)
        except Exception as e:
            logger.error(f"Error generating overview: {e}")
            warnings.append("Error generating overview; used deterministic fallback summary.")
            overview = self._fallback_section(
                "Overview",
                self.overview_gen._fallback_summary(scan_result, intelligence_result),
            )

        # 2. architecture
        try:
            architecture = self.arch_gen.generate(intelligence_result)
            warnings.extend(architecture.warnings)
        except Exception as e:
            logger.error(f"Error generating architecture: {e}")
            warnings.append("Error generating architecture; used deterministic fallback.")
            architecture = self._fallback_section(
                "Architecture",
                "Architecture details could not be synthesized fully, but the project appears to expose a backend API with supporting application modules.",
            )

        # 3. tech_stack
        try:
            tech_stack = self.tech_gen.generate(intelligence_result)
            warnings.extend(tech_stack.warnings)
        except Exception as e:
            logger.error(f"Error generating tech stack: {e}")
            warnings.append("Error generating tech stack; used deterministic fallback.")
            tech_stack = self._fallback_section(
                "Tech Stack",
                "Detected stack evidence was incomplete during generation, but the repository includes application and API-layer technology signals.",
            )

        # 4. modules
        try:
            modules = self.mod_gen.generate(intelligence_result)
        except Exception as e:
            logger.error(f"Error generating modules: {e}")
            warnings.append(f"Error generating modules: {e}")
            modules = []

        # 5. api_endpoints
        try:
            api_endpoints = self.api_gen.generate(intelligence_result)
        except Exception as e:
            logger.error(f"Error generating API endpoints: {e}")
            warnings.append(f"Error generating API endpoints: {e}")
            api_endpoints = []

        # 6. databases
        try:
            databases = self.db_gen.generate(intelligence_result, snapshot=snapshot)
            warnings.extend(databases.warnings)
        except Exception as e:
            logger.error(f"Error generating databases: {e}")
            warnings.append("Error generating databases; used deterministic fallback.")
            databases = self._fallback_section(
                "Databases",
                "Database/storage details could not be fully generated, but available evidence suggests the project includes persistent storage integration.",
            )

        # 7. workflow
        try:
            workflow, wf_warnings = self.workflow_gen.generate(intelligence_result, snapshot=snapshot)
            warnings.extend(wf_warnings)
        except Exception as e:
            logger.error(f"Error generating workflow: {e}")
            warnings.append(f"Error generating workflow: {e}")
            workflow = []
            wf_warnings = []

        # 8. setup_notes
        try:
            setup_notes = self.setup_gen.generate(scan_result, snapshot=snapshot)
            warnings.extend(setup_notes.warnings)
        except Exception as e:
            logger.error(f"Error generating setup notes: {e}")
            warnings.append("Error generating setup notes; used deterministic fallback.")
            setup_notes = self._fallback_section(
                "Setup Notes",
                "Setup notes could not be generated fully. Review the repository entrypoints, dependency manifests, and environment configuration files for run instructions.",
            )

        # 9. risks
        try:
            risks = self.risk_gen.generate(scan_result, intelligence_result, wf_warnings, snapshot=snapshot)
        except Exception as e:
            logger.error(f"Error generating risks: {e}")
            warnings.append(f"Error generating risks: {e}")
            risks = []

        # 10. confidence/evidence count
        evidence_count = sum(
            len(x.evidence) for x in [overview, architecture, tech_stack, databases, setup_notes]
        ) + sum(len(m.evidence) for m in modules) + \
            sum(len(a.evidence) for a in api_endpoints) + \
            sum(len(w.evidence) for w in workflow) + \
            sum(len(r.evidence) for r in risks)

        # 9.5 Project Intelligence Brief
        try:
            project_brief = self.brief_gen.generate(
                scan_result,
                intelligence_result,
                graph_result,
                overview,
                risks,
                snapshot=snapshot,
                product_identity=identity,
                canonical_intelligence=canonical,
            )
            warnings.extend(project_brief.warnings)
            evidence_count += sum(len(x.evidence) for x in [project_brief.goal, project_brief.what, project_brief.why])
            evidence_count += sum(len(x.evidence) for x in project_brief.completed)
            evidence_count += sum(len(x.evidence) for x in project_brief.remaining)
        except Exception as e:
            logger.error(f"Error generating project brief: {e}")
            warnings.append(f"Error generating project brief: {e}")
            project_brief = None

        # Overall confidence
        high_confs = sum(1 for x in [overview, architecture, tech_stack] if x.confidence == "high")
        confidence = "high" if high_confs >= 2 else "medium" if high_confs >= 1 else "low"

        from app.docs.utils.section_utils import safe_str
        arch_obj = getattr(intelligence_result, "architecture", None)
        project_type_val = getattr(arch_obj, "type", arch_obj)
        project_type_str = safe_str(project_type_val, "unknown")

        prd = PRDResult(
            session_id=session_id,
            title="Project Requirements Document",
            project_type=canonical.project_type or project_type_str,
            architecture_label=identity.architecture,
            repo_intelligence_score=identity.repo_intelligence_score,
            architecture_confidence=_safe_confidence_for_prd(canonical.confidence.architecture),
            product_purpose_confidence=_safe_confidence_for_prd(canonical.confidence.product_purpose),
            overview=overview,
            project_brief=project_brief,
            architecture=architecture,
            tech_stack=tech_stack,
            modules=modules,
            api_endpoints=api_endpoints,
            databases=databases,
            workflow=workflow,
            setup_notes=setup_notes,
            risks=risks,
            confidence=confidence,
            evidence_count=evidence_count,
            warnings=warnings,
            canonical_intelligence=canonical,
        )
        prd.architecture_label = identity.architecture
        prd.repo_intelligence_score = identity.repo_intelligence_score
        if prd.canonical_intelligence is not None:
            from app.docs.models import APISectionItem, ProjectStatusItem, RiskItem, WorkflowSectionItem
            prd.overview.content = prd.canonical_intelligence.product_summary
            if prd.project_brief is not None:
                prd.project_brief.goal.content = prd.canonical_intelligence.product_summary
                prd.project_brief.what.content = prd.canonical_intelligence.what
                prd.project_brief.why.content = prd.canonical_intelligence.why
                prd.project_brief.completed = [
                    ProjectStatusItem(
                        title=item.title,
                        status="built",
                        description=item.description,
                        evidence=[],
                        confidence=_safe_confidence_for_prd(item.confidence),
                    )
                    for item in prd.canonical_intelligence.completed
                ]
                prd.project_brief.remaining = [
                    ProjectStatusItem(
                        title=item.title,
                        status="missing",
                        description=item.description,
                        evidence=[],
                        confidence=_safe_confidence_for_prd(item.confidence),
                    )
                    for item in prd.canonical_intelligence.remaining
                ]
                prd.project_brief.issues = [
                    RiskItem(
                        severity=str(item.severity or "medium").lower() if str(item.severity or "").lower() in {"high", "medium", "low"} else "medium",
                        title=item.title,
                        description=item.title,
                        evidence=[],
                        recommendation=item.recommendation,
                    )
                    for item in prd.canonical_intelligence.issues
                ]
                if prd.project_brief.what.content != prd.canonical_intelligence.what:
                    prd.project_brief.what.content = prd.canonical_intelligence.what
                assert prd.project_brief.what.content == prd.canonical_intelligence.what
            prd.api_endpoints = [
                APISectionItem(
                    method=item.method,
                    path=item.path,
                    framework=item.source,
                    source_file=item.source,
                    handler=None,
                    description=item.purpose,
                    evidence=[],
                    confidence="medium",
                )
                for item in prd.canonical_intelligence.api_surface
            ]
            prd.workflow = [
                WorkflowSectionItem(
                    order=item.step,
                    source=item.title,
                    action=item.description,
                    target=None,
                    evidence=[],
                    confidence="medium",
                )
                for item in prd.canonical_intelligence.workflow
            ]
            stack_lines = []
            if prd.canonical_intelligence.tech_stack.languages:
                stack_lines.append(f"Languages: {', '.join(prd.canonical_intelligence.tech_stack.languages)}")
            if prd.canonical_intelligence.tech_stack.frameworks:
                stack_lines.append(f"Frameworks: {', '.join(prd.canonical_intelligence.tech_stack.frameworks)}")
            if prd.canonical_intelligence.tech_stack.databases:
                stack_lines.append(f"Databases / Storage: {', '.join(prd.canonical_intelligence.tech_stack.databases)}")
            if prd.canonical_intelligence.tech_stack.tools:
                stack_lines.append(f"Tools: {', '.join(prd.canonical_intelligence.tech_stack.tools)}")
            if stack_lines:
                prd.tech_stack.content = ". ".join(stack_lines) + "."
            prd.databases.content = (
                f"Databases / storage detected: {', '.join(prd.canonical_intelligence.tech_stack.databases)}."
                if prd.canonical_intelligence.tech_stack.databases
                else "No database or storage layer was confirmed from the analyzed evidence."
            )
            prd.overview.content = CanonicalOutputGuard.sanitize_text(prd.overview.content, prd.canonical_intelligence)
            if prd.project_brief is not None:
                prd.project_brief.goal.content = CanonicalOutputGuard.sanitize_text(prd.project_brief.goal.content, prd.canonical_intelligence)
                prd.project_brief.what.content = prd.canonical_intelligence.what
                prd.project_brief.why.content = CanonicalOutputGuard.sanitize_text(prd.project_brief.why.content, prd.canonical_intelligence)
        return self.validator.validate_prd(prd, identity)

    def _fallback_section(self, title: str, content: str) -> PRDSection:
        return PRDSection(title=title, content=content, confidence="low")
