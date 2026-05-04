from app.chat.classifiers.question_classifier import QuestionClassifier
from app.chat.retrieval.context_retriever import ContextRetriever
from app.chat.retrieval.evidence_ranker import EvidenceRanker
from app.chat.retrieval.graph_context_selector import GraphContextSelector
from app.graph.graph_engine import KnowledgeGraphEngine
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.conftest import python_fastapi_scan


def _inputs():
    scan = python_fastapi_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    return scan, intelligence, graph


def test_architecture_context_retrieval():
    scan, intelligence, _graph = _inputs()
    classification = QuestionClassifier().classify("What is the architecture overview?")
    contexts = ContextRetriever().retrieve("What is the architecture overview?", classification, scan, intelligence)

    assert contexts
    assert any(item.category == "architecture" for item in contexts)
    assert any(item.evidence for item in contexts if item.category == "architecture")


def test_workflow_graph_context_selection():
    scan, intelligence, graph = _inputs()
    classification = QuestionClassifier().classify("Explain the request workflow")
    contexts = GraphContextSelector().select("Explain the request workflow", classification, graph)

    assert contexts
    assert any("workflow" in item.context_id for item in contexts)


def test_api_graph_context_selection():
    scan, intelligence, graph = _inputs()
    classification = QuestionClassifier().classify("Which API endpoints exist?")
    contexts = GraphContextSelector().select("Which API endpoints exist?", classification, graph)

    assert contexts
    assert any(item.source_type == "graph_node" and "api_endpoint" in item.content for item in contexts)


def test_database_graph_context_selection():
    scan, intelligence, graph = _inputs()
    classification = QuestionClassifier().classify("Which database is used?")
    contexts = GraphContextSelector().select("Which database is used?", classification, graph)

    assert contexts
    assert any("uses_database" in item.content or "database" in item.content.lower() for item in contexts)


def test_evidence_ranking_deterministic():
    scan, intelligence, graph = _inputs()
    classifier = QuestionClassifier()
    classification = classifier.classify("Which API endpoint handles users?")
    contexts = [
        *ContextRetriever().retrieve("Which API endpoint handles users?", classification, scan, intelligence),
        *GraphContextSelector().select("Which API endpoint handles users?", classification, graph),
    ]
    ranked_one = EvidenceRanker().rank("Which API endpoint handles users?", classification, contexts)
    ranked_two = EvidenceRanker().rank("Which API endpoint handles users?", classification, contexts)

    assert [item.context_id for item in ranked_one] == [item.context_id for item in ranked_two]
