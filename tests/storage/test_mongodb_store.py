from __future__ import annotations

from app.storage.mongodb_store import MongoDBStore


class FakeCollection:
    def __init__(self):
        self.rows = []
        self.indexes = []

    def create_index(self, field):
        self.indexes.append(field)

    def update_one(self, query, update, upsert=False):
        row = self.find_one(query)
        payload = dict(update.get("$set", {}))
        if row is None:
            payload.update(query)
            self.rows.append(payload)
        else:
            row.update(payload)

    def find_one(self, query):
        for row in self.rows:
            if all(row.get(key) == value for key, value in query.items()):
                return row
        return None

    def insert_one(self, payload):
        self.rows.append(dict(payload))

    def find(self, query):
        return [row for row in self.rows if all(row.get(key) == value for key, value in query.items())]

    def delete_many(self, query):
        return None


class FakeDatabase(dict):
    def __getitem__(self, item):
        if item not in self:
            self[item] = FakeCollection()
        return dict.__getitem__(self, item)


class FakeClient(dict):
    def __getitem__(self, item):
        if item not in self:
            self[item] = FakeDatabase()
        return dict.__getitem__(self, item)


def test_mongodb_store_session_result_and_chat_persistence():
    store = MongoDBStore("mongodb://localhost:27017", "ahal_ai", client=FakeClient())
    store.create_session("sid-1", {"created_at": "now", "gemini_api_key": "secret"})
    store.update_session("sid-1", {"status": "completed"})
    store.set_result("sid-1", {"contents": {".env": "API_KEY=123", "app/main.py": "print('ok')"}})
    store.append_chat_message("sid-1", {"role": "user", "content": "hello"})
    session = store.get_session("sid-1")
    result = store.get_result("sid-1")
    history = store.get_chat_history("sid-1")
    assert session["status"] == "completed"
    assert "gemini_api_key" not in str(session).lower()
    assert ".env" not in str(result).lower()
    assert history[0]["content"] == "hello"


def test_mongodb_store_repo_index_and_reports_persistence():
    store = MongoDBStore("mongodb://localhost:27017", "ahal_ai", client=FakeClient())
    store.create_repo_index("idx-1", {"repo_url": "https://github.com/example/repo"})
    store.update_repo_index("idx-1", {"status": "ready"})
    store.save_prd_diff("a:b", {"summary": "diff"})
    store.save_test_gap_result("sid-1", {"summary": "gap"})
    store.save_onboarding_report("sid-1", {"summary": "onboard"})
    store.save_pr_analysis_result("pr-1", {"summary": "pr"})
    assert store.get_repo_index("idx-1")["status"] == "ready"
    assert store.get_prd_diff("a:b")["summary"] == "diff"
