import json
from time import perf_counter
from typing import Any

from app.agent.planner import build_plan
from app.agent.router import route_task
from app.agent.state import AgentState
from app.agent.tools import ReviewTools, verify_evidence


class ReviewAgent:
    def __init__(self, rag_service, gemini_service) -> None:
        self.tools = ReviewTools(rag_service)
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
            filters=dict(filters),
            plan=build_plan(task),
        )

        if task in {"root_cause_analysis", "improvement_planning"}:
            if state.filters.get("max_rating") is None:
                state.filters["max_rating"] = 3

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
                    state.answer = self._generate_answer(state)
                    step.summary = "Generated answer from tool outputs"
                step.status = "completed"
            except Exception as exc:
                step.status = "failed"
                step.summary = str(exc)
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
