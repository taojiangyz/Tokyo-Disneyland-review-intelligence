import pytest

from scripts.evaluate_retrieval import query_metrics


def test_query_metrics_calculates_recall_and_reciprocal_rank() -> None:
    metrics = query_metrics(
        ranked_ids=["irrelevant", "high", "partial"],
        grades={"high": 2, "partial": 1, "missed": 1},
        k=3,
    )

    assert metrics["recall"] == pytest.approx(2 / 3)
    assert metrics["mrr"] == pytest.approx(1 / 2)
    assert 0 < metrics["ndcg"] < 1


def test_query_metrics_handles_no_relevant_labels() -> None:
    metrics = query_metrics(["one"], {"one": 0}, k=1)

    assert metrics == {"recall": 0.0, "mrr": 0.0, "ndcg": 0.0}
