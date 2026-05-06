from __future__ import annotations

from app.intelligence.canonical_presenter import CanonicalProjectPresenter
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.conftest import make_scan_result


def _contextbridge_scan():
    return make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "package.json", "extension": ".json"},
            {"path": "app/main.py", "extension": ".py"},
            {"path": "frontend/src/main.tsx", "extension": ".tsx"},
            {"path": ".env.example", "extension": ""},
        ],
        contents={
            "README.md": (
                "# ContextBridge AI\n\n"
                "AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.\n"
            ),
            "package.json": (
                '{"name":"contextbridge-ai","description":"AI-powered developer tool that transforms code changes into structured, '
                'queryable knowledge using Gemma models."}'
            ),
            "app/main.py": (
                'from fastapi import FastAPI\napp = FastAPI()\n'
                '@app.post("/analyze")\ndef analyze(): pass\n'
                '@app.post("/ask")\ndef ask(): pass\n'
                '@app.post("/context")\ndef context(): pass\n'
                '@app.get("/status/{task_id}")\ndef status(task_id: str): pass\n'
                '@app.get("/")\ndef root(): pass\n'
            ),
            "frontend/src/main.tsx": "export default function App() { return null }\n",
            ".env.example": "MONGODB_URL=mongodb://secret-host/db\n",
        },
    )


def test_explicit_developer_tool_overrides_cms():
    scan = _contextbridge_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("session-1", scan, intelligence)

    assert canonical.product_domain in {"developer intelligence tool", "code intelligence platform"}
    assert "content management" not in canonical.product_summary.lower()
    assert "cms" not in canonical.product_domain.lower()


def test_canonical_what_uses_explicit_developer_description():
    scan = _contextbridge_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("session-1", scan, intelligence)

    assert "ai-powered developer tool" in canonical.what.lower()
    assert "structured, queryable knowledge" in canonical.what.lower()
    assert "content management application" not in canonical.what.lower()


def test_canonical_what_exact_for_contextbridge():
    scan = _contextbridge_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("session-1", scan, intelligence)

    assert canonical.what == "ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models."


def test_mongodb_not_language():
    scan = _contextbridge_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("session-1", scan, intelligence)

    assert "MongoDB" in canonical.tech_stack.databases or "Mongodb" not in canonical.tech_stack.languages
    assert all(item != "MongoDB" for item in canonical.tech_stack.languages)


def test_api_deduplication():
    scan = make_scan_result(
        files=[{"path": "app/main.py", "extension": ".py"}],
        contents={
            "app/main.py": (
                'from fastapi import FastAPI\napp = FastAPI()\n'
                '@app.post("/analyze")\ndef analyze_one(): pass\n'
                '@app.post("/analyze")\ndef analyze_two(): pass\n'
                '@app.get("/status/{Task Id}")\ndef status_one(task_id: str): pass\n'
                '@app.get("/status/{task_id}")\ndef status_two(task_id: str): pass\n'
            )
        },
    )
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("session-1", scan, intelligence)

    api_keys = [f"{item.method} {item.path}" for item in canonical.api_surface]
    assert api_keys.count("POST /analyze") == 1
    assert api_keys.count("GET /status/{task_id}") == 1


def test_workflow_no_impossible_fastapi_step():
    scan = _contextbridge_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("session-1", scan, intelligence)

    rendered = " ".join(f"{item.title} {item.description}" for item in canonical.workflow).lower()
    assert "types/index.ts initializes fastapi" not in rendered


def test_no_secret_evidence_primary():
    scan = _contextbridge_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("session-1", scan, intelligence)

    labels = " ".join(item.label.lower() for item in canonical.evidence)
    assert ".env.example" not in labels
    assert "mongodb://" not in labels


def test_remaining_deduped():
    scan = _contextbridge_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("session-1", scan, intelligence)

    remaining = [item.title.lower() for item in canonical.remaining]
    assert remaining.count("ci/cd pipeline not detected.") <= 1


def test_no_duplicate_summary_paragraphs():
    scan = _contextbridge_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("session-1", scan, intelligence)

    paragraphs = [part.strip() for part in canonical.product_summary.split("\n\n") if part.strip()]
    assert len(paragraphs) == len(set(paragraphs))
