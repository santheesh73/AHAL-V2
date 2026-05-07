from app.intelligence.intelligence_engine import IntelligenceEngine
from app.intelligence.repository_type_classifier import RepositoryTypeClassifier
from tests.intelligence.conftest import make_scan_result


def _coding_interview_university_scan():
    return make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "translations/es/README.md", "extension": ".md"},
        ],
        contents={
            "README.md": (
                "# Coding Interview University\n\n"
                "This is my multi-month study plan for becoming a software engineer for a large company.\n\n"
                "The guide organizes interview preparation topics, resources, and learning progression.\n"
            ),
            "translations/es/README.md": "# Coding Interview University (ES)\n\nPlan de estudio traducido.\n",
        },
    )


def test_coding_interview_university_classified_as_curriculum():
    scan = _coding_interview_university_scan()
    intelligence = IntelligenceEngine().analyze(scan)

    result = RepositoryTypeClassifier().classify(scan_result=scan, intelligence_result=intelligence)

    assert result.repo_type == "curriculum"
    assert result.confidence == "high"
    joined = " ".join(result.reasoning).lower()
    assert "backend" not in joined
    assert "devops" not in joined

