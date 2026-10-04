from collections import Counter
from statistics import mean
from time import perf_counter
from typing import Any
from math import ceil

from app.services.rag_service import COLLECTION_NAME, build_filter


class ReviewTools:
    def __init__(self, rag_service, topic_service=None) -> None:
        self.rag_service = rag_service
        self.topic_service = topic_service

    def topic_distribution(self, filters: dict[str, Any]) -> dict[str, Any]:
        if self.topic_service is None:
            return {"available": False, "review_count": 0, "topics": []}
        return self.topic_service.distribution(filters)

    def compare_topics_by_market(self, filters: dict[str, Any]) -> dict[str, Any]:
        if self.topic_service is None:
            return {"available": False, "markets": {}}
        return self.topic_service.compare_markets(filters)

    def search_reviews(
        self,
        query: str,
        filters: dict[str, Any],
        limit: int = 5,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        ranked, trace = self.rag_service.retrieve_for_evaluation(
            query=query,
            mode="dense",
            regions=filters.get("regions"),
            min_rating=filters.get("min_rating"),
            max_rating=filters.get("max_rating"),
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            limit=limit,
        )
        evidence = []
        for point, score in ranked:
            payload = point.payload or {}
            evidence.append(
                {
                    "review_id": str(payload.get("review_id", "")),
                    "region": payload.get("region"),
                    "rating": payload.get("rating"),
                    "review_date": payload.get("review_date"),
                    "text": str(payload.get("text", "")),
                    "score": float(score),
                }
            )
        return evidence, trace

    def review_statistics(
        self,
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        started = perf_counter()
        query_filter = build_filter(
            regions=filters.get("regions"),
            min_rating=filters.get("min_rating"),
            max_rating=filters.get("max_rating"),
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
        )
        records = []
        offset = None
        while True:
            batch, offset = self.rag_service.client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=query_filter,
                limit=256,
                offset=offset,
                with_payload=["region", "rating", "review_date"],
                with_vectors=False,
            )
            records.extend(batch)
            if offset is None:
                break

        regions: Counter[str] = Counter()
        ratings: Counter[str] = Counter()
        months: Counter[str] = Counter()
        numeric_ratings: list[float] = []
        market_ratings: dict[str, list[float]] = {}
        for record in records:
            payload = record.payload or {}
            if payload.get("region"):
                regions[str(payload["region"])] += 1
            if payload.get("rating") is not None:
                rating = float(payload["rating"])
                numeric_ratings.append(rating)
                ratings[str(int(rating))] += 1
                if payload.get("region"):
                    market_ratings.setdefault(
                        str(payload["region"]), []
                    ).append(rating)
            if payload.get("review_date"):
                months[str(payload["review_date"])[:7]] += 1

        return {
            "review_count": len(records),
            "average_rating": (
                round(mean(numeric_ratings), 3) if numeric_ratings else None
            ),
            "by_market": dict(sorted(regions.items())),
            "average_rating_by_market": {
                market: round(mean(values), 3)
                for market, values in sorted(market_ratings.items())
            },
            "by_rating": dict(sorted(ratings.items())),
            "by_month": dict(sorted(months.items())),
            "calculation": "deterministic",
            "duration_ms": round((perf_counter() - started) * 1000, 2),
        }

    def search_reviews_by_market(
        self,
        query: str,
        filters: dict[str, Any],
        limit: int = 6,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        markets = list(filters.get("regions") or ["CN", "HK", "KR"])
        per_market = ceil(limit / len(markets))
        grouped: dict[str, list[dict[str, Any]]] = {}
        traces: dict[str, Any] = {}
        for market in markets:
            market_filters = {**filters, "regions": [market]}
            grouped[market], traces[market] = self.search_reviews(
                query,
                market_filters,
                per_market,
            )

        interleaved = []
        for index in range(per_market):
            for market in markets:
                if index < len(grouped[market]):
                    interleaved.append(grouped[market][index])
        return interleaved[:limit], {
            "retrieval_mode": "dense_by_market",
            "markets": markets,
            "per_market": traces,
        }


def verify_evidence(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    review_ids = [item.get("review_id") for item in evidence]
    valid_ids = [item for item in review_ids if item]
    return {
        "passed": bool(evidence) and len(valid_ids) == len(evidence),
        "evidence_count": len(evidence),
        "unique_review_ids": len(set(valid_ids)),
        "issues": [] if evidence else ["No evidence matched the request"],
    }
