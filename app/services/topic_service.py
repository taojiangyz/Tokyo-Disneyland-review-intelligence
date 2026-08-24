import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


class TopicService:
    """Deterministic analytics over private, derived topic labels."""

    def __init__(self, labels_path: str | Path | None = None) -> None:
        self.labels_path = Path(
            labels_path
            or os.getenv("ALADDIN_TOPIC_LABELS", "data/topic_labels.jsonl")
        )
        self.records = self._load_records()
        self.available = bool(self.records)

    def _load_records(self) -> list[dict[str, Any]]:
        if not self.labels_path.exists():
            return []
        records = []
        with self.labels_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid topic label JSON at line {line_number}"
                    ) from exc
        return records

    @staticmethod
    def _matches(record: dict[str, Any], filters: dict[str, Any]) -> bool:
        regions = filters.get("regions") or []
        if regions and record.get("region") not in regions:
            return False
        rating = record.get("rating")
        if filters.get("min_rating") is not None and (
            rating is None or float(rating) < float(filters["min_rating"])
        ):
            return False
        if filters.get("max_rating") is not None and (
            rating is None or float(rating) > float(filters["max_rating"])
        ):
            return False
        date = record.get("review_date")
        if filters.get("date_from") and (
            not date or str(date) < str(filters["date_from"])
        ):
            return False
        if filters.get("date_to") and (
            not date or str(date) > str(filters["date_to"])
        ):
            return False
        return True

    def distribution(self, filters: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            return {"available": False, "review_count": 0, "topics": []}
        matched = [r for r in self.records if self._matches(r, filters)]
        topic_counts: Counter[str] = Counter()
        sentiments: Counter[str] = Counter()
        confidence_total = 0.0
        for record in matched:
            topic_counts.update(set(record.get("topics") or []))
            if record.get("sentiment"):
                sentiments[str(record["sentiment"])] += 1
            confidence_total += float(record.get("confidence") or 0)
        denominator = len(matched)
        topics = [
            {
                "topic": topic,
                "count": count,
                "review_share": round(count / denominator, 4),
            }
            for topic, count in topic_counts.most_common()
        ]
        return {
            "available": True,
            "review_count": denominator,
            "topics": topics,
            "sentiments": dict(sorted(sentiments.items())),
            "average_confidence": (
                round(confidence_total / denominator, 4) if denominator else None
            ),
            "calculation": "deterministic_over_ai_assisted_labels",
        }

    def compare_markets(self, filters: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            return {"available": False, "markets": {}}
        matched = [r for r in self.records if self._matches(r, filters)]
        by_market: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in matched:
            if record.get("region"):
                by_market[str(record["region"])].append(record)
        markets = {}
        for market, records in sorted(by_market.items()):
            counts: Counter[str] = Counter()
            for record in records:
                counts.update(set(record.get("topics") or []))
            markets[market] = {
                "review_count": len(records),
                "topics": [
                    {
                        "topic": topic,
                        "count": count,
                        "review_share": round(count / len(records), 4),
                    }
                    for topic, count in counts.most_common()
                ],
            }
        return {
            "available": True,
            "markets": markets,
            "calculation": "deterministic_over_ai_assisted_labels",
        }
