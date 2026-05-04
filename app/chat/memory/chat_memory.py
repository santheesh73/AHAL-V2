"""Lightweight in-memory chat history for Phase 4."""

from __future__ import annotations

import threading
import time

from app.chat.models import ChatMessage
from app.config import config
from app.storage import storage_backend


class ChatMemory:
    def __init__(self, max_messages_per_session: int | None = None, ttl_seconds: int | None = 3600) -> None:
        self._max_messages = max_messages_per_session if max_messages_per_session is not None else config.scanner.chat_memory_max_messages
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._sessions: dict[str, tuple[float, list[ChatMessage]]] = {}

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        if not config.scanner.chat_memory_enabled:
            return
        with self._lock:
            self._cleanup_locked()
            updated_at, messages = self._sessions.get(session_id, (time.monotonic(), []))
            messages = [*messages, message][-self._max_messages :]
            self._sessions[session_id] = (time.monotonic(), messages)
        storage_backend.append_chat_message(session_id, message.model_dump())

    def get_history(self, session_id: str) -> list[ChatMessage]:
        if not config.scanner.chat_memory_enabled:
            return []
        with self._lock:
            self._cleanup_locked()
            _updated_at, messages = self._sessions.get(session_id, (0.0, []))
            if messages:
                return list(messages)
        return [ChatMessage.model_validate(item) for item in (storage_backend.get_chat_history(session_id) or [])][-self._max_messages :]

    def _cleanup_locked(self) -> None:
        if not self._ttl_seconds:
            return
        now = time.monotonic()
        stale = [sid for sid, (updated_at, _messages) in self._sessions.items() if (now - updated_at) > self._ttl_seconds]
        for sid in stale:
            del self._sessions[sid]


chat_memory = ChatMemory()
