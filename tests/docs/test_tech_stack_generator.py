from app.docs.generators.tech_stack_generator import TechStackGenerator

def test_tech_stack_section(mock_intelligence_result):
    gen = TechStackGenerator()
    res = gen.generate(mock_intelligence_result)
    assert "FastAPI" in res.content
    assert "PostgreSQL" in res.content
