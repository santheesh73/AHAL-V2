from app.chat.classifiers.question_classifier import QuestionClassifier


def test_question_classifier_categories():
    classifier = QuestionClassifier()

    assert classifier.classify("Give me the architecture overview").category == "architecture"
    assert classifier.classify("Explain the request lifecycle").category == "workflow"
    assert classifier.classify("Which API endpoint handles users?").category == "api"
    assert classifier.classify("What database is used?").category == "database"
    assert classifier.classify("Which module owns auth service?").category == "module"
    assert classifier.classify("Which file defines this?").category == "file"
    assert classifier.classify("Which dependency adds FastAPI?").category == "dependency"
    assert classifier.classify("How does auth login security work?").category == "security"
    assert classifier.classify("What tests exist and coverage?").category == "testing"
    assert classifier.classify("Tell me about this codebase").category == "general"
