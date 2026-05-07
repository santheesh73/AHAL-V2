from app.intelligence.canonical_presenter import CanonicalProjectPresenter
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.test_repository_type_classifier import _coding_interview_university_scan


def test_curriculum_summary_not_devops():
    scan = _coding_interview_university_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("curriculum-session", scan, intelligence)

    assert canonical.repo_type == "curriculum"
    assert canonical.project_type == "curriculum"
    assert canonical.product_domain == "software engineering education"
    assert "study plan" in canonical.product_summary.lower()
    assert "devops" not in canonical.product_summary.lower()
    assert "automation tool" not in canonical.product_summary.lower()
    assert "backend" not in canonical.product_summary.lower()
    assert "api layer" not in canonical.product_summary.lower()


def test_curriculum_completed_items_are_relevant():
    scan = _coding_interview_university_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    canonical = CanonicalProjectPresenter().build("curriculum-session", scan, intelligence)

    titles = [item.title for item in canonical.completed]

    assert "Study Plan Documentation" in titles
    assert "Learning Roadmap" in titles
    assert "Backend API Layer" not in titles

