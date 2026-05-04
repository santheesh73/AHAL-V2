from __future__ import annotations

from app.storage.serialization import sanitize_for_storage


class MemorySessionStore:
    def __init__(self) -> None:
        self._sessions = {}
        self._results = {}
        self._chat = {}
        self._repo_indexes = {}
        self._repo_history = {}
        self._prd_diffs = {}
        self._test_gaps = {}
        self._onboarding = {}
        self._pr_analysis = {}

    def create_session(self, session_id: str, payload: dict) -> None:
        self._sessions[session_id] = sanitize_for_storage(dict(payload))

    def get_session(self, session_id: str):
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, payload: dict) -> None:
        self._sessions.setdefault(session_id, {}).update(sanitize_for_storage(dict(payload)))

    def set_result(self, session_id: str, result) -> None:
        self._results[session_id] = sanitize_for_storage(result)

    def get_result(self, session_id: str):
        return self._results.get(session_id)

    def append_chat_message(self, session_id: str, message: dict) -> None:
        self._chat.setdefault(session_id, []).append(sanitize_for_storage(dict(message)))

    def get_chat_history(self, session_id: str):
        return list(self._chat.get(session_id, []))

    def create_repo_index(self, index_id: str, payload: dict) -> None:
        self._repo_indexes[index_id] = sanitize_for_storage(dict(payload))
        self._repo_history.setdefault(index_id, [])

    def get_repo_index(self, index_id: str):
        return self._repo_indexes.get(index_id)

    def update_repo_index(self, index_id: str, payload: dict) -> None:
        self._repo_indexes.setdefault(index_id, {}).update(sanitize_for_storage(dict(payload)))

    def list_repo_index_history(self, index_id: str):
        return list(self._repo_history.get(index_id, []))

    def save_prd_diff(self, key: str, payload: dict) -> None:
        self._prd_diffs[key] = sanitize_for_storage(dict(payload))

    def get_prd_diff(self, key: str):
        return self._prd_diffs.get(key)

    def save_test_gap_result(self, session_id: str, payload: dict) -> None:
        self._test_gaps[session_id] = sanitize_for_storage(dict(payload))

    def save_onboarding_report(self, session_id: str, payload: dict) -> None:
        self._onboarding[session_id] = sanitize_for_storage(dict(payload))

    def save_pr_analysis_result(self, key: str, payload: dict) -> None:
        self._pr_analysis[key] = sanitize_for_storage(dict(payload))

    def cleanup_expired_sessions(self) -> None:
        return None
