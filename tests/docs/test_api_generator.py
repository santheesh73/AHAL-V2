from app.docs.generators.api_generator import APIGenerator

def test_api_generation_includes_diagnose(mock_intelligence_result):
    gen = APIGenerator()
    res = gen.generate(mock_intelligence_result)
    assert len(res) == 2
    paths = [a.path for a in res]
    assert "/diagnose" in paths
    assert "/search" in paths
