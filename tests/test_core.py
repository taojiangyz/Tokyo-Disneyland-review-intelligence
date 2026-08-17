from datetime import date

import pytest
from pydantic import ValidationError
from qdrant_client import models

from app.schemas import AnalyzeRequest, RetrieveRequest
from app.services.rag_service import build_filter, to_sparse_vector


def test_request_combines_legacy_and_multi_market_filters() -> None:
    request = AnalyzeRequest(
        query="Compare queue complaints",
        region="HK",
        regions=["CN", "KR"],
    )

    assert request.selected_regions() == ["CN", "KR", "HK"]


@pytest.mark.parametrize(
    "payload",
    [
        {"regions": ["US"]},
        {"min_rating": 5, "max_rating": 1},
        {
            "date_from": date(2025, 2, 1),
            "date_to": date(2025, 1, 1),
        },
    ],
)
def test_request_rejects_invalid_filters(payload: dict) -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest(query="Valid question", **payload)


def test_build_filter_supports_multiple_markets() -> None:
    query_filter = build_filter(
        regions=["CN", "KR"],
        min_rating=1,
        max_rating=3,
        date_from="2024-01-01",
        date_to="2025-12-31",
    )

    assert query_filter is not None
    assert len(query_filter.must) == 3
    market_condition = query_filter.must[0]
    assert isinstance(market_condition, models.FieldCondition)
    assert market_condition.match.any == ["CN", "KR"]


def test_sparse_vector_is_sorted_by_token_id() -> None:
    vector = to_sparse_vector({"9": 0.4, "2": 0.8})

    assert vector.indices == [2, 9]
    assert vector.values == [0.8, 0.4]


def test_retrieve_request_accepts_supported_modes() -> None:
    for mode in ("dense", "hybrid", "hybrid_rerank"):
        request = RetrieveRequest(query="Queue complaints", mode=mode)
        assert request.mode == mode


def test_retrieve_request_rejects_unknown_mode() -> None:
    with pytest.raises(ValidationError):
        RetrieveRequest(query="Queue complaints", mode="unknown")
