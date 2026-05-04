"""
AHAL AI — Scanner Unit Tests

Tests:
  - FileFilter: ignored extensions excluded
  - FileFilter: ignored directories excluded
  - FileFilter: hidden files (dot-prefix) excluded
  - FileFilter: known dotfiles allowed
  - PriorityHandler: main.py → HIGH
  - PriorityHandler: utils/ → MEDIUM
  - PriorityHandler: tests/ → LOW
  - PriorityHandler: unknown dir → MEDIUM (default)
  - safe_utils: safe_decode never raises
  - safe_utils: safe_read_file never raises on bad path
  - safe_utils: is_likely_binary detects null bytes
  - safe_utils: normalize_path strips leading slashes
  - safe_utils: clamp stays within bounds
  - content cap: total content never exceeds budget
"""

from __future__ import annotations

import io
import os
import zipfile

import pytest

from app.config import config
from app.core.scanner.file_filter import FileFilter
from app.core.scanner.priority_handler import PriorityHandler
from app.utils.safe_utils import (
    clamp,
    is_likely_binary,
    normalize_path,
    safe_decode,
    safe_extension,
    safe_read_file,
)


# ── FileFilter ────────────────────────────────────────────────────

@pytest.fixture
def ff() -> FileFilter:
    return FileFilter(config.scanner)


def test_filter_ignores_exe(ff: FileFilter):
    include, reason = ff.should_include("app/binary.exe", 100)
    assert include is False
    assert "ignored_extension" in reason


def test_filter_ignores_dll(ff: FileFilter):
    include, _ = ff.should_include("lib/something.dll", 100)
    assert include is False


def test_filter_ignores_node_modules(ff: FileFilter):
    include, reason = ff.should_include("node_modules/lodash/index.js", 100)
    assert include is False
    assert "ignored_directory" in reason


def test_filter_ignores_git_dir(ff: FileFilter):
    include, reason = ff.should_include(".git/config", 100)
    assert include is False


def test_filter_ignores_hidden_file(ff: FileFilter):
    include, reason = ff.should_include(".hidden_secret", 100)
    assert include is False
    assert "hidden_file" in reason


def test_filter_allows_gitignore(ff: FileFilter):
    include, _ = ff.should_include(".gitignore", 100)
    assert include is True


def test_filter_allows_dockerignore(ff: FileFilter):
    include, _ = ff.should_include(".dockerignore", 100)
    assert include is True


def test_filter_allows_env_example(ff: FileFilter):
    include, _ = ff.should_include(".env.example", 100)
    assert include is True


def test_filter_allows_python_file(ff: FileFilter):
    include, _ = ff.should_include("src/app.py", 100)
    assert include is True


def test_filter_allows_typescript(ff: FileFilter):
    include, _ = ff.should_include("src/index.ts", 100)
    assert include is True


def test_filter_ignores_pyc(ff: FileFilter):
    include, _ = ff.should_include("app/__pycache__/main.cpython-311.pyc", 100)
    assert include is False


def test_filter_ignores_png(ff: FileFilter):
    include, _ = ff.should_include("assets/logo.png", 100)
    assert include is False


def test_filter_ignores_nested_node_modules(ff: FileFilter):
    include, reason = ff.should_include("ClairoAI(Frontend)/node_modules/@swc/helpers/x.js", 100)
    assert include is False
    assert reason == "ignored_directory:node_modules"


def test_filter_ignores_site_packages(ff: FileFilter):
    include, reason = ff.should_include("Frontend/.venv/Lib/site-packages/pkg/x.py", 100)
    assert include is False
    assert "ignored_directory" in reason


def test_filter_ignores_pycache(ff: FileFilter):
    include, reason = ff.should_include("Backend/__pycache__/main.cpython-314.pyc", 100)
    assert include is False
    assert reason == "ignored_directory:__pycache__"


def test_filter_allows_project_source_paths(ff: FileFilter):
    assert ff.should_include("src/components/App.tsx", 100)[0] is True
    assert ff.should_include("Frontend/src/main.tsx", 100)[0] is True


# ── PriorityHandler ───────────────────────────────────────────────

@pytest.fixture
def ph() -> PriorityHandler:
    return PriorityHandler(config.scanner)


def test_priority_main_py_is_high(ph: PriorityHandler):
    from app.models.file_schema import Priority
    assert ph.classify("main.py") == Priority.HIGH


def test_priority_src_dir_is_high(ph: PriorityHandler):
    from app.models.file_schema import Priority
    assert ph.classify("src/routes/users.py") == Priority.HIGH


def test_priority_utils_is_medium(ph: PriorityHandler):
    from app.models.file_schema import Priority
    assert ph.classify("utils/helpers.py") == Priority.MEDIUM


