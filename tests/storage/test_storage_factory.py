from __future__ import annotations

import importlib
from dataclasses import replace

import app.config as config_module
from app.chat.memory.chat_memory import ChatMemory
from app.chat.models import ChatMessage
from app.indexing.repo_indexer import RepoIndexer
from app.models.file_schema import ScanStatus
from app.sessions.session_manager import SessionManager
from app.storage.factory import create_storage_backend
from app.storage.memory_store import MemorySessionStore
from tests.intelligence.conftest import python_fastapi_scan
from tests.storage.test_mongodb_store import FakeClient


class TrackingStore(MemorySessionStore):
    def __init__(self) -> None:
        super().__init__()
        self.calls = []

    def create_session(self, session_id: str, payload: dict) -> None:
        self.calls.append(("create_session", session_id))
        super().create_session(session_id, payload)

    def update_session(self, session_id: str, payload: dict) -> None:
        self.calls.append(("update_session", session_id))
        super().update_session(session_id, payload)

    def set_result(self, session_id: str, result) -> None:
        self.calls.append(("set_result", session_id))
        super().set_result(session_id, result)

    def append_chat_message(self, session_id: str, message: dict) -> None:
        self.calls.append(("append_chat_message", session_id))
        super().append_chat_message(session_id, message)

    def create_repo_index(self, index_id: str, payload: dict) -> None:
        self.calls.append(("create_repo_index", index_id))
        super().create_repo_index(index_id, payload)


def test_memory_backend_remains_default():
    backend = create_storage_backend(config_module.config)
    assert isinstance(backend, MemorySessionStore)


def test_session_and_result_persistence_calls_store(monkeypatch):
    store = TrackingStore()
    monkeypatch.setattr("app.sessions.session_manager.storage_backend", store)
    manager = SessionManager()
    sid = manager.create_session(session_type="repo", source_name="https://github.com/example/repo")
    scan = python_fastapi_scan()
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    manager.set_result(sid, scan)
    call_names = [name for name, _ in store.calls]
    assert "create_session" in call_names
    assert "set_result" in call_names


def test_chat_history_persistence_calls_store(monkeypatch):
    store = TrackingStore()
    chat_memory_module = importlib.import_module("app.chat.memory.chat_memory")
    monkeypatch.setattr(chat_memory_module, "storage_backend", store)
    memory = ChatMemory(max_messages_per_session=5, ttl_seconds=3600)
    memory.add_message("sid-1", ChatMessage(role="user", content="Hello"))
    assert any(name == "append_chat_message" for name, _ in store.calls)


def test_repo_index_persistence_calls_store(monkeypatch):
    store = TrackingStore()
    monkeypatch.setattr("app.indexing.repo_indexer.storage_backend", store)
    indexer = RepoIndexer()
    manager = SessionManager()
    sid = manager.create_session(session_type="repo", source_name="https://github.com/example/repo")
    info = manager.get_info(sid)
    scan = python_fastapi_scan()
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    manager.set_result(sid, scan)
    indexer.create_index(sid, info, scan)
    assert any(name == "create_repo_index" for name, _ in store.calls)


def test_sensitive_values_are_not_persisted(monkeypatch):
    store = TrackingStore()
    monkeypatch.setattr("app.sessions.session_manager.storage_backend", store)
    manager = SessionManager()
    sid = manager.create_session(session_type="repo", source_name="https://github.com/example/repo")
    manager.set_artifact(sid, "secret", {"gemini_api_key": "abc", "contents": {".env": "GEMINI_API_KEY=abc"}})
    persisted = store.get_session(sid)
    payload = str(persisted).lower()
    assert "gemini_api_key" not in payload
    assert ".env" not in payload


def test_mongodb_backend_can_be_created_with_fake_client():
    fake_config = replace(
        config_module.config,
        scanner=replace(config_module.config.scanner, storage_backend="mongodb"),
    )
    backend = create_storage_backend(fake_config, client=FakeClient())
    assert backend.__class__.__name__ == "MongoDBStore"
