import json

import pytest

from src.prepare_data import load_and_normalize, write_jsonl


def source_record(review_id: str = "review-1") -> dict:
    return {
        "review_id": review_id,
        "text": "A useful review",
        "title": "Visit",
        "languageType": "zh_cn",
        "rating": 4,
        "review_date": "2025-01-02",
        "source": "test",
        "park": "Tokyo Disneyland",
        "poi_id": "park-1",
        "raw_locale": "zh_CN",
    }


def write_source(path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def test_pipeline_normalizes_and_writes_atomically(tmp_path) -> None:
    source = tmp_path / "source.jsonl"
    output = tmp_path / "normalized.jsonl"
    write_source(source, [source_record()])

    records = load_and_normalize(source)
    write_jsonl(records, output)

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["region"] == "CN"
    assert saved["lang_tag"] == "zh-CN"
    assert saved["rating"] == 4
    assert not output.with_suffix(".jsonl.tmp").exists()


def test_pipeline_rejects_duplicate_review_ids(tmp_path) -> None:
    source = tmp_path / "source.jsonl"
    write_source(source, [source_record(), source_record()])

    with pytest.raises(ValueError, match="Duplicate review_id"):
        load_and_normalize(source)


def test_pipeline_rejects_invalid_iso_date(tmp_path) -> None:
    source = tmp_path / "source.jsonl"
    record = source_record()
    record["review_date"] = "not-a-date"
    write_source(source, [record])

    with pytest.raises(ValueError):
        load_and_normalize(source)
