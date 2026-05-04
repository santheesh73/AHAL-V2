from __future__ import annotations

from app.context.smart_context_selector import SmartContextSelector
from tests.intelligence.conftest import make_scan_result


def test_prioritizes_readme_entrypoints_routes_services():
    scan = make_scan_result(
        files=[
            {"path": "README.md"},
            {"path": "app.py"},
            {"path": "app/api/routes.py"},
            {"path": "app/services/reporting.py"},
        ],
        contents={
            "README.md": "Project docs",
            "app.py": "from fastapi import FastAPI\napp = FastAPI()",
            "app/api/routes.py": "@router.get('/health')\ndef health():\n    pass",
            "app/services/reporting.py": "def build_report():\n    pass",
        },
    )
    selected = SmartContextSelector().select(scan)
    assert selected.files
    assert selected.files[0].path == "README.md"
    assert any(item.path == "app.py" for item in selected.files)


def test_ignored_paths_excluded():
    scan = make_scan_result(
        contents={
            "node_modules/lib/index.js": "console.log('x')",
            "src/app.py": "print('ok')",
        }
    )
    selected = SmartContextSelector().select(scan)
    assert all("node_modules" not in item.path for item in selected.files)


def test_context_char_budget_enforced(monkeypatch):
    from app.config import config

    old_total = config.scanner.max_total_context_chars
    old_file = config.scanner.max_file_context_chars
    object.__setattr__(config.scanner, "max_total_context_chars", 20)
    object.__setattr__(config.scanner, "max_file_context_chars", 15)
    try:
        scan = make_scan_result(
            contents={
                "README.md": "a" * 50,
                "app.py": "b" * 50,
            }
        )
        selected = SmartContextSelector().select(scan)
        assert selected.total_chars <= 20
        assert all(len(item.excerpt) <= 15 for item in selected.files)
    finally:
        object.__setattr__(config.scanner, "max_total_context_chars", old_total)
        object.__setattr__(config.scanner, "max_file_context_chars", old_file)


def test_deterministic_order():
    scan = make_scan_result(
        contents={
            "README.md": "docs",
            "app.py": "code",
            "services/a.py": "a",
            "services/b.py": "b",
        }
    )
    first = [item.path for item in SmartContextSelector().select(scan).files]
    second = [item.path for item in SmartContextSelector().select(scan).files]
    assert first == second


def test_empty_repo_no_crash():
    selected = SmartContextSelector().select(make_scan_result(contents={}))
    assert selected.files == []
    assert selected.confidence == "low"


def test_env_files_excluded():
    scan = make_scan_result(contents={".env": "SECRET=123", "app.py": "print('ok')"})
    selected = SmartContextSelector().select(scan)
    assert all(item.path != ".env" for item in selected.files)


def test_secret_files_excluded():
    scan = make_scan_result(contents={"secrets.env": "API_KEY=123", "app.py": "print('ok')"})
    selected = SmartContextSelector().select(scan)
    assert all("secret" not in item.path.lower() for item in selected.files)


def test_budget_enforced(monkeypatch):
    from app.config import config

    old_total = config.scanner.max_total_context_chars
    object.__setattr__(config.scanner, "max_total_context_chars", 5)
    try:
        scan = make_scan_result(contents={"README.md": "123456789", "app.py": "abcdef"})
        selected = SmartContextSelector().select(scan)
        assert selected.total_chars <= 5
    finally:
        object.__setattr__(config.scanner, "max_total_context_chars", old_total)
