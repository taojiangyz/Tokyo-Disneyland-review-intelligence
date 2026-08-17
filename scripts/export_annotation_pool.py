import argparse
import csv
import json
from pathlib import Path

import requests

MODES = ("dense", "hybrid", "hybrid_rerank")


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pool retrieval candidates for human labeling")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--cases", type=Path, default=Path("evals/regression_cases.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("evals/annotations/relevance.csv"))
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_cases(args.cases)
    if args.limit:
        cases = cases[: args.limit]
    rows = []
    for case_index, case in enumerate(cases, start=1):
        pooled: dict[str, dict] = {}
        print(f"[{case_index}/{len(cases)}] {case['id']}", flush=True)
        for mode in MODES:
            payload = {
                "query": case["question"],
                "mode": mode,
                "top_k": args.top_k,
                **case["payload"],
            }
            payload["top_k"] = args.top_k
            payload["candidate_limit"] = 20
            response = requests.post(
                f"{args.base_url}/api/v1/retrieve", json=payload, timeout=180
            )
            response.raise_for_status()
            for rank, item in enumerate(response.json()["evidence"], start=1):
                entry = pooled.setdefault(
                    item["review_id"],
                    {
                        "query_id": case["id"],
                        "question": case["question"],
                        "review_id": item["review_id"],
                        "region": item.get("region"),
                        "rating": item.get("rating"),
                        "review_date": item.get("review_date"),
                        "text": item.get("text", ""),
                        "retrieved_by": [],
                        "best_rank": rank,
                        "relevance": "",
                        "notes": "",
                    },
                )
                entry["retrieved_by"].append(mode)
                entry["best_rank"] = min(entry["best_rank"], rank)
        for entry in pooled.values():
            entry["retrieved_by"] = ",".join(entry["retrieved_by"])
            rows.append(entry)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    with args.output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Candidates: {len(rows)}")
    print(f"Annotation file: {args.output.resolve()}")


if __name__ == "__main__":
    main()