def test_priority_tests_dir_is_low(ph: PriorityHandler):
    from app.models.file_schema import Priority
    assert ph.classify("tests/test_main.py") == Priority.LOW


def test_priority_config_dir_is_low(ph: PriorityHandler):
    from app.models.file_schema import Priority
    assert ph.classify("config/settings.yaml") == Priority.LOW


def test_priority_unknown_dir_is_medium(ph: PriorityHandler):
    from app.models.file_schema import Priority
    assert ph.classify("random_folder/file.py") == Priority.MEDIUM


def test_priority_package_json_is_high(ph: PriorityHandler):
    from app.models.file_schema import Priority
    assert ph.classify("package.json") == Priority.HIGH


def test_priority_dockerfile_is_high(ph: PriorityHandler):
    from app.models.file_schema import Priority
    assert ph.classify("Dockerfile") == Priority.HIGH


# ── safe_utils — never-raise guarantees ──────────────────────────

def test_safe_decode_valid_utf8():
    result = safe_decode(b"hello world")
    assert result == "hello world"


def test_safe_decode_latin1_fallback():
    # bytes that are not valid UTF-8
    result = safe_decode(bytes([0x80, 0x81, 0x82]))
    assert result is not None  # latin-1 fallback


def test_safe_decode_empty_bytes():
    assert safe_decode(b"") == ""


def test_safe_decode_with_max_bytes():
    result = safe_decode(b"hello world", max_bytes=5)
    assert result == "hello"


def test_safe_decode_pure_garbage_never_raises():
    garbage = bytes(range(256)) * 10
    try:
        safe_decode(garbage)  # may return None or str
    except Exception as e:
        pytest.fail(f"safe_decode raised: {e}")


def test_safe_read_file_nonexistent_path():
    """Must return None, not raise."""
    result = safe_read_file("/nonexistent/path/to/file.py", 1024)
    assert result is None


def test_safe_read_file_actual_file(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("x = 1\n")
    result = safe_read_file(str(f), 1024)
    assert result == "x = 1\n"


def test_safe_read_file_respects_max_bytes(tmp_path):
    f = tmp_path / "large.py"
    f.write_text("a" * 1000)
    result = safe_read_file(str(f), 10)
    assert result == "a" * 10


def test_is_likely_binary_null_byte():
    assert is_likely_binary(b"hello\x00world") is True


def test_is_likely_binary_text():
    assert is_likely_binary(b"def hello():\n    return 42\n") is False


def test_is_likely_binary_empty():
    # Empty bytes: no null bytes, no non-text → not binary
    assert is_likely_binary(b"") is False


def test_normalize_path_backslashes():
    assert normalize_path("app\\core\\scanner.py") == "app/core/scanner.py"


def test_normalize_path_strips_leading_slash():
    assert normalize_path("/app/main.py") == "app/main.py"


def test_normalize_path_strips_dot_slash():
    assert normalize_path("./app/main.py") == "app/main.py"


def test_normalize_path_clean_path():
    assert normalize_path("app/main.py") == "app/main.py"


def test_clamp_within_bounds():
    assert clamp(50, 0, 100) == 50


def test_clamp_below_min():
    assert clamp(-5, 0, 100) == 0


def test_clamp_above_max():
    assert clamp(150, 0, 100) == 100


def test_safe_extension_py():
    assert safe_extension("app/main.py") == ".py"


def test_safe_extension_no_ext():
    assert safe_extension("Makefile") == ""


def test_safe_extension_uppercase():
    assert safe_extension("Image.PNG") == ".png"


# ── Content cap enforcement ───────────────────────────────────────

def test_content_cap_never_exceeded(tmp_path):
    """
    Scanner must never accumulate more than max_total_content_mb bytes.
    Use a 0 MB cap so that no content is stored, but file metadata still collected.
    """
    import dataclasses
    from app.config import ScannerConfig

    # 0 MB cap → 0 bytes; every file's content is skipped
    zero_cap_cfg = dataclasses.replace(config.scanner, max_total_content_mb=0)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(10):
            zf.writestr(f"file_{i}.py", "x = 1\n" * 100)
    buf.seek(0)

    zip_path = str(tmp_path / "large.zip")
    with open(zip_path, "wb") as fout:
        fout.write(buf.read())

    from app.core.scanner.scanner import Scanner
    scanner = Scanner(zero_cap_cfg)
    result = scanner.scan_zip(zip_path=zip_path, session_id="test-cap")

    # With 0-byte budget, no text content should be stored
    assert len(result.contents) == 0
    # File metadata (path, size, priority) must still be collected
    assert len(result.files) > 0
