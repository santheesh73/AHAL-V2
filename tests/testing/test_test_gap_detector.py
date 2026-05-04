from __future__ import annotations

from app.testing import TestGapDetector
from tests.intelligence.conftest import empty_scan_result, make_scan_result


def _api_scan(with_tests: bool = False, with_pytest_ini: bool = False):
    files = [{"path": "app/api/analyze.py", "extension": ".py"}]
    contents = {
        "app/api/analyze.py": 'from fastapi import APIRouter\nrouter = APIRouter()\n@router.post("/analyze/code")\ndef analyze_code():\n    return {"ok": True}\n',
    }
    if with_tests:
        files.append({"path": "tests/api/test_code_analysis.py", "extension": ".py"})
        contents["tests/api/test_code_analysis.py"] = 'def test_analyze_code(client):\n    response = client.post("/analyze/code")\n    assert response.status_code == 200\n'
    if with_pytest_ini:
        files.append({"path": "pytest.ini", "extension": ".ini"})
        contents["pytest.ini"] = "[pytest]\n"
    return make_scan_result(files=files, contents=contents)


def test_detects_test_files_in_tests():
    result = TestGapDetector().detect("s1", _api_scan(with_tests=True))
    assert any("tests/api/test_code_analysis.py" in item for item in result.tested_evidence)


def test_detects_pytest_vitest_jest_config():
    scan = make_scan_result(
        files=[
            {"path": "app/api/analyze.py", "extension": ".py"},
            {"path": "pytest.ini", "extension": ".ini"},
            {"path": "package.json", "extension": ".json"},
        ],
        contents={
            "app/api/analyze.py": 'from fastapi import APIRouter\nrouter = APIRouter()\n@router.get("/health")\ndef health(): return {"ok": True}\n',
            "pytest.ini": "[pytest]\n",
            "package.json": '{"devDependencies":{"vitest":"1.0.0","jest":"29.0.0"}}',
        },
    )
    result = TestGapDetector().detect("s2", scan)
    payload = " ".join(result.tested_evidence).lower()
    assert "pytest.ini" in payload
    assert "package.json" in payload


def test_api_endpoint_without_test_becomes_high_priority_gap():
    result = TestGapDetector().detect("s3", _api_scan(with_tests=False))
    assert any(item.target_type == "api" and item.priority == "high" for item in result.gaps)


def test_api_endpoint_with_matching_test_is_not_a_gap():
    result = TestGapDetector().detect("s4", _api_scan(with_tests=True))
    assert not any(item.target_type == "api" and "/analyze/code" in item.target for item in result.gaps)


def test_session_auth_module_without_test_becomes_high_priority():
    scan = make_scan_result(
        files=[{"path": "app/auth/session_manager.py", "extension": ".py"}],
        contents={"app/auth/session_manager.py": "def issue_session_token(user_id):\n    return str(user_id)\n"},
    )
    result = TestGapDetector().detect("s5", scan)
    assert any(item.target_type == "auth" and item.priority == "high" for item in result.gaps)


def test_database_model_module_without_test_becomes_high_priority():
    scan = make_scan_result(
        files=[{"path": "app/models/user.py", "extension": ".py"}],
        contents={"app/models/user.py": "from pydantic import BaseModel\nclass User(BaseModel):\n    name: str\n"},
    )
    result = TestGapDetector().detect("s6", scan)
    assert any(item.target_type == "database" and item.priority in {"high", "medium"} for item in result.gaps)


def test_service_module_without_test_becomes_medium_priority():
    scan = make_scan_result(
        files=[{"path": "app/services/repo_indexer.py", "extension": ".py"}],
        contents={"app/services/repo_indexer.py": "def build_index(items):\n    return list(items)\n"},
    )
    result = TestGapDetector().detect("s7", scan)
    assert any(item.target_type in {"service", "module"} and item.priority == "medium" for item in result.gaps)


def test_docs_only_files_are_low_or_ignored():
    scan = make_scan_result(
        files=[{"path": "README.md", "extension": ".md"}],
        contents={"README.md": "# Project\nSome docs.\n"},
    )
    result = TestGapDetector().detect("s8", scan)
    assert result.gap_count == 0


def test_include_low_priority_false_hides_low_gaps():
    scan = make_scan_result(
        files=[{"path": "README.md", "extension": ".md"}],
        contents={"README.md": "# Project\nSome docs.\n"},
    )
    result = TestGapDetector().detect("s9", scan, include_low_priority=False)
    assert result.gap_count == 0


def test_include_low_priority_true_includes_low_gaps():
    scan = make_scan_result(
        files=[{"path": "README.md", "extension": ".md"}],
        contents={"README.md": "# Project\nSome docs.\n"},
    )
    result = TestGapDetector().detect("s10", scan, include_low_priority=True)
    assert any(item.priority == "low" for item in result.gaps)


def test_empty_project_returns_safe_warning():
    result = TestGapDetector().detect("s11", empty_scan_result())
    assert result.warnings
    assert result.confidence == "low"


def test_no_raw_repr_leakage():
    result = TestGapDetector().detect("s12", _api_scan(with_tests=True, with_pytest_ini=True))
    payload = str(result.model_dump()).lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
