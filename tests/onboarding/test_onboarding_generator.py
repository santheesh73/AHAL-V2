from __future__ import annotations

from unittest.mock import patch

from app.models.file_schema import ScanStatus
from app.onboarding import OnboardingGenerator
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import make_scan_result


def _onboarding_scan():
    return make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "app/main.py", "extension": ".py"},
            {"path": "app/api/routes.py", "extension": ".py"},
            {"path": "app/services/auth_service.py", "extension": ".py"},
            {"path": "app/models/user.py", "extension": ".py"},
            {"path": "app/workers/sync_pipeline.py", "extension": ".py"},
            {"path": "frontend/src/main.tsx", "extension": ".tsx"},
            {"path": "frontend/src/routes/dashboard.tsx", "extension": ".tsx"},
            {"path": "docker-compose.yml", "extension": ".yml"},
            {"path": "Dockerfile", "extension": ""},
            {"path": "tests/test_routes.py", "extension": ".py"},
            {"path": "node_modules/ignored.js", "extension": ".js"},
        ],
        contents={
            "README.md": "# AHAL Demo\n\nRepository intelligence backend with frontend dashboard.\n",
            "app/main.py": 'from fastapi import FastAPI\nfrom app.api.routes import router\napp = FastAPI()\napp.include_router(router)\n@app.get("/health")\ndef health():\n    return {"ok": True}\n',
            "app/api/routes.py": 'from fastapi import APIRouter\nrouter = APIRouter()\n@router.get("/users")\ndef list_users():\n    return []\n@router.post("/users")\ndef create_user():\n    return {"ok": True}\n',
            "app/services/auth_service.py": 'def validate_session(token: str) -> bool:\n    return bool(token)\n',
            "app/models/user.py": 'from pydantic import BaseModel\nclass User(BaseModel):\n    id: str\n    email: str\n',
            "app/workers/sync_pipeline.py": 'def sync_repo():\n    return "done"\n',
            "frontend/src/main.tsx": 'import ReactDOM from "react-dom/client";\nimport Dashboard from "./routes/dashboard";\nReactDOM.createRoot(document.getElementById("root")!).render(<Dashboard />);\n',
            "frontend/src/routes/dashboard.tsx": 'export default function Dashboard() { return <div>Dashboard</div>; }\n',
            "docker-compose.yml": "services:\n  api:\n    build: .\n",
            "Dockerfile": 'FROM python:3.11\nCMD ["uvicorn", "app.main:app"]\n',
            "tests/test_routes.py": 'def test_users_route():\n    assert True\n',
            "node_modules/ignored.js": "console.log('ignore');\n",
        },
    )


def _completed_session(session_type: str):
    sid = session_manager.create_session(session_type=session_type, source_name="demo")
    scan = _onboarding_scan()
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    return sid, scan


def test_generates_report_for_completed_folder_and_repo_sessions():
    generator = OnboardingGenerator()
    for session_type in ("folder", "repo"):
        sid, scan = _completed_session(session_type)
        report = generator.generate(session_id=sid, scan_result=scan)
        assert report.session_id == sid
        assert report.reading_order
        assert report.time_budget_minutes == 30


def test_reading_order_starts_with_readme_when_available():
    sid, scan = _completed_session("repo")
    report = OnboardingGenerator().generate(session_id=sid, scan_result=scan)
    assert report.reading_order[0].files_to_read[0] == "README.md"


def test_entry_points_and_api_routes_are_included():
    sid, scan = _completed_session("repo")
    report = OnboardingGenerator().generate(session_id=sid, scan_result=scan)
    assert any("app/main.py" in item for item in report.key_entry_points)
    assert any("/users" in item for item in report.important_apis)


def test_backend_audience_emphasizes_apis_services_and_database():
    sid, scan = _completed_session("repo")
    report = OnboardingGenerator().generate(session_id=sid, scan_result=scan, audience="backend")
    joined = " ".join(step.title for step in report.reading_order).lower()
    critical = " ".join(report.critical_modules).lower()
    assert "api" in joined
    assert "service" in joined or "service" in critical
    assert "database" in joined or "schema" in joined or "model" in critical


def test_frontend_audience_emphasizes_ui_and_api_contract():
    sid, scan = _completed_session("repo")
    report = OnboardingGenerator().generate(session_id=sid, scan_result=scan, audience="frontend")
    assert any("frontend/src/main.tsx" in item for item in report.key_entry_points)
    assert "contract" in report.summary.lower()
    assert any("/users" in item for item in report.important_apis)


def test_qa_audience_emphasizes_workflows_and_test_gaps():
    sid, scan = _completed_session("repo")
    report = OnboardingGenerator().generate(session_id=sid, scan_result=scan, audience="qa")
    text = " ".join(report.gotchas + report.safe_first_tasks + report.main_workflows).lower()
    assert "test" in text
    assert "workflow" in " ".join(report.reading_order[5].title.lower() for _ in [0]) or report.main_workflows


def test_devops_audience_emphasizes_docker_config_and_health():
    sid, scan = _completed_session("repo")
    report = OnboardingGenerator().generate(session_id=sid, scan_result=scan, audience="devops")
    all_files = " ".join(",".join(step.files_to_read) for step in report.reading_order).lower()
    assert "docker-compose.yml" in all_files or "dockerfile" in all_files
    assert any("/health" in item for item in report.important_apis)


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_no_gemini_required_no_raw_repr_and_no_ignored_paths(mock_generate):
    sid, scan = _completed_session("repo")
    report = OnboardingGenerator().generate(session_id=sid, scan_result=scan)
    payload = str(report.model_dump()).lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
    assert "node_modules" not in payload
    mock_generate.assert_not_called()
