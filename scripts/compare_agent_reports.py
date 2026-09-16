from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median
from typing import Any


def load_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("mode") != "live":
        raise ValueError(f"{path} is not a live Agent evaluation report")
    return report


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return round(ordered[index], 2)


def summarize(report: dict[str, Any], label: str) -> dict[str, Any]:
    live_rows = [item.get("live", {}) for item in report["results"]]
    latencies = [
        float(row["total_ms"])
        for row in live_rows
        if row.get("total_ms") is not None
    ]
    token_totals = [
        int((row.get("usage") or {}).get("total_tokens", 0))
        for row in live_rows
    ]
    providers = sorted({row.get("provider") for row in live_rows if row.get("provider")})
    models = sorted({row.get("model") for row in live_rows if row.get("model")})
    return {
        "label": label,
        "provider": ", ".join(providers) or "unknown",
        "model": ", ".join(models) or "unknown",
        "passed": report["passed"],
        "total": report["total"],
        "pass_rate": round(report["passed"] / report["total"], 4),
        "mean_latency_ms": round(mean(latencies), 2) if latencies else None,
        "p50_latency_ms": round(median(latencies), 2) if latencies else None,
        "p95_latency_ms": percentile(latencies, 0.95),
        "total_tokens": sum(token_totals),
    }


def compare_reports(paths: list[Path], labels: list[str]) -> dict[str, Any]:
    reports = [load_report(path) for path in paths]
    case_sets = [{item["id"] for item in report["results"]} for report in reports]
    if any(case_set != case_sets[0] for case_set in case_sets[1:]):
        raise ValueError("Reports do not contain the same evaluation case IDs")
    return {
        "case_count": len(case_sets[0]),
        "providers": [
            summarize(report, label) for report, label in zip(reports, labels)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare live Agent evaluation reports across LLM providers"
    )
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--labels", nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    labels = args.labels or [path.stem for path in args.reports]
    if len(labels) != len(args.reports):
        raise SystemExit("--labels must match the number of reports")
    comparison = compare_reports(args.reports, labels)
    rendered = json.dumps(comparison, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
