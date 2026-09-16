from pathlib import Path

from scripts.run_agent_evaluation import (
    SMOKE_CASE_IDS,
    build_summary,
    classify_failure,
    live_failures,
    load_cases,
    structural_result,
)


CASES = Path("evals/agent_cases.jsonl")


def test_agent_evaluation_has_40_unique_cases_and_three_languages() -> None:
    cases = load_cases(CASES)
    assert len(cases) == 40
    assert len({case["id"] for case in cases}) == 40
    questions = "\n".join(case["question"] for case in cases)
    assert any("\u4e00" <= char <= "\u9fff" for char in questions)
    assert any("what" in case["question"].casefold() for case in cases)
    assert any("です" in case["question"] for case in cases)


def test_smoke_suite_covers_all_tasks_and_no_evidence() -> None:
    by_id = {case["id"]: case for case in load_cases(CASES)}
    smoke = [by_id[case_id] for case_id in SMOKE_CASE_IDS]
    assert len(smoke) == 5
    assert {case["expect"]["task"] for case in smoke} == {
        "evidence_qa",
        "root_cause_analysis",
        "market_comparison",
        "improvement_planning",
    }
    assert any(case["category"] == "no_evidence" for case in smoke)


def test_all_agent_structural_expectations_pass() -> None:
    failures = {
        case["id"]: structural_result(case)["failures"]
        for case in load_cases(CASES)
        if structural_result(case)["failures"]
    }
    assert failures == {}


def test_live_summary_reports_latency_tokens_and_root_causes() -> None:
    results = [
        {
            "id": "a",
            "category": "evidence_qa",
            "passed": True,
            "failures": [],
            "live": {
                "provider": "gemini",
                "model": "model-a",
                "total_ms": 100,
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                "step_timings_ms": {
                    "search_reviews": 100,
                    "grounded_generation": 600,
                },
            },
        },
        {
            "id": "b",
            "category": "evidence_qa",
            "passed": False,
            "failures": ["answer cites IDs outside returned evidence"],
            "live": {
                "provider": "gemini",
                "model": "model-a",
                "total_ms": 300,
                "usage": {"prompt_tokens": 20, "completion_tokens": 7, "total_tokens": 27},
                "step_timings_ms": {
                    "search_reviews": 300,
                    "grounded_generation": 1000,
                },
            },
        },
    ]
    summary = build_summary(results, live=True)
    assert summary["pass_rate"] == 0.5
    assert summary["latency_ms"] == {"mean": 200.0, "p50": 200.0, "p95": 300.0}
    assert summary["token_usage"]["total_tokens"] == 42
    assert summary["failed_cases_by_root_cause"]["prompt"] == 1
    assert summary["tool_latency_ms"]["search_reviews"] == {
        "calls": 2,
        "mean": 200.0,
        "p50": 200.0,
        "p95": 300.0,
    }
    assert summary["tool_latency_ms"]["grounded_generation"]["p95"] == 1000.0


def test_failure_classification_covers_debugging_layers() -> None:
    assert classify_failure("answer contains no evidence citations") == "prompt"
    assert classify_failure("evidence violates max_rating") == "retrieval"
    assert classify_failure("statistics calculation=None") == "data"
    assert classify_failure("generation_status=degraded") == "model"
    assert classify_failure("response tools=[]") == "orchestration"


def test_live_eval_rejects_silent_generation_degradation() -> None:
    case = {
        "expect": {
            "task": "evidence_qa",
            "regions": [],
            "max_rating": None,
            "tools": [
                "search_reviews",
                "evidence_verifier",
                "grounded_generation",
            ],
        }
    }
    response = {
        "task": "evidence_qa",
        "filters": {"regions": [], "max_rating": None},
        "steps": [
            {"tool": "search_reviews"},
            {"tool": "evidence_verifier"},
            {"tool": "grounded_generation"},
        ],
        "evidence": [{"review_id": "r1", "region": "CN", "rating": 5}],
        "analytics": {"generation": {"status": "degraded"}},
        "answer": "Generation unavailable.",
    }
    assert live_failures(case, response) == [
        "generation_status=degraded, expected=completed"
    ]
