import json

from app.services.topic_service import TopicService


def write_labels(path):
    rows = [
        {"review_id": "r1", "region": "KR", "rating": 2, "review_date": "2025-01-01", "topics": ["waiting_time", "crowding"], "sentiment": "negative", "confidence": 0.9},
        {"review_id": "r2", "region": "KR", "rating": 5, "review_date": "2025-02-01", "topics": ["attractions"], "sentiment": "positive", "confidence": 0.8},
        {"review_id": "r3", "region": "HK", "rating": 2, "review_date": "2024-01-01", "topics": ["waiting_time"], "sentiment": "negative", "confidence": 1.0},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_distribution_filters_and_counts_multilabel_reviews(tmp_path):
    path = tmp_path / "labels.jsonl"
    write_labels(path)
    result = TopicService(path).distribution({"regions": ["KR"], "max_rating": 3})
    assert result["review_count"] == 1
    assert {item["topic"] for item in result["topics"]} == {"waiting_time", "crowding"}
    assert all(item["review_share"] == 1.0 for item in result["topics"])
    assert result["sentiments"] == {"negative": 1}


def test_market_comparison_uses_each_market_as_denominator(tmp_path):
    path = tmp_path / "labels.jsonl"
    write_labels(path)
    result = TopicService(path).compare_markets({})
    assert result["markets"]["KR"]["review_count"] == 2
    waiting = next(x for x in result["markets"]["KR"]["topics"] if x["topic"] == "waiting_time")
    assert waiting["review_share"] == 0.5
    assert result["markets"]["HK"]["topics"][0]["review_share"] == 1.0


def test_missing_labels_degrades_gracefully(tmp_path):
    service = TopicService(tmp_path / "missing.jsonl")
    assert not service.available
    assert not service.distribution({})["available"]
