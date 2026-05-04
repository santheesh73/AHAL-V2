from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.storage.serialization import sanitize_for_storage


class MongoDBStore:
    def __init__(self, uri: str, database: str, ttl_hours: int = 24, client=None) -> None:
        self._ttl_hours = ttl_hours
        self._client = client or self._create_client(uri)
        self._db = self._client[database]
        self._sessions = self._db["sessions"]
        self._results = self._db["results"]
        self._chat = self._db["chat_history"]
        self._repo_indexes = self._db["repo_indexes"]
        self._repo_history = self._db["repo_index_history"]
        self._prd_diffs = self._db["prd_diffs"]
        self._test_gaps = self._db["test_gaps"]
        self._onboarding = self._db["onboarding_reports"]
        self._pr_analysis = self._db["pr_analysis"]
        self._ensure_indexes()

    def _create_client(self, uri: str):
        try:
            from pymongo import MongoClient
        except Exception as exc:
            raise RuntimeError("MongoDB backend requires pymongo to be installed.") from exc
        return MongoClient(uri)

    def _ensure_indexes(self) -> None:
        for collection, fields in [
            (self._sessions, ["session_id", "created_at", "updated_at"]),
            (self._repo_indexes, ["index_id", "repo_url", "created_at", "updated_at"]),
            (self._repo_history, ["index_id", "created_at"]),
            (self._pr_analysis, ["created_at"]),
        ]:
            for field in fields:
                try:
                    collection.create_index(field)
                except Exception:
                    continue

    def create_session(self, session_id: str, payload: dict) -> None:
        document = sanitize_for_storage(dict(payload))
        document["session_id"] = session_id
        self._sessions.update_one({"session_id": session_id}, {"$set": document}, upsert=True)

    def get_session(self, session_id: str):
        return self._sessions.find_one({"session_id": session_id}) or None

    def update_session(self, session_id: str, payload: dict) -> None:
        self._sessions.update_one({"session_id": session_id}, {"$set": sanitize_for_storage(dict(payload))}, upsert=True)

    def set_result(self, session_id: str, result) -> None:
        payload = sanitize_for_storage(result)
        self._results.update_one({"session_id": session_id}, {"$set": {"session_id": session_id, "result": payload}}, upsert=True)

    def get_result(self, session_id: str):
        row = self._results.find_one({"session_id": session_id}) or {}
        return row.get("result")

    def append_chat_message(self, session_id: str, message: dict) -> None:
        self._chat.insert_one({"session_id": session_id, "message": sanitize_for_storage(dict(message)), "created_at": datetime.now(timezone.utc)})

    def get_chat_history(self, session_id: str):
        return [row.get("message", {}) for row in self._chat.find({"session_id": session_id})]

    def create_repo_index(self, index_id: str, payload: dict) -> None:
        document = sanitize_for_storage(dict(payload))
        document["index_id"] = index_id
        self._repo_indexes.update_one({"index_id": index_id}, {"$set": document}, upsert=True)

    def get_repo_index(self, index_id: str):
        return self._repo_indexes.find_one({"index_id": index_id}) or None

    def update_repo_index(self, index_id: str, payload: dict) -> None:
        self._repo_indexes.update_one({"index_id": index_id}, {"$set": sanitize_for_storage(dict(payload))}, upsert=True)
        history = sanitize_for_storage(dict(payload))
        history["index_id"] = index_id
        history["created_at"] = datetime.now(timezone.utc)
        self._repo_history.insert_one(history)

    def list_repo_index_history(self, index_id: str):
        return list(self._repo_history.find({"index_id": index_id}))

    def save_prd_diff(self, key: str, payload: dict) -> None:
        self._prd_diffs.update_one({"key": key}, {"$set": {"key": key, "payload": sanitize_for_storage(dict(payload))}}, upsert=True)

    def get_prd_diff(self, key: str):
        row = self._prd_diffs.find_one({"key": key}) or {}
        return row.get("payload")

    def save_test_gap_result(self, session_id: str, payload: dict) -> None:
        self._test_gaps.update_one({"session_id": session_id}, {"$set": {"session_id": session_id, "payload": sanitize_for_storage(dict(payload))}}, upsert=True)

    def save_onboarding_report(self, session_id: str, payload: dict) -> None:
        self._onboarding.update_one({"session_id": session_id}, {"$set": {"session_id": session_id, "payload": sanitize_for_storage(dict(payload))}}, upsert=True)

    def save_pr_analysis_result(self, key: str, payload: dict) -> None:
        self._pr_analysis.update_one({"key": key}, {"$set": {"key": key, "payload": sanitize_for_storage(dict(payload)), "created_at": datetime.now(timezone.utc)}}, upsert=True)

    def cleanup_expired_sessions(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._ttl_hours)
        try:
            self._sessions.delete_many({"created_at": {"$lt": cutoff.isoformat()}})
        except Exception:
            return None
