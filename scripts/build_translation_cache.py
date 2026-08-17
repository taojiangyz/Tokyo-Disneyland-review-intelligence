import argparse
import csv
from pathlib import Path
import time

from app.services.translation_service import (
    DEFAULT_CACHE_PATH,
    contains_korean,
    load_cache,
    save_cache,
    translate_batch_to_chinese,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cache Korean review translations")
    parser.add_argument(
        "--candidates",
        type=Path,
        default=Path("evals/annotations/candidate_pool_15.csv"),
    )
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_PATH)
    parser.add_argument("--batch-size", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.candidates.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    unique = {
        row["review_id"]: row["text"]
        for row in rows
        if contains_korean(row["text"])
    }
    cache = load_cache(args.cache)
    pending = [
        {"review_id": review_id, "text": text}
        for review_id, text in unique.items()
        if review_id not in cache
    ]
    print(f"Korean reviews: {len(unique)}")
    print(f"Already cached: {len(unique) - len(pending)}")
    for start in range(0, len(pending), args.batch_size):
        batch = pending[start : start + args.batch_size]
        translations = None
        for attempt in range(1, 4):
            try:
                translations = translate_batch_to_chinese(batch)
                break
            except Exception as exc:
                if attempt == 3:
                    raise RuntimeError(
                        f"Translation batch failed after {attempt} attempts"
                    ) from exc
                print(f"Attempt {attempt} failed; retrying...", flush=True)
                time.sleep(2**attempt)
        assert translations is not None
        cache.update(translations)
        save_cache(cache, args.cache)
        print(f"Translated: {min(start + len(batch), len(pending))}/{len(pending)}")
    print(f"Cache: {args.cache.resolve()}")


if __name__ == "__main__":
    main()
