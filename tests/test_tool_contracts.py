import pytest
from pydantic import ValidationError

from app.agent.tool_contracts import AgentPlan, plan_to_steps


def valid_qa_plan() -> dict:
    return {
        "task": "evidence_qa",
        "calls": [
            {"tool": "search_reviews", "arguments": {"evidence_limit": 5}},
            {"tool": "evidence_verifier", "arguments": {}},
            {"tool": "grounded_generation", "arguments": {}},
        ],
    }


def test_plan_accepts_bounded_whitelisted_workflow() -> None:
    plan = AgentPlan.model_validate(valid_qa_plan())
    assert [step.tool for step in plan_to_steps(plan)] == [
        "search_reviews",
        "evidence_verifier",
        "grounded_generation",
    ]


def test_plan_rejects_unknown_tool() -> None:
    payload = valid_qa_plan()
    payload["calls"][0]["tool"] = "shell"
    with pytest.raises(ValidationError):
        AgentPlan.model_validate(payload)


def test_plan_rejects_unbounded_arguments() -> None:
    payload = valid_qa_plan()
    payload["calls"][0]["arguments"] = {"evidence_limit": 1000}
    with pytest.raises(ValidationError):
        AgentPlan.model_validate(payload)


def test_plan_requires_verification_after_retrieval() -> None:
    payload = valid_qa_plan()
    payload["calls"][0], payload["calls"][1] = (
        payload["calls"][1],
        payload["calls"][0],
    )
    with pytest.raises(ValidationError, match="must follow"):
        AgentPlan.model_validate(payload)


def test_analytical_plan_requires_statistics_tools() -> None:
    payload = valid_qa_plan()
    payload["task"] = "root_cause_analysis"
    with pytest.raises(ValidationError, match="required tools"):
        AgentPlan.model_validate(payload)
