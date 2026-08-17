import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

DATA_PATH = Path("data/tdr_land_reviews_clean.jsonl")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL file and report malformed lines clearly."""
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path.resolve()}")

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

            if not isinstance(record, dict):
                raise TypeError(
                    f"Line {line_number} is not a JSON object."
                )

            records.append(record)

    return records


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def main() -> None:
    records = load_jsonl(DATA_PATH)

    print("=" * 60)
    print("DISNEY REVIEW DATA INSPECTION")
    print("=" * 60)
    print(f"Data file: {DATA_PATH.resolve()}")
    print(f"Total records: {len(records)}")

    if not records:
        print("The dataset is empty.")
        return

    all_fields: Counter[str] = Counter()
    regions: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    ratings: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    parks: Counter[str] = Counter()

    review_ids: list[str] = []
    empty_text_ids: list[str] = []
    missing_id_count = 0
    text_lengths: list[int] = []

    for record in records:
        all_fields.update(record.keys())

        review_id = normalize_text(record.get("review_id"))
        text = normalize_text(record.get("text"))

        if review_id:
            review_ids.append(review_id)
        else:
            missing_id_count += 1

        if text:
            text_lengths.append(len(text))
        else:
            empty_text_ids.append(review_id or "<missing review_id>")

        regions[normalize_text(record.get("region")) or "<missing>"] += 1
        languages[normalize_text(record.get("lang_tag")) or "<missing>"] += 1
        ratings[normalize_text(record.get("rating")) or "<missing>"] += 1
        sources[normalize_text(record.get("source")) or "<missing>"] += 1
        parks[normalize_text(record.get("park")) or "<missing>"] += 1

    duplicate_ids = [
        review_id
        for review_id, count in Counter(review_ids).items()
        if count > 1
    ]

    print("\nFields:")
    for field, count in sorted(all_fields.items()):
        print(f"- {field}: present in {count}/{len(records)} records")

    print("\nData-quality checks:")
    print(f"- Missing review_id: {missing_id_count}")
    print(f"- Duplicate review_id values: {len(duplicate_ids)}")
    print(f"- Empty text records: {len(empty_text_ids)}")

    if duplicate_ids:
        print(f"- Duplicate ID examples: {duplicate_ids[:10]}")

    if empty_text_ids:
        print(f"- Empty-text ID examples: {empty_text_ids[:10]}")

    print("\nRegion distribution:")
    for key, value in regions.most_common():
        print(f"- {key}: {value}")

    print("\nLanguage distribution:")
    for key, value in languages.most_common():
        print(f"- {key}: {value}")

    print("\nRating distribution:")
    for key, value in sorted(ratings.items()):
        print(f"- {key}: {value}")

    print("\nSource distribution:")
    for key, value in sources.most_common():
        print(f"- {key}: {value}")

    print("\nPark distribution:")
    for key, value in parks.most_common():
        print(f"- {key}: {value}")

    if text_lengths:
        sorted_lengths = sorted(text_lengths)

        print("\nText length in characters:")
        print(f"- Minimum: {min(sorted_lengths)}")
        print(f"- Median: {statistics.median(sorted_lengths):.1f}")
        print(f"- Mean: {statistics.mean(sorted_lengths):.1f}")
        print(f"- 95th percentile: {sorted_lengths[int(len(sorted_lengths) * 0.95) - 1]}")
        print(f"- Maximum: {max(sorted_lengths)}")

    print("\nFirst record preview:")
    preview = records[0].copy()
    preview_text = normalize_text(preview.get("text"))

    if len(preview_text) > 300:
        preview["text"] = preview_text[:300] + "..."

    print(json.dumps(preview, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
