import json

import pytest

from scripts.build_topic_labels import (
    balanced_sample,
    completed_ids,
    parse_json_response,
    validate_labels,
)


def test_parse_fenced_json_and_validate_labels():
    parsed = parse_json_response('```json\n{"labels":[{"review_id":"r1","topics":["waiting_time"],"sentiment":"negative","confidence":0.9}]}\n```')
    labels = validate_labels(parsed, {"r1"}, {"waiting_time"}, {"negative"})
    assert labels[0]["confidence"] == 0.9


def test_validation_rejects_unknown_topic():
    payload = {"labels": [{"review_id": "r1", "topics": ["invented"], "sentiment": "negative", "confidence": 0.5}]}
    with pytest.raises(ValueError, match="Unknown topics"):
        validate_labels(payload, {"r1"}, {"waiting_time"}, {"negative"})


def test_completed_ids_supports_resume(tmp_path):
    path = tmp_path / "labels.jsonl"
    path.write_text(json.dumps({"review_id": "r1"}) + "\n", encoding="utf-8")
    assert completed_ids(path) == {"r1"}


def test_taxonomy_separates_food_price_from_overall_value():
    taxonomy = json.loads(
        open("config/topic_taxonomy.json", encoding="utf-8").read()
    )
    topics = {item["id"]: item for item in taxonomy["topics"]}
    assert "food" in topics["food_price"]["description"].lower()
    assert "overall" in topics["value_for_money"]["description"].lower()
    assert taxonomy["version"] == "1.1"


def test_balanced_sample_covers_market_and_rating_segments():
    rows = [
        {"review_id": f"{region}-{rating}-{number}", "region": region, "rating": rating}
        for region in ["CN", "HK", "KR"]
        for rating in [2, 5]
        for number in range(4)
    ]
    sample = balanced_sample(rows, 12, seed=7)
    segments = {(row["region"], "low" if row["rating"] <= 3 else "high") for row in sample}
    assert len(sample) == 12
    assert len(segments) == 6
    assert sample == balanced_sample(rows, 12, seed=7)
