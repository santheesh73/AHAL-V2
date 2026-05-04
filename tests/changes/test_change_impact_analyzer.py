from __future__ import annotations

from app.changes.change_impact_analyzer import ChangeImpactAnalyzer
from app.changes.models import ChangeAnalysisRequest, ChangedFileInput
from tests.intelligence.conftest import python_fastapi_scan
from app.intelligence.intelligence_engine import IntelligenceEngine


def _analyze_diff(diff_text: str, session_aware: bool = False):
    analyzer = ChangeImpactAnalyzer()
    request = ChangeAnalysisRequest(diff_text=diff_text, source_type="diff")
    if session_aware:
        scan = python_fastapi_scan()
        intelligence = IntelligenceEngine().analyze(scan_result=scan, session_id="sid", include_llm_explanation=False)
        return analyzer.analyze(request, scan_result=scan, intelligence_result=intelligence)
    return analyzer.analyze(request)


def test_api_route_change_detected():
    result = _analyze_diff(
        """diff --git a/app/api/routes.py b/app/api/routes.py
--- a/app/api/routes.py
+++ b/app/api/routes.py
@@
+@router.post("/users")
+async def create_user():
+    return {}
"""
    )
    assert result.changed_files[0].change_type == "api"
    assert "POST /users" in result.changed_files[0].affected_apis


def test_database_model_change_becomes_medium_or_high_risk():
    result = ChangeImpactAnalyzer().analyze(
        ChangeAnalysisRequest(
            source_type="files",
            changed_files=[ChangedFileInput(path="app/models/user.py", after="class User(BaseModel):\n    id: int", status="modified")],
        )
    )
    assert result.changed_files[0].risk_level in {"medium", "high"}


def test_auth_security_change_becomes_high_risk():
    result = ChangeImpactAnalyzer().analyze(
        ChangeAnalysisRequest(
            source_type="files",
            changed_files=[ChangedFileInput(path="app/services/auth.py", after="def authorize():\n    pass", status="modified")],
        )
    )
    assert result.changed_files[0].risk_level == "high"


def test_docs_only_change_becomes_low_risk():
    result = ChangeImpactAnalyzer().analyze(
        ChangeAnalysisRequest(
            source_type="files",
            changed_files=[ChangedFileInput(path="README.md", after="Updated docs", status="modified")],
        )
    )
    assert result.changed_files[0].risk_level == "low"


def test_suggested_tests_generated_for_api_change():
    result = _analyze_diff(
        """diff --git a/app/api/routes.py b/app/api/routes.py
--- a/app/api/routes.py
+++ b/app/api/routes.py
@@
+@router.get("/orders")
"""
    )
    joined = " ".join(result.suggested_tests).lower()
    assert "endpoint integration tests" in joined


def test_suggested_tests_generated_for_model_schema_change():
    result = ChangeImpactAnalyzer().analyze(
        ChangeAnalysisRequest(
            source_type="files",
            changed_files=[ChangedFileInput(path="app/schema/order_schema.py", after="class OrderSchema: pass", status="modified")],
        )
    )
    joined = " ".join(result.suggested_tests).lower()
    assert "database migration or persistence tests" in joined or "serialization" in joined


def test_standalone_diff_works_without_session_id():
    result = _analyze_diff(
        """diff --git a/app/services/reporting.py b/app/services/reporting.py
--- a/app/services/reporting.py
+++ b/app/services/reporting.py
@@
+def build_report():
+    return {}
"""
    )
    assert result.session_id is None
    assert result.changed_files


def test_with_session_id_maps_to_known_modules_if_available():
    result = _analyze_diff(
        """diff --git a/app/api/routes.py b/app/api/routes.py
--- a/app/api/routes.py
+++ b/app/api/routes.py
@@
+@router.get("/users")
""",
        session_aware=True,
    )
    modules = " ".join(result.changed_files[0].affected_modules).lower()
    assert "api" in modules


def test_no_raw_repr_leakage():
    result = ChangeImpactAnalyzer().analyze(
        ChangeAnalysisRequest(
            source_type="files",
            changed_files=[ChangedFileInput(path="README.md", after="docs", status="modified")],
        )
    )
    payload = result.model_dump_json().lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
