import json

import pytest

from scripts.build_topic_labels import completed_ids, parse_json_response, validate_labels


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
