from app.docs.generators.setup_generator import SetupGenerator

def test_setup_notes_from_requirements(mock_scan_result):
    gen = SetupGenerator()
    res = gen.generate(mock_scan_result)
    assert "requirements.txt" in res.content
