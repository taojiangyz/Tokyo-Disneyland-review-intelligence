import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

import requests

DEFAULT_CASES = Path("evals/regression_cases.jsonl")
DEFAULT_OUTPUT = Path("evals/results/latest.json")


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
    return cases


def evaluate_response(case: dict[str, Any], response: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    evidence = response.get("evidence", [])
    expected = case["expect"]
    count = len(evidence)
    if count < expected.get("min_evidence", 0):
        failures.append(f"evidence_count {count} below minimum")
    if count > expected.get("max_evidence", 10_000):
        failures.append(f"evidence_count {count} above maximum")

    allowed_regions = set(expected.get("allowed_regions", []))
    returned_regions = {item.get("region") for item in evidence}
    if allowed_regions and not returned_regions.issubset(allowed_regions):
        failures.append(f"unexpected regions: {sorted(returned_regions - allowed_regions)}")

    for item in evidence:
        rating = item.get("rating")
        review_date = item.get("review_date")
        if expected.get("min_rating") is not None and rating < expected["min_rating"]:
            failures.append(f"rating {rating} below filter")
        if expected.get("max_rating") is not None and rating > expected["max_rating"]:
            failures.append(f"rating {rating} above filter")
        if expected.get("date_from") and review_date < expected["date_from"]:
            failures.append(f"date {review_date} before filter")
        if expected.get("date_to") and review_date > expected["date_to"]:
            failures.append(f"date {review_date} after filter")

    generation = response.get("trace", {}).get("generation", {})
    expected_status = expected.get("generation_status")
    if expected_status and generation.get("status") != expected_status:
        failures.append(f"generation status is {generation.get('status')}")

    if generation.get("status") == "completed" and evidence:
        evidence_ids = {item["review_id"] for item in evidence}
        cited_ids = set(re.findall(r"\[([^\]]+)\]", response.get("answer", "")))
        if not cited_ids:
            failures.append("answer contains no review citations")
        if cited_ids - evidence_ids:
            failures.append("answer cites review IDs outside retrieved evidence")
    return sorted(set(failures))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Aladdin RAG regression suite")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case-id")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_cases(args.cases)
    if args.case_id:
        cases = [case for case in cases if case["id"] == args.case_id]
    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No matching regression cases")

    results = []
    for index, case in enumerate(cases, start=1):
        payload = {"query": case["question"], **case["payload"]}
        print(f"[{index}/{len(cases)}] {case['id']}", flush=True)
        try:
            api_response = requests.post(
                f"{args.base_url}/api/v1/analyze",
                json=payload,
                timeout=180,
            )
            api_response.raise_for_status()
            response = api_response.json()
            failures = evaluate_response(case, response)
            results.append({
                "id": case["id"],
                "category": case["category"],
                "passed": not failures,
                "failures": failures,
                "evidence_count": len(response.get("evidence", [])),
                "generation_status": response.get("trace", {}).get("generation", {}).get("status"),
                "timing_ms": response.get("trace", {}).get("timing_ms", {}),
            })
        except requests.RequestException as exc:
            results.append({"id": case["id"], "category": case["category"], "passed": False, "failures": [str(exc)]})

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "total": len(results),
        "passed": sum(item["passed"] for item in results),
        "failed": sum(not item["passed"] for item in results),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Passed: {report['passed']}/{report['total']}")
    print(f"Report: {args.output.resolve()}")
    raise SystemExit(1 if report["failed"] else 0)


if __name__ == "__main__":
    main()
