from app.agent.state import AgentStep, AgentTask


def build_plan(task: AgentTask) -> list[AgentStep]:
    if task == "market_comparison":
        return [
            AgentStep("Calculate segment statistics", "review_statistics"),
            AgentStep("Retrieve evidence by market", "search_reviews"),
            AgentStep("Verify evidence coverage", "evidence_verifier"),
            AgentStep("Write market comparison", "grounded_generation"),
        ]
    if task == "root_cause_analysis":
        return [
            AgentStep("Calculate low-rating distribution", "review_statistics"),
            AgentStep("Retrieve complaint evidence", "search_reviews"),
            AgentStep("Verify evidence coverage", "evidence_verifier"),
            AgentStep("Explain supported root causes", "grounded_generation"),
        ]
    if task == "improvement_planning":
        return [
            AgentStep("Calculate low-rating distribution", "review_statistics"),
            AgentStep("Retrieve problem evidence", "search_reviews"),
            AgentStep("Verify evidence coverage", "evidence_verifier"),
            AgentStep("Prioritize supported actions", "grounded_generation"),
        ]
    return [
        AgentStep("Retrieve relevant reviews", "search_reviews"),
        AgentStep("Verify evidence coverage", "evidence_verifier"),
        AgentStep("Answer from evidence", "grounded_generation"),
    ]
