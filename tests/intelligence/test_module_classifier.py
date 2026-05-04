"""Tests for ModuleClassifier."""

from app.intelligence.classifiers.module_classifier import ModuleClassifier
from tests.intelligence.conftest import empty_scan_result, make_scan_result, python_fastapi_scan


def test_routes_controllers_classified_as_api():
    scan = make_scan_result(files=[
        {"path": "api/routes.py"},
        {"path": "controllers/user_controller.py"},
    ])
    modules = ModuleClassifier().classify(scan)
    cats = {m.category for m in modules}
    assert "api" in cats


def test_components_pages_classified_as_ui():
    scan = make_scan_result(files=[
        {"path": "components/Header.tsx"},
        {"path": "pages/index.tsx"},
    ])
    modules = ModuleClassifier().classify(scan)
    cats = {m.category for m in modules}
    assert "ui" in cats


def test_models_classified_as_model():
    scan = make_scan_result(files=[
        {"path": "models/user.py"},
        {"path": "models/item.py"},
    ])
    modules = ModuleClassifier().classify(scan)
    assert any(m.category == "model" for m in modules)


def test_schemas_classified_as_schema():
    scan = make_scan_result(files=[
        {"path": "schemas/user_schema.py"},
    ])
    modules = ModuleClassifier().classify(scan)
    assert any(m.category == "schema" for m in modules)


def test_services_classified_as_service():
    scan = make_scan_result(files=[
        {"path": "services/auth_service.py"},
    ])
    modules = ModuleClassifier().classify(scan)
    assert any(m.category == "service" for m in modules)


def test_auth_classified():
    scan = make_scan_result(files=[
        {"path": "auth/jwt_handler.py"},
        {"path": "auth/middleware.py"},
    ])
    modules = ModuleClassifier().classify(scan)
    assert any(m.category == "auth" for m in modules)


def test_tests_classified_as_test():
    scan = make_scan_result(files=[
        {"path": "tests/test_main.py"},
        {"path": "tests/test_api.py"},
    ])
    modules = ModuleClassifier().classify(scan)
    assert any(m.category == "test" for m in modules)


def test_utils_classified_as_utility():
    scan = make_scan_result(files=[
        {"path": "utils/helpers.py"},
    ])
    modules = ModuleClassifier().classify(scan)
    assert any(m.category == "utility" for m in modules)


def test_empty_scan():
    assert ModuleClassifier().classify(empty_scan_result()) == []


def test_root_level_files_skipped():
    """Root-level files (no directory) should not form modules."""
    scan = make_scan_result(files=[
        {"path": "main.py"},
        {"path": "readme.md"},
    ])
    modules = ModuleClassifier().classify(scan)
    assert len(modules) == 0


def test_multiple_files_high_confidence():
    scan = make_scan_result(files=[
        {"path": "api/routes.py"},
        {"path": "api/middleware.py"},
        {"path": "api/auth.py"},
    ])
    modules = ModuleClassifier().classify(scan)
    api_mod = next(m for m in modules if m.category == "api")
    assert api_mod.confidence == "high"
