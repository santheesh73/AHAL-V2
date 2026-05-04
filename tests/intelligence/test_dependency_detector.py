"""Tests for DependencyDetector."""

from app.intelligence.detectors.dependency_detector import DependencyDetector
from tests.intelligence.conftest import empty_scan_result, make_scan_result, python_fastapi_scan, react_nextjs_scan


def test_package_json_dependencies():
    scan = react_nextjs_scan()
    detector = DependencyDetector()
    deps = detector.detect(scan)
    names = [d.name for d in deps]
    assert "react" in names
    assert "next" in names


def test_package_json_dev_dependencies():
    scan = react_nextjs_scan()
    detector = DependencyDetector()
    deps = detector.detect(scan)
    names = [d.name for d in deps]
    assert "typescript" in names


def test_requirements_txt_dependencies():
    scan = python_fastapi_scan()
    detector = DependencyDetector()
    deps = detector.detect(scan)
    names = [d.name for d in deps]
    assert "fastapi" in names
    assert "uvicorn" in names
    assert "asyncpg" in names


def test_pyproject_dependency_lines():
    scan = make_scan_result(
        files=[{"path": "pyproject.toml", "extension": ".toml"}],
        contents={
            "pyproject.toml": '[project]\nname = "mylib"\n\n[project.dependencies]\nrequests = ">=2.28"\nclick = ">=8.0"\n',
        },
    )
    detector = DependencyDetector()
    deps = detector.detect(scan)
    names = [d.name for d in deps]
    assert "requests" in names or "click" in names


def test_malformed_package_json_does_not_crash():
    scan = make_scan_result(
        files=[{"path": "package.json", "extension": ".json"}],
        contents={"package.json": "THIS IS NOT JSON {{{"},
    )
    detector = DependencyDetector()
    deps = detector.detect(scan)
    assert isinstance(deps, list)  # No crash


def test_duplicate_dependencies_deduped():
    scan = make_scan_result(
        files=[
            {"path": "requirements.txt", "extension": ".txt"},
        ],
        contents={
            "requirements.txt": "fastapi\nfastapi>=0.100\n",
        },
    )
    detector = DependencyDetector()
    deps = detector.detect(scan)
    fastapi_deps = [d for d in deps if d.name.lower() == "fastapi"]
    assert len(fastapi_deps) == 1


def test_empty_scan_returns_empty():
    detector = DependencyDetector()
    assert detector.detect(empty_scan_result()) == []


def test_every_dep_has_evidence():
    scan = python_fastapi_scan()
    detector = DependencyDetector()
    for dep in detector.detect(scan):
        assert len(dep.evidence) > 0
        assert dep.source_file


def test_categorization_applied():
    scan = python_fastapi_scan()
    detector = DependencyDetector()
    deps = detector.detect(scan)
    fastapi = next(d for d in deps if d.name == "fastapi")
    assert fastapi.category == "backend"


def test_go_mod_parsing():
    scan = make_scan_result(
        files=[{"path": "go.mod", "extension": ".mod"}],
        contents={"go.mod": "module example.com/myapp\n\ngo 1.21\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.9.0\n)\n"},
    )
    detector = DependencyDetector()
    deps = detector.detect(scan)
    assert len(deps) >= 1
    assert any("gin" in d.name for d in deps)
