from app.db.models.evaluation import EvaluationCase
from app.services.evaluation import compute_metrics


def _case(**overrides) -> EvaluationCase:
    values = {
        "name": "Case",
        "question": "What is RAG?",
        "reference_answer": None,
        "required_facts": None,
        "expected_sources": None,
        "selected_document_ids": None,
    }
    values.update(overrides)

    case = EvaluationCase(**values)
    return case


def test_retrieval_metrics_with_expected_sources():
    case = _case(
        expected_sources=[
            {"document_id": "1", "page": 2},
            {"document_id": "2", "page": None},
        ]
    )
    actual_sources = [
        {"document_id": "1", "page": 2, "chunk_id": "1:0"},
        {"document_id": "3", "page": 1, "chunk_id": "3:0"},
    ]

    metrics = compute_metrics(case, "answer", actual_sources)

    assert metrics["expected_sources_count"] == 2
    assert metrics["retrieved_expected_sources"] == 1
    assert metrics["retrieval_hit_rate"] == 0.5
    assert metrics["source_recall"] == 0.5
    assert metrics["source_precision"] == 0.5
    assert metrics["unexpected_sources_count"] == 1


def test_page_mismatch_does_not_match():
    case = _case(
        expected_sources=[{"document_id": "1", "page": 2}]
    )
    actual_sources = [
        {"document_id": "1", "page": 3, "chunk_id": "1:0"}
    ]

    metrics = compute_metrics(case, "answer", actual_sources)

    assert metrics["retrieved_expected_sources"] == 0
    assert metrics["retrieval_hit_rate"] == 0.0


def test_expected_source_without_page_matches_any_page():
    case = _case(
        expected_sources=[{"document_id": "1"}]
    )
    actual_sources = [
        {"document_id": "1", "page": 7, "chunk_id": "1:0"}
    ]

    metrics = compute_metrics(case, "answer", actual_sources)

    assert metrics["retrieved_expected_sources"] == 1
    assert metrics["retrieval_hit_rate"] == 1.0


def test_fact_coverage_counts_covered_facts():
    case = _case(
        required_facts=[
            "Retrieval augmented generation",
            "Vector database stores embeddings",
            "Fact that is absent",
        ]
    )
    answer = (
        "RAG is retrieval augmented generation. A "
        "vector database stores embeddings."
    )

    metrics = compute_metrics(case, answer, [])

    assert metrics["required_facts_count"] == 3
    assert metrics["required_facts_covered"] == 2
    assert metrics["fact_coverage"] == 2 / 3


def test_fact_coverage_is_case_and_punctuation_insensitive():
    case = _case(required_facts=["The Document's Title!"])
    answer = "the document title is mentioned here"

    metrics = compute_metrics(case, answer, [])

    assert metrics["required_facts_covered"] == 1
    assert metrics["fact_coverage"] == 1.0


def test_no_ground_truth_produces_no_metrics():
    case = _case()

    metrics = compute_metrics(case, "answer", [])

    assert metrics == {}


def test_missing_expected_sources_do_not_create_hits():
    """Expected sources that were not retrieved lower
    the hit rate instead of producing false positives."""
    case = _case(
        expected_sources=[{"document_id": "1"}]
    )

    metrics = compute_metrics(case, "answer", [])

    assert metrics["retrieved_expected_sources"] == 0
    assert metrics["retrieval_hit_rate"] == 0.0
    assert "source_precision" not in metrics


def test_deleted_documents_produce_no_source_matches():
    """A deleted document cannot be retrieved anymore,
    so its expected source never matches."""
    case = _case(
        expected_sources=[
            {"document_id": "deleted-document"}
        ]
    )
    actual_sources = [
        {"document_id": "other-document", "page": 1}
    ]

    metrics = compute_metrics(case, "answer", actual_sources)

    assert metrics["retrieved_expected_sources"] == 0
    assert metrics["retrieval_hit_rate"] == 0.0
    assert metrics["unexpected_sources_count"] == 1
