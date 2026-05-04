from app.docs.generators.risk_generator import RiskGenerator
from unittest.mock import MagicMock

def test_risk_generation(mock_scan_result, mock_intelligence_result):
    gen = RiskGenerator()
    # It has auth and db, but no deployment config and no test
    risks = gen.generate(mock_scan_result, mock_intelligence_result, [])
    titles = [r.title for r in risks]
    assert "No tests detected" in titles
    assert "No deployment config detected" in titles
