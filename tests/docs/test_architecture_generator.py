from app.docs.generators.architecture_generator import ArchitectureGenerator

def test_architecture_from_intelligence(mock_intelligence_result):
    gen = ArchitectureGenerator()
    res = gen.generate(mock_intelligence_result)
    assert "Architecture Type: Backend" in res.content
    assert "Primary Frameworks: FastAPI" in res.content
    assert res.confidence == "high"
