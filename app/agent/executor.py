import json
from time import perf_counter
from typing import Any

from app.agent.planner import build_plan
from app.agent.router import has_root_cause_intent, infer_markets, route_task
from app.agent.state import AgentState
from app.agent.tools import ReviewTools, verify_evidence


def resolve_agent_filters(
    query: str,
    task: str,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """Apply deterministic query-derived filters without overriding UI choices."""
    resolved = dict(filters)
    if not resolved.get("regions"):
        inferred_markets = infer_markets(query)
        if inferred_markets:
            resolved["regions"] = inferred_markets

    needs_low_ratings = task in {
        "root_cause_analysis",
        "improvement_planning",
    } or (task == "market_comparison" and has_root_cause_intent(query))
    if needs_low_ratings and resolved.get("max_rating") is None:
        resolved["max_rating"] = 3
    return resolved


class ReviewAgent:
    def __init__(self, rag_service, gemini_service, topic_service=None) -> None:
        self.tools = ReviewTools(rag_service, topic_service)
        self.gemini_service = gemini_service

    def run(
        self,
        query: str,
        filters: dict[str, Any],
        evidence_limit: int = 5,
    ) -> AgentState:
        task = route_task(query)
        state = AgentState(
            query=query,
            task=task,
            filters=resolve_agent_filters(query, task, filters),
            plan=build_plan(task),
        )

        for step in state.plan:
            started = perf_counter()
            try:
                if step.tool == "review_statistics":
                    state.analytics["statistics"] = (
                        self.tools.review_statistics(state.filters)
                    )
                    step.summary = (
                        f"Calculated over {state.analytics['statistics']['review_count']} "
                        "matching reviews"
                    )
                elif step.tool == "topic_distribution":
                    result = self.tools.topic_distribution(state.filters)
                    state.analytics["topic_distribution"] = result
                    step.summary = (
                        f"Counted {len(result.get('topics', []))} labeled topics"
                        if result.get("available")
                        else "Topic labels are not available; skipped"
                    )
                elif step.tool == "compare_topics_by_market":
                    result = self.tools.compare_topics_by_market(state.filters)
                    state.analytics["topics_by_market"] = result
                    step.summary = (
                        f"Compared {len(result.get('markets', {}))} markets"
                        if result.get("available")
                        else "Topic labels are not available; skipped"
                    )
                elif step.tool == "search_reviews":
                    search = (
                        self.tools.search_reviews_by_market
                        if task == "market_comparison"
                        else self.tools.search_reviews
                    )
                    state.evidence, retrieval_trace = search(
                        query, state.filters, evidence_limit
                    )
                    state.analytics["retrieval_trace"] = retrieval_trace
                    step.summary = f"Selected {len(state.evidence)} reviews"
                elif step.tool == "evidence_verifier":
                    verification = verify_evidence(state.evidence)
                    state.analytics["verification"] = verification
                    step.summary = (
                        "Evidence verified"
                        if verification["passed"]
                        else "Evidence insufficient"
                    )
                elif step.tool == "grounded_generation":
                    verification = state.analytics.get("verification", {})
                    if not state.evidence and not verification.get("passed"):
                        state.answer = (
                            "No reviews matched the selected filters, so there is "
                            "not enough evidence to answer this question."
                        )
                        state.analytics["generation"] = {
                            "status": "skipped_no_evidence"
                        }
                        step.summary = "Skipped generation because no evidence matched"
                    else:
                        state.answer = self._generate_answer(state)
                        state.analytics["generation"] = {"status": "completed"}
                        step.summary = "Generated answer from tool outputs"
                step.status = "completed"
            except Exception as exc:
                step.status = "failed"
                step.summary = str(exc)
                if step.tool == "grounded_generation":
                    state.answer = (
                        "Answer generation is temporarily unavailable. "
                        "The deterministic analytics and retrieved evidence "
                        "remain available."
                    )
                    state.analytics["generation_error"] = type(exc).__name__
                    state.analytics["generation"] = {"status": "degraded"}
                else:
                    raise
            finally:
                step.duration_ms = round(
                    (perf_counter() - started) * 1000,
                    2,
                )
        return state

    def _generate_answer(self, state: AgentState) -> str:
        evidence_text = "\n\n".join(
            (
                f"[{item['review_id']}] Market: {item.get('region')}; "
                f"Rating: {item.get('rating')}; Date: {item.get('review_date')}\n"
                f"Review: {item.get('text', '')}"
            )
            for item in state.evidence
        )
        analytics = {
            key: value
            for key, value in state.analytics.items()
            if key != "retrieval_trace"
        }
        return self.gemini_service.generate_agent_answer(
            query=state.query,
            task=state.task,
            evidence_text=evidence_text,
            analytics_json=json.dumps(
                analytics,
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
