import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean

import requests

MODES = ("dense", "hybrid", "hybrid_rerank")


def load_cases(path: Path) -> dict[str, dict]:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return {case["id"]: case for case in cases}


def load_labels(path: Path) -> dict[str, dict[str, int]]:
    labels: dict[str, dict[str, int]] = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row["relevance"].strip() not in {"0", "1", "2"}:
                continue
            labels.setdefault(row["query_id"], {})[row["review_id"]] = int(row["relevance"])
    return labels


def query_metrics(ranked_ids: list[str], grades: dict[str, int], k: int) -> dict[str, float]:
    relevant = {review_id for review_id, grade in grades.items() if grade > 0}
    hits = [review_id for review_id in ranked_ids[:k] if review_id in relevant]
    recall = len(set(hits)) / len(relevant) if relevant else 0.0
    reciprocal_rank = next((1 / rank for rank, review_id in enumerate(ranked_ids[:k], 1) if review_id in relevant), 0.0)
    dcg = sum((2 ** grades.get(review_id, 0) - 1) / math.log2(rank + 1) for rank, review_id in enumerate(ranked_ids[:k], 1))
    ideal = sorted(grades.values(), reverse=True)[:k]
    idcg = sum((2 ** grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal, 1))
    return {"recall": recall, "mrr": reciprocal_rank, "ndcg": dcg / idcg if idcg else 0.0}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate labeled retrieval results")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--cases", type=Path, default=Path("evals/regression_cases.jsonl"))
    parser.add_argument("--labels", type=Path, default=Path("evals/annotations/relevance_labels.csv"))
    parser.add_argument("--output", type=Path, default=Path("evals/results/retrieval_metrics.json"))
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_cases(args.cases)
    labels = load_labels(args.labels)
    labeled_queries = sorted(set(cases) & set(labels))
    if not labeled_queries:
        raise SystemExit("No relevance labels found. Assign 0, 1, or 2 in the annotation CSV.")

    report = {"labeled_queries": len(labeled_queries), "top_k": args.top_k, "modes": {}}
    for mode in MODES:
        per_query = []
        for query_id in labeled_queries:
            case = cases[query_id]
            payload = {"query": case["question"], "mode": mode, "top_k": args.top_k, **case["payload"]}
            payload["top_k"] = args.top_k
            response = requests.post(f"{args.base_url}/api/v1/retrieve", json=payload, timeout=180)
            response.raise_for_status()
            data = response.json()
            ranked_ids = [item["review_id"] for item in data["evidence"]]
            metrics = query_metrics(ranked_ids, labels[query_id], args.top_k)
            metrics["query_id"] = query_id
            metrics["latency_ms"] = data["trace"]["timing_ms"]["retrieval_pipeline"]
            per_query.append(metrics)
        report["modes"][mode] = {
            "recall_at_k": mean(item["recall"] for item in per_query),
            "mrr_at_k": mean(item["mrr"] for item in per_query),
            "ndcg_at_k": mean(item["ndcg"] for item in per_query),
            "mean_latency_ms": mean(item["latency_ms"] for item in per_query),
            "queries": per_query,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["modes"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output.resolve()}")


if __name__ == "__main__":
    main()
