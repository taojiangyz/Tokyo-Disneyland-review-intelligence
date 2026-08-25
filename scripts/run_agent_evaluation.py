from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any

import requests
from dotenv import load_dotenv

from app.agent.executor import resolve_agent_filters
from app.agent.planner import build_plan
from app.agent.router import route_task


DEFAULT_CASES = Path("evals/agent_cases.jsonl")
DEFAULT_OUTPUT = Path("evals/results/agent_latest.json")


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
    return cases


def structural_result(case: dict[str, Any]) -> dict[str, Any]:
    expected = case["expect"]
    task = route_task(case["question"])
    payload = case.get("payload", {})
    initial_filters = {
        "regions": payload.get("regions", []),
        "min_rating": payload.get("min_rating"),
        "max_rating": payload.get("max_rating"),
        "date_from": payload.get("date_from"),
        "date_to": payload.get("date_to"),
    }
    filters = resolve_agent_filters(case["question"], task, initial_filters)
    tools = [step.tool for step in build_plan(task)]
    failures: list[str] = []
    if task != expected["task"]:
        failures.append(f"task={task}, expected={expected['task']}")
    for key in ("regions", "max_rating", "date_from", "date_to"):
        if key in expected and filters.get(key) != expected[key]:
            failures.append(f"{key}={filters.get(key)!r}, expected={expected[key]!r}")
    if tools != expected["tools"]:
        failures.append(f"tools={tools!r}, expected={expected['tools']!r}")
    return {
        "id": case["id"],
        "category": case["category"],
        "passed": not failures,
        "failures": failures,
        "task": task,
        "filters": filters,
        "tools": tools,
    }


def live_failures(case: dict[str, Any], response: dict[str, Any]) -> list[str]:
    expected = case["expect"]
    failures: list[str] = []
    if response.get("task") != expected["task"]:
        failures.append(f"response task={response.get('task')}")

    filters = response.get("filters", {})
    for key in ("regions", "max_rating", "date_from", "date_to"):
        if key in expected and filters.get(key) != expected[key]:
            failures.append(f"response {key}={filters.get(key)!r}")

    tools = [step.get("tool") for step in response.get("steps", [])]
    if tools != expected["tools"]:
        failures.append(f"response tools={tools!r}")

    evidence = response.get("evidence", [])
    if len(evidence) > expected.get("max_evidence", 10_000):
        failures.append(f"evidence_count={len(evidence)} above maximum")
    expected_regions = set(expected.get("regions", []))
    returned_regions = {item.get("region") for item in evidence}
    if expected_regions and not returned_regions.issubset(expected_regions):
        failures.append(f"unexpected evidence regions={returned_regions - expected_regions}")
    max_rating = expected.get("max_rating")
    if max_rating is not None and any(
        item.get("rating") is not None and item["rating"] > max_rating
        for item in evidence
    ):
        failures.append("evidence violates max_rating")

    analytics = response.get("analytics", {})
    status = analytics.get("generation", {}).get("status")
    if expected.get("generation_status") and status != expected["generation_status"]:
        failures.append(f"generation_status={status}")
    if expected.get("requires_deterministic_statistics"):
        calculation = analytics.get("statistics", {}).get("calculation")
        if calculation != "deterministic":
            failures.append(f"statistics calculation={calculation}")

    if status == "completed" and evidence:
        evidence_ids = {item.get("review_id") for item in evidence}
        cited_ids = set(re.findall(r"\[([^\]]+)\]", response.get("answer", "")))
        if not cited_ids:
            failures.append("answer contains no evidence citations")
        elif not cited_ids.issubset(evidence_ids):
            failures.append("answer cites IDs outside returned evidence")
    return sorted(set(failures))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Aladdin Agent behavior")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--live", action="store_true", help="Call the live Agent API")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case-id")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    cases = load_cases(args.cases)
    if args.case_id:
        cases = [case for case in cases if case["id"] == args.case_id]
    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No matching Agent evaluation cases")

    results: list[dict[str, Any]] = []
    headers = {}
    api_token = os.getenv("ALADDIN_API_TOKEN", "").strip()
    if api_token:
        headers["X-Aladdin-Token"] = api_token

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']}", flush=True)
        result = structural_result(case)
        if args.live and result["passed"]:
            payload = {"query": case["question"], "evidence_limit": 5, **case["payload"]}
            try:
                api_response = requests.post(
                    f"{args.base_url}/api/v1/agent/analyze",
                    json=payload,
                    headers=headers,
                    timeout=180,
                )
                api_response.raise_for_status()
                response = api_response.json()
                failures = live_failures(case, response)
                result["failures"].extend(failures)
                result["passed"] = not result["failures"]
                result["live"] = {
                    "evidence_count": len(response.get("evidence", [])),
                    "generation_status": response.get("analytics", {})
                    .get("generation", {})
                    .get("status"),
                    "total_ms": response.get("trace", {}).get("total_ms"),
                }
            except requests.RequestException as exc:
                result["passed"] = False
                result["failures"].append(str(exc))
        results.append(result)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if args.live else "structural",
        "total": len(results),
        "passed": sum(item["passed"] for item in results),
        "failed": sum(not item["passed"] for item in results),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Passed: {report['passed']}/{report['total']}")
    print(f"Report: {args.output.resolve()}")
    raise SystemExit(1 if report["failed"] else 0)


if __name__ == "__main__":
    main()
