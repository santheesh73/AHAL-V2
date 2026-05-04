from __future__ import annotations

from app.indexing.models import DeltaScanRequest, DeltaChangedFile
from app.indexing.repo_indexer import RepoIndexer
from app.sessions.models import utc_now_iso
from tests.intelligence.conftest import make_scan_result, python_fastapi_scan


def _info(session_type="repo", source_name="https://github.com/example/repo"):
    class Info:
        pass
    info = Info()
    info.session_type = session_type
    info.source_name = source_name
    return info


def test_fingerprints_are_deterministic():
    scan = make_scan_result(contents={"b.py": "print('b')", "a.py": "print('a')"})
    indexer = RepoIndexer()
    first = indexer.create_index("s1", _info(), scan)
    second = indexer.create_index("s2", _info(), scan)
    assert [(item.path, item.hash) for item in first.file_fingerprints] == [(item.path, item.hash) for item in second.file_fingerprints]


def test_ignored_paths_excluded():
    scan = make_scan_result(contents={"node_modules/x.js": "x", "app.py": "print('ok')"})
    index = RepoIndexer().create_index("s1", _info(), scan)
    assert all("node_modules" not in item.path for item in index.file_fingerprints)


def test_env_secrets_excluded():
    scan = make_scan_result(contents={".env": "SECRET=1", "secrets.env": "TOKEN=1", "app.py": "print('ok')"})
    index = RepoIndexer().create_index("s1", _info(), scan)
    paths = [item.path for item in index.file_fingerprints]
    assert ".env" not in paths
    assert "secrets.env" not in paths


def test_added_file_detected():
    indexer = RepoIndexer()
    index = indexer.create_index("s1", _info(), make_scan_result(contents={"app.py": "print('ok')"}))
    delta = indexer.run_delta(DeltaScanRequest(index_id=index.index_id, changed_files=[DeltaChangedFile(path="new.py", content="print('new')", status="added")]))
    assert "new.py" in delta.added_files


def test_modified_file_detected():
    indexer = RepoIndexer()
    index = indexer.create_index("s1", _info(), make_scan_result(contents={"app.py": "print('ok')"}))
    delta = indexer.run_delta(DeltaScanRequest(index_id=index.index_id, changed_files=[DeltaChangedFile(path="app.py", content="print('changed')", status="modified")]))
    assert "app.py" in delta.modified_files


def test_deleted_file_detected():
    indexer = RepoIndexer()
    index = indexer.create_index("s1", _info(), make_scan_result(contents={"app.py": "print('ok')"}))
    delta = indexer.run_delta(DeltaScanRequest(index_id=index.index_id, changed_files=[DeltaChangedFile(path="app.py", status="deleted")]))
    assert "app.py" in delta.deleted_files


def test_unchanged_files_counted():
    indexer = RepoIndexer()
    index = indexer.create_index("s1", _info(), make_scan_result(contents={"app.py": "print('ok')", "b.py": "print('b')"}))
    delta = indexer.run_delta(DeltaScanRequest(index_id=index.index_id, changed_files=[DeltaChangedFile(path="app.py", content="print('changed')", status="modified")]))
    assert delta.unchanged_files_count == 1


def test_force_full_rescan_works():
    indexer = RepoIndexer()
    index = indexer.create_index("s1", _info(), make_scan_result(contents={"app.py": "print('ok')"}))
    delta = indexer.run_delta(DeltaScanRequest(index_id=index.index_id, force_full_rescan=True))
    assert delta.rescan_scope == "full"
