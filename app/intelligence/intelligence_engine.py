"""
AHAL AI — Intelligence Engine Orchestrator (Phase 2, Step 13)

Central orchestrator that runs all detectors, classifiers, and inferers
in the correct order and assembles the IntelligenceResult.

Never mutates ScanResult.
Never crashes on empty results.
Deterministic when LLM is disabled.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.intelligence.classifiers.architecture_classifier import ArchitectureClassifier
from app.intelligence.classifiers.module_classifier import ModuleClassifier
from app.intelligence.detectors.api_detector import APIDetector
from app.intelligence.detectors.database_detector import DatabaseDetector
from app.intelligence.detectors.dependency_detector import DependencyDetector
from app.intelligence.detectors.entrypoint_detector import EntryPointDetector
from app.intelligence.detectors.framework_detector import FrameworkDetector
from app.intelligence.detectors.language_detector import LanguageDetector
from app.intelligence.models import IntelligenceResult, LLMExplanation
from app.intelligence.utils.confidence import calculate_confidence_score
from app.intelligence.workflow.workflow_inferer import WorkflowInferer
from app.models.file_schema import ScanResult

logger = logging.getLogger("ahal.intelligence")


class IntelligenceEngine:
    """
    Orchestrates all Phase 2 intelligence analysis.

    Execution order:
        1. Language detection
        2. Dependency detection
        3. Framework detection (uses deps)
        4. Entry point detection (uses frameworks)
        5. API detection (uses frameworks)
        6. Database detection (uses deps, frameworks)
        7. Module classification
        8. Architecture classification (uses all above)
        9. Workflow inference (uses all above)
       10. Confidence scoring
       11. Optional LLM explanation
    """

    def __init__(self) -> None:
        self._lang_detector = LanguageDetector()
        self._dep_detector = DependencyDetector()
        self._fw_detector = FrameworkDetector()
        self._ep_detector = EntryPointDetector()
        self._api_detector = APIDetector()
        self._db_detector = DatabaseDetector()
        self._mod_classifier = ModuleClassifier()
        self._arch_classifier = ArchitectureClassifier()
        self._wf_inferer = WorkflowInferer()

    def analyze(
        self,
        scan_result: ScanResult,
        session_id: Optional[str] = None,
        include_llm_explanation: bool = False,
    ) -> IntelligenceResult:
        """
        Run full intelligence pipeline on a completed ScanResult.
        Returns IntelligenceResult with all detections, classifications, and scores.
        """
        warnings: List[str] = []

        # ── 1. Languages ────────────────────────────────────────
        try:
            languages = self._lang_detector.detect(scan_result)
        except Exception as e:
            logger.error("Language detection failed: %s", e)
            languages = []
            warnings.append(f"Language detection failed: {e}")

        # ── 2. Dependencies ─────────────────────────────────────
        try:
            dependencies = self._dep_detector.detect(scan_result)
        except Exception as e:
            logger.error("Dependency detection failed: %s", e)
            dependencies = []
            warnings.append(f"Dependency detection failed: {e}")

        # ── 3. Frameworks ───────────────────────────────────────
        try:
            frameworks = self._fw_detector.detect(scan_result, dependencies=dependencies)
        except Exception as e:
            logger.error("Framework detection failed: %s", e)
            frameworks = []
            warnings.append(f"Framework detection failed: {e}")

        # ── 4. Entry points ─────────────────────────────────────
        try:
            entry_points = self._ep_detector.detect(scan_result, frameworks=frameworks)
        except Exception as e:
            logger.error("Entry point detection failed: %s", e)
            entry_points = []
            warnings.append(f"Entry point detection failed: {e}")

        # ── 5. API endpoints ────────────────────────────────────
        try:
            api_endpoints = self._api_detector.detect(scan_result, frameworks=frameworks)
        except Exception as e:
            logger.error("API detection failed: %s", e)
            api_endpoints = []
            warnings.append(f"API detection failed: {e}")

        # ── 6. Databases ────────────────────────────────────────
        try:
            databases = self._db_detector.detect(
                scan_result, dependencies=dependencies, frameworks=frameworks,
            )
        except Exception as e:
            logger.error("Database detection failed: %s", e)
            databases = []
            warnings.append(f"Database detection failed: {e}")

        # ── 7. Modules ──────────────────────────────────────────
        try:
            modules = self._mod_classifier.classify(scan_result)
        except Exception as e:
            logger.error("Module classification failed: %s", e)
            modules = []
            warnings.append(f"Module classification failed: {e}")

        # ── 8. Architecture ─────────────────────────────────────
        try:
            architecture = self._arch_classifier.classify(
                scan_result,
                languages=languages,
                frameworks=frameworks,
                entry_points=entry_points,
                modules=modules,
                api_endpoints=api_endpoints,
                databases=databases,
                dependencies=dependencies,
            )
        except Exception as e:
            logger.error("Architecture classification failed: %s", e)
            from app.intelligence.models import ArchitectureResult
            architecture = ArchitectureResult()
            warnings.append(f"Architecture classification failed: {e}")

        # ── 9. Workflow ─────────────────────────────────────────
        try:
            workflow = self._wf_inferer.infer(
                scan_result,
                architecture=architecture,
                frameworks=frameworks,
                entry_points=entry_points,
                modules=modules,
                api_endpoints=api_endpoints,
                databases=databases,
            )
        except Exception as e:
            logger.error("Workflow inference failed: %s", e)
            from app.intelligence.models import WorkflowResult
            workflow = WorkflowResult()
            warnings.append(f"Workflow inference failed: {e}")

        # ── 10. Confidence score ────────────────────────────────
        try:
            confidence_score = calculate_confidence_score(
                languages=languages,
                dependencies=dependencies,
                frameworks=frameworks,
                entry_points=entry_points,
                api_endpoints=api_endpoints,
                databases=databases,
                modules=modules,
                architecture=architecture,
                workflow=workflow,
            )
        except Exception as e:
            logger.error("Confidence scoring failed: %s", e)
            confidence_score = 0.0
            warnings.append(f"Confidence scoring failed: {e}")

        # ── Evidence count ──────────────────────────────────────
        evidence_count = self._count_evidence(
            languages, dependencies, frameworks, entry_points,
            api_endpoints, databases, modules, architecture, workflow,
        )

        # ── Project type ────────────────────────────────────────
        project_type = architecture.type

        # ── 11. Optional LLM explanation ────────────────────────
        explanation: Optional[LLMExplanation] = None
        if include_llm_explanation:
            try:
                from app.intelligence.llm.explanation_service import ExplanationService
                svc = ExplanationService()
                explanation = svc.explain(IntelligenceResult(
                    session_id=session_id,
                    project_type=project_type,
                    languages=languages,
                    dependencies=dependencies,
                    frameworks=frameworks,
                    entry_points=entry_points,
                    api_endpoints=api_endpoints,
                    databases=databases,
                    modules=modules,
                    architecture=architecture,
                    workflow=workflow,
                    warnings=warnings,
                    evidence_count=evidence_count,
                    confidence_score=confidence_score,
                ))
            except Exception as e:
                logger.error("LLM explanation failed: %s", e)
                explanation = LLMExplanation(
                    model="",
                    content="",
                    used=False,
                    error=f"LLM explanation failed: {e}",
                )
                warnings.append(f"LLM explanation unavailable: {e}")

        return IntelligenceResult(
            session_id=session_id,
            project_type=project_type,
            languages=languages,
            dependencies=dependencies,
            frameworks=frameworks,
            entry_points=entry_points,
            api_endpoints=api_endpoints,
            databases=databases,
            modules=modules,
            architecture=architecture,
            workflow=workflow,
            warnings=warnings,
            evidence_count=evidence_count,
            confidence_score=confidence_score,
            explanation=explanation,
        )

    def _count_evidence(self, *args) -> int:
        """Count total evidence items across all detections."""
        count = 0
        for collection in args:
            if isinstance(collection, list):
                for item in collection:
                    if hasattr(item, "evidence"):
                        count += len(item.evidence)
            elif hasattr(collection, "evidence"):
                count += len(collection.evidence)
            # WorkflowResult has steps with evidence
            if hasattr(collection, "steps"):
                for step in collection.steps:
                    if hasattr(step, "evidence"):
                        count += len(step.evidence)
        return count
