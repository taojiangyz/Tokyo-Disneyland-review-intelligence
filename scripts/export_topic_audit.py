"""Export a private, representative audit sample for topic-label QA."""

import argparse
import json
import random
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def select_audit_sample(
    labels: list[dict[str, Any]],
    size: int,
    seed: int = 42,
) -> list[dict[str, Any]]:
    if size > len(labels):
        raise ValueError("Audit size exceeds available labels")
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    def add(row: dict[str, Any]) -> None:
        review_id = str(row["review_id"])
        if review_id not in selected_ids and len(selected) < size:
            selected.append(row)
            selected_ids.add(review_id)

    # Review uncertain outputs first.
    for row in sorted(labels, key=lambda item: float(item["confidence"])):
        if float(row["confidence"]) < 0.8:
            add(row)

    # Include obvious rating/text-sentiment tensions for calibration.
    for row in labels:
        mismatch = (
            float(row["rating"]) <= 2 and row["sentiment"] == "positive"
        ) or (
            float(row["rating"]) >= 4 and row["sentiment"] == "negative"
        )
        if mismatch:
            add(row)

    # Fill round-robin across market and low/high rating segments.
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in labels:
        if str(row["review_id"]) in selected_ids:
            continue
        segment = "low" if float(row["rating"]) <= 3 else "high"
        groups.setdefault((str(row["region"]), segment), []).append(row)
    rng = random.Random(seed)
    for group in groups.values():
        rng.shuffle(group)
    keys = sorted(groups)
    while len(selected) < size and keys:
        remaining = []
        for key in keys:
            if groups[key] and len(selected) < size:
                add(groups[key].pop())
            if groups[key]:
                remaining.append(key)
        keys = remaining
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, default=Path("data/topic_labels.jsonl"))
    parser.add_argument("--reviews", type=Path, default=Path("data/disney_reviews_normalized.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/topic_audit_sample.jsonl"))
    parser.add_argument("--size", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    labels = load_jsonl(args.labels)
    reviews = {str(row["review_id"]): row for row in load_jsonl(args.reviews)}
    sample = select_audit_sample(labels, args.size, args.seed)
    output_rows = []
    for label in sample:
        review = reviews[str(label["review_id"])]
        output_rows.append(
            {
                "review_id": str(label["review_id"]),
                "text": review["text"],
                "region": label["region"],
                "rating": label["rating"],
                "review_date": label.get("review_date"),
                "ai_topics": label["topics"],
                "ai_sentiment": label["sentiment"],
                "ai_confidence": label["confidence"],
                "taxonomy_version": label["taxonomy_version"],
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output_rows),
        encoding="utf-8",
    )
    temporary.replace(args.output)
    print(f"Exported {len(output_rows)} private audit items to {args.output}")


if __name__ == "__main__":
    main()
