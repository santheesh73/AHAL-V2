"""Tests for LanguageDetector."""

from app.intelligence.detectors.language_detector import LanguageDetector
from tests.intelligence.conftest import empty_scan_result, make_scan_result, python_fastapi_scan, react_nextjs_scan


def test_python_detected():
    scan = python_fastapi_scan()
    detector = LanguageDetector()
    results = detector.detect(scan)
    names = [r.name for r in results]
    assert "Python" in names


def test_typescript_detected():
    scan = react_nextjs_scan()
    detector = LanguageDetector()
    results = detector.detect(scan)
    names = [r.name for r in results]
    assert "TypeScript" in names


def test_mixed_language_percentages():
    scan = make_scan_result(files=[
        {"path": "app.py", "extension": ".py"},
        {"path": "utils.py", "extension": ".py"},
        {"path": "index.ts", "extension": ".ts"},
    ])
    detector = LanguageDetector()
    results = detector.detect(scan)
    py = next(r for r in results if r.name == "Python")
    ts = next(r for r in results if r.name == "TypeScript")
    assert py.percentage > ts.percentage
    assert abs(py.percentage + ts.percentage - 100.0) < 0.01


def test_unknown_extensions_ignored():
    scan = make_scan_result(files=[
        {"path": "data.xyz", "extension": ".xyz"},
        {"path": "readme.md", "extension": ".md"},
    ])
    detector = LanguageDetector()
    results = detector.detect(scan)
    assert len(results) == 0


def test_empty_scan_returns_empty():
    detector = LanguageDetector()
    results = detector.detect(empty_scan_result())
    assert results == []


def test_confidence_high_when_three_or_more():
    scan = make_scan_result(files=[
        {"path": "a.py"}, {"path": "b.py"}, {"path": "c.py"},
    ])
    detector = LanguageDetector()
    results = detector.detect(scan)
    py = next(r for r in results if r.name == "Python")
    assert py.confidence == "high"


def test_confidence_medium_when_one_or_two():
    scan = make_scan_result(files=[{"path": "a.py"}])
    detector = LanguageDetector()
    results = detector.detect(scan)
    py = next(r for r in results if r.name == "Python")
    assert py.confidence == "medium"


def test_every_language_has_evidence():
    scan = python_fastapi_scan()
    detector = LanguageDetector()
    for lang in detector.detect(scan):
        assert len(lang.evidence) > 0
        for e in lang.evidence:
            assert e.file
            assert e.reason
