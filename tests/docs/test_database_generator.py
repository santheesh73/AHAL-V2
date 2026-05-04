from app.docs.generators.database_generator import DatabaseGenerator
from unittest.mock import MagicMock

def test_database_absence_message():
    gen = DatabaseGenerator()
    intel = MagicMock()
    intel.databases = []
    res = gen.generate(intel)
    assert "No database/storage layer detected" in res.content
