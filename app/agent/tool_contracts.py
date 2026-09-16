from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agent.state import AgentStep, AgentTask


ToolName = Literal[
    "review_statistics",
    "topic_distribution",
    "compare_topics_by_market",
    "search_reviews",
    "evidence_verifier",
    "grounded_generation",
]


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_limit: int | None = Field(default=None, ge=3, le=10)


class PlannedToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: ToolName
    arguments: ToolArguments = Field(default_factory=ToolArguments)


class AgentPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: AgentTask
    calls: list[PlannedToolCall] = Field(min_length=3, max_length=6)

    @model_validator(mode="after")
    def validate_workflow(self) -> "AgentPlan":
        tools = [call.tool for call in self.calls]
        if tools[-1] != "grounded_generation":
            raise ValueError("grounded_generation must be the final tool")
        if "search_reviews" not in tools:
            raise ValueError("search_reviews is required")
        search_index = tools.index("search_reviews")
        verifier_index = tools.index("evidence_verifier") if "evidence_verifier" in tools else -1
        if verifier_index <= search_index:
            raise ValueError("evidence_verifier must follow search_reviews")
        if self.task in {"root_cause_analysis", "improvement_planning"}:
            required = {"review_statistics", "topic_distribution"}
            if not required.issubset(tools):
                raise ValueError("analytical task is missing required tools")
        if self.task == "market_comparison":
            required = {"review_statistics", "compare_topics_by_market"}
            if not required.issubset(tools):
                raise ValueError("market comparison is missing required tools")
        return self


STEP_NAMES: dict[ToolName, str] = {
    "review_statistics": "Calculate segment statistics",
    "topic_distribution": "Calculate topic distribution",
    "compare_topics_by_market": "Compare labeled topics by market",
    "search_reviews": "Retrieve relevant review evidence",
    "evidence_verifier": "Verify evidence coverage",
    "grounded_generation": "Write grounded answer",
}


def plan_to_steps(plan: AgentPlan) -> list[AgentStep]:
    return [AgentStep(STEP_NAMES[call.tool], call.tool) for call in plan.calls]


def submit_plan_function_schema() -> dict[str, Any]:
    """JSON Schema exposed to the model as one bounded function call."""
    return AgentPlan.model_json_schema()
