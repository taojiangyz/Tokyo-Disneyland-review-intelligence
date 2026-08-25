from pathlib import Path

from scripts.run_agent_evaluation import load_cases, structural_result


CASES = Path("evals/agent_cases.jsonl")


def test_agent_evaluation_has_40_unique_cases_and_three_languages() -> None:
    cases = load_cases(CASES)
    assert len(cases) == 40
    assert len({case["id"] for case in cases}) == 40
    questions = "\n".join(case["question"] for case in cases)
    assert any("\u4e00" <= char <= "\u9fff" for char in questions)
    assert any("what" in case["question"].casefold() for case in cases)
    assert any("です" in case["question"] for case in cases)


def test_all_agent_structural_expectations_pass() -> None:
    failures = {
        case["id"]: structural_result(case)["failures"]
        for case in load_cases(CASES)
        if structural_result(case)["failures"]
    }
    assert failures == {}
