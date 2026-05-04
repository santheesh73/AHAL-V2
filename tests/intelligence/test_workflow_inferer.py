"""Tests for WorkflowInferer."""

from app.intelligence.classifiers.architecture_classifier import ArchitectureClassifier
from app.intelligence.classifiers.module_classifier import ModuleClassifier
from app.intelligence.detectors.api_detector import APIDetector
from app.intelligence.detectors.database_detector import DatabaseDetector
from app.intelligence.detectors.dependency_detector import DependencyDetector
from app.intelligence.detectors.entrypoint_detector import EntryPointDetector
from app.intelligence.detectors.framework_detector import FrameworkDetector
from app.intelligence.workflow.workflow_inferer import WorkflowInferer
from tests.intelligence.conftest import (
    empty_scan_result,
    fullstack_scan,
    make_scan_result,
    python_fastapi_scan,
    react_nextjs_scan,
)


def _full_workflow(scan):
    """Run full pipeline and return workflow result."""
    deps = DependencyDetector().detect(scan)
    fws = FrameworkDetector().detect(scan, dependencies=deps)
    eps = EntryPointDetector().detect(scan, frameworks=fws)
    apis = APIDetector().detect(scan, frameworks=fws)
    dbs = DatabaseDetector().detect(scan, dependencies=deps, frameworks=fws)
    mods = ModuleClassifier().classify(scan)
    arch = ArchitectureClassifier().classify(
        scan, frameworks=fws, entry_points=eps, modules=mods,
        api_endpoints=apis, databases=dbs, dependencies=deps,
    )
    return WorkflowInferer().infer(
        scan, architecture=arch, frameworks=fws, entry_points=eps,
        modules=mods, api_endpoints=apis, databases=dbs,
    )


def test_fastapi_minimal_workflow():
    wf = _full_workflow(python_fastapi_scan())
    assert len(wf.steps) >= 2
    assert wf.completeness in ("complete", "partial")


def test_react_frontend_partial_workflow():
    wf = _full_workflow(react_nextjs_scan())
    assert len(wf.steps) >= 1
    # Should have a frontend step
    sources = [s.source for s in wf.steps]
    assert "User" in sources


def test_fullstack_partial_workflow():
    wf = _full_workflow(fullstack_scan())
    assert len(wf.steps) >= 3
    assert wf.completeness in ("complete", "partial")


def test_database_step_only_when_db_evidence():
    """No database in scan → no database step in workflow."""
    scan = make_scan_result(
        files=[{"path": "app.py", "extension": ".py"}],
        contents={"app.py": "from flask import Flask\napp = Flask(__name__)\n"},
    )
    wf = _full_workflow(scan)
    db_steps = [s for s in wf.steps if "database" in s.action.lower() or "queries" in s.action.lower()]
    assert len(db_steps) == 0


def test_unknown_when_insufficient_evidence():
    scan = make_scan_result(
        files=[{"path": "data.txt"}],
        contents={"data.txt": "hello world\n"},
    )
    wf = _full_workflow(scan)
    assert wf.completeness in ("unknown", "minimal")


def test_every_step_has_evidence():
    wf = _full_workflow(python_fastapi_scan())
    for step in wf.steps:
        assert len(step.evidence) > 0, f"Step {step.order} '{step.action}' has no evidence"


def test_empty_scan():
    wf = _full_workflow(empty_scan_result())
    assert wf.completeness == "unknown"
    assert len(wf.steps) == 0
