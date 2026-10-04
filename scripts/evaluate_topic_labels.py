"""Evaluate AI-assisted topic labels against private human audit decisions."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    verified = [row for row in rows if row.get("status") == "verified"]
    skipped = len(rows) - len(verified)
    tp = fp = fn = exact = sentiment_correct = 0
    by_topic: dict[str, Counter] = defaultdict(Counter)
    for row in verified:
        predicted = set(row["ai_topics"])
        expected = set(row["human_topics"])
        exact += predicted == expected
        sentiment_correct += row["ai_sentiment"] == row["human_sentiment"]
        tp += len(predicted & expected)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
        for topic in predicted | expected:
            by_topic[topic]["tp"] += int(topic in predicted and topic in expected)
            by_topic[topic]["fp"] += int(topic in predicted and topic not in expected)
            by_topic[topic]["fn"] += int(topic in expected and topic not in predicted)
            by_topic[topic]["support"] += int(topic in expected)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    per_topic = {}
    for topic, counts in sorted(by_topic.items()):
        topic_precision = counts["tp"] / (counts["tp"] + counts["fp"]) if counts["tp"] + counts["fp"] else None
        topic_recall = counts["tp"] / (counts["tp"] + counts["fn"]) if counts["tp"] + counts["fn"] else None
        per_topic[topic] = {
            "support": counts["support"],
            "precision": round(topic_precision, 4) if topic_precision is not None else None,
            "recall": round(topic_recall, 4) if topic_recall is not None else None,
        }
    denominator = len(verified)
    return {
        "reviewed": len(rows),
        "verified": denominator,
        "skipped": skipped,
        "topic_exact_match": round(exact / denominator, 4) if denominator else None,
        "topic_micro_precision": round(precision, 4),
        "topic_micro_recall": round(recall, 4),
        "topic_micro_f1": round(f1, 4),
        "sentiment_accuracy": round(sentiment_correct / denominator, 4) if denominator else None,
        "per_topic": per_topic,
        "sampling_note": "Audit sample intentionally oversamples low-confidence and rating-sentiment tension cases.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/topic_audit_reviews.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("evals/results/topic_label_audit.json"))
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = evaluate(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
