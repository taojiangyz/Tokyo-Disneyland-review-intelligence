import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
from typing import Any

DEFAULT_INPUT_PATH = Path("data/tdr_land_reviews_clean.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/disney_reviews_normalized.jsonl")
REGION_MAP = {"zh_cn": "CN", "zh_hk": "HK", "ko": "KR"}
LANG_TAG_MAP = {"zh_cn": "zh-CN", "zh_hk": "zh-HK", "ko": "ko-KR"}


def normalize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalize_rating(value: Any) -> int:
    rating = int(float(value))
    if not 1 <= rating <= 5:
        raise ValueError(f"Invalid rating: {value}")
    return rating


def normalize_date(value: Any) -> str:
    normalized = normalize_text(value)
    date.fromisoformat(normalized)
    return normalized


def load_and_normalize(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path.resolve()}")
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            try:
                source = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
            locale = normalize_text(source.get("languageType"))
            if locale not in REGION_MAP:
                raise ValueError(f"Unknown languageType on line {line_number}: {locale}")
            review_id = normalize_text(source.get("review_id"))
            text = normalize_text(source.get("text"))
            if not review_id:
                raise ValueError(f"Missing review_id on line {line_number}")
            if review_id in seen_ids:
                raise ValueError(f"Duplicate review_id on line {line_number}: {review_id}")
            if not text:
                raise ValueError(f"Missing text on line {line_number}")
            seen_ids.add(review_id)
            records.append({
                "review_id": review_id,
                "text": text,
                "title": normalize_text(source.get("title")),
                "region": REGION_MAP[locale],
                "lang_tag": LANG_TAG_MAP[locale],
                "rating": normalize_rating(source.get("rating")),
                "review_date": normalize_date(source.get("review_date")),
                "source": normalize_text(source.get("source")),
                "park": normalize_text(source.get("park")),
                "poi_id": normalize_text(source.get("poi_id")),
                "raw_locale": normalize_text(source.get("raw_locale")),
            })
    if not records:
        raise ValueError("Input dataset contains no valid records")
    return records


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    temporary_path.replace(path)


def print_report(records: list[dict[str, Any]], output_path: Path | None) -> None:
    regions = Counter(record["region"] for record in records)
    dates = [record["review_date"] for record in records]
    ratings = [record["rating"] for record in records]
    print(f"Validated records: {len(records)}")
    print(f"Regions: {dict(sorted(regions.items()))}")
    print(f"Rating range: {min(ratings)}-{max(ratings)}")
    print(f"Date range: {min(dates)} to {max(dates)}")
    if output_path:
        print(f"Output: {output_path.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and normalize review data")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_and_normalize(args.input)
    if not args.validate_only:
        write_jsonl(records, args.output)
    print_report(records, None if args.validate_only else args.output)


if __name__ == "__main__":
    main()
