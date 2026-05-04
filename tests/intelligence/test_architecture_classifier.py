"""Tests for ArchitectureClassifier."""

from app.intelligence.classifiers.architecture_classifier import ArchitectureClassifier
from app.intelligence.detectors.api_detector import APIDetector
from app.intelligence.detectors.database_detector import DatabaseDetector
from app.intelligence.detectors.dependency_detector import DependencyDetector
from app.intelligence.detectors.entrypoint_detector import EntryPointDetector
from app.intelligence.detectors.framework_detector import FrameworkDetector
from app.intelligence.detectors.language_detector import LanguageDetector
from app.intelligence.classifiers.module_classifier import ModuleClassifier
from tests.intelligence.conftest import (
    empty_scan_result,
    express_mongo_scan,
    fullstack_scan,
    make_scan_result,
    python_fastapi_scan,
    react_nextjs_scan,
)


def _full_classify(scan):
    """Run full pipeline and return architecture result."""
    langs = LanguageDetector().detect(scan)
    deps = DependencyDetector().detect(scan)
    fws = FrameworkDetector().detect(scan, dependencies=deps)
    eps = EntryPointDetector().detect(scan, frameworks=fws)
    apis = APIDetector().detect(scan, frameworks=fws)
    dbs = DatabaseDetector().detect(scan, dependencies=deps, frameworks=fws)
    mods = ModuleClassifier().classify(scan)

    return ArchitectureClassifier().classify(
        scan,
        languages=langs,
        frameworks=fws,
        entry_points=eps,
        modules=mods,
        api_endpoints=apis,
        databases=dbs,
        dependencies=deps,
    )


def test_frontend_only():
    arch = _full_classify(react_nextjs_scan())
    assert arch.type == "frontend"
    assert arch.confidence in ("high", "medium")


def test_backend_only():
    arch = _full_classify(python_fastapi_scan())
    assert arch.type == "backend"
    assert arch.confidence in ("high", "medium")


def test_fullstack():
    arch = _full_classify(fullstack_scan())
    assert arch.type == "fullstack"


def test_cli():
    scan = make_scan_result(
        files=[
            {"path": "cli.py", "extension": ".py"},
            {"path": "pyproject.toml", "extension": ".toml"},
        ],
        contents={
            "cli.py": "import click\n\n@click.command()\ndef main():\n    click.echo('hello')\n",
            "pyproject.toml": '[project]\nname = "mytool"\n\n[project.scripts]\nmytool = "cli:main"\n\n[project.dependencies]\nclick = ">=8.0"\n',
        },
    )
    arch = _full_classify(scan)
    assert arch.type == "cli"


def test_library():
    scan = make_scan_result(
        files=[
            {"path": "setup.py", "extension": ".py"},
            {"path": "mylib/__init__.py", "extension": ".py"},
            {"path": "mylib/core.py", "extension": ".py"},
        ],
        contents={
            "setup.py": "from setuptools import setup\nsetup(name='mylib', version='1.0')\n",
            "mylib/__init__.py": "",
            "mylib/core.py": "def add(a, b): return a + b\n",
        },
    )
    arch = _full_classify(scan)
    assert arch.type == "library"


def test_unknown_with_insufficient_evidence():
    scan = make_scan_result(
        files=[{"path": "data.csv"}],
        contents={"data.csv": "a,b,c\n1,2,3\n"},
    )
    arch = _full_classify(scan)
    assert arch.type == "unknown"
    assert arch.confidence == "low"


def test_empty_scan():
    arch = _full_classify(empty_scan_result())
    assert arch.type == "unknown"


def test_architecture_has_reasoning():
    arch = _full_classify(python_fastapi_scan())
    assert len(arch.reasoning) > 0
