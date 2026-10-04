from dataclasses import dataclass, field
from typing import Any, Literal


AgentTask = Literal[
    "evidence_qa",
    "root_cause_analysis",
    "market_comparison",
    "improvement_planning",
]


@dataclass
class AgentStep:
    name: str
    tool: str
    status: Literal["planned", "completed", "failed"] = "planned"
    summary: str | None = None
    duration_ms: float | None = None


@dataclass
class AgentState:
    query: str
    task: AgentTask
    filters: dict[str, Any]
    plan: list[AgentStep] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    analytics: dict[str, Any] = field(default_factory=dict)
    answer: str = ""
