from app.docs.generators.module_generator import ModuleGenerator

def test_module_generation(mock_intelligence_result):
    gen = ModuleGenerator()
    res = gen.generate(mock_intelligence_result)
    assert len(res) == 1
    assert res[0].name == "AuthModule"
    assert "app/auth.py" in res[0].files
