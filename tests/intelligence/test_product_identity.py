from app.intelligence.intelligence_engine import IntelligenceEngine
from app.intelligence.product_identity import ProductIdentityResolver
from tests.intelligence.conftest import make_scan_result


def test_generic_folder_name_frontend_is_not_used_as_product_name():
    scan = make_scan_result(
        files=[{"path": "frontend/main.py", "extension": ".py"}],
        contents={"frontend/main.py": "from fastapi import FastAPI\napp = FastAPI()\n"},
    )
    identity = ProductIdentityResolver().resolve(scan_result=scan, intelligence_result=IntelligenceEngine().analyze(scan))
    assert identity.project_name is None


def test_generic_folder_name_backend_is_not_used_as_product_name():
    scan = make_scan_result(
        files=[{"path": "backend/app.py", "extension": ".py"}],
        contents={"backend/app.py": "from fastapi import FastAPI\napp = FastAPI()\n"},
    )
    identity = ProductIdentityResolver().resolve(scan_result=scan, intelligence_result=IntelligenceEngine().analyze(scan))
    assert identity.project_name is None


def test_readme_title_is_used_as_product_name():
    scan = make_scan_result(
        files=[{"path": "README.md", "extension": ".md"}],
        contents={"README.md": "# FactShield\n\nClaim verification service.\n"},
    )
    identity = ProductIdentityResolver().resolve(scan_result=scan, intelligence_result=IntelligenceEngine().analyze(scan))
    assert identity.project_name == "Factshield"


def test_package_description_is_used_when_readme_absent():
    scan = make_scan_result(
        files=[{"path": "package.json", "extension": ".json"}],
        contents={"package.json": '{"name":"claim-guard","description":"AI claim verification backend"}'},
    )
    identity = ProductIdentityResolver().resolve(scan_result=scan, intelligence_result=IntelligenceEngine().analyze(scan))
    assert "claim verification backend" in identity.purpose_summary.lower()


def test_unknown_project_uses_conservative_fallback():
    scan = make_scan_result(
        files=[{"path": "main.py", "extension": ".py"}, {"path": "requirements.txt", "extension": ".txt"}],
        contents={"main.py": "from fastapi import FastAPI\napp = FastAPI()\n", "requirements.txt": "fastapi\nmotor\n"},
    )
    identity = ProductIdentityResolver().resolve(scan_result=scan, intelligence_result=IntelligenceEngine().analyze(scan))
    assert "exact product purpose is not fully specified" in identity.purpose_summary.lower()
