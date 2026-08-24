from app.agent.executor import ReviewAgent
from app.agent.planner import build_plan
from app.agent.router import route_task
from app.agent.tools import verify_evidence


class FakeTools:
    def topic_distribution(self, filters):
        return {"available": True, "review_count": 12, "topics": []}

    def compare_topics_by_market(self, filters):
        return {"available": True, "markets": {"KR": {"review_count": 12}}}

    def review_statistics(self, filters):
        return {
            "review_count": 12,
            "average_rating": 2.5,
            "by_market": {"KR": 12},
            "by_rating": {"1": 4, "2": 4, "3": 4},
            "by_month": {},
            "calculation": "deterministic",
            "duration_ms": 1.0,
        }

    def search_reviews(self, query, filters, limit):
        return (
            [
                {
                    "review_id": "review-1",
                    "region": "KR",
                    "rating": 2,
                    "review_date": "2025-01-01",
                    "text": "The queue was too long.",
                    "score": 0.9,
                }
            ],
            {"retrieval_mode": "dense"},
        )

    def search_reviews_by_market(self, query, filters, limit):
        return self.search_reviews(query, filters, limit)


class FakeGemini:
    def generate_agent_answer(self, **kwargs):
        assert '"review_count": 12' in kwargs["analytics_json"]
        assert "[review-1]" in kwargs["evidence_text"]
        return "Supported answer [review-1]"


class FailingGemini:
    def generate_agent_answer(self, **kwargs):
        raise RuntimeError("temporary provider error")


def test_router_supports_three_agent_workflows() -> None:
    assert route_task("Compare Korea and Hong Kong") == "market_comparison"
    assert route_task("What are the root causes of complaints?") == (
        "root_cause_analysis"
    )
    assert route_task("What should management prioritize improving?") == (
        "improvement_planning"
    )
    assert route_task("What do visitors say about food?") == "evidence_qa"


def test_planner_exposes_auditable_tools() -> None:
    tools = [step.tool for step in build_plan("market_comparison")]
    assert tools == [
        "review_statistics",
        "compare_topics_by_market",
        "search_reviews",
        "evidence_verifier",
        "grounded_generation",
    ]


def test_evidence_verifier_rejects_empty_results() -> None:
    assert not verify_evidence([])["passed"]
    assert verify_evidence([{"review_id": "r1"}])["passed"]


def test_agent_executes_statistics_retrieval_verification_and_generation() -> None:
    agent = ReviewAgent.__new__(ReviewAgent)
    agent.tools = FakeTools()
    agent.gemini_service = FakeGemini()

    state = agent.run(
        "What should management prioritize improving?",
        {"regions": ["KR"], "max_rating": None},
        evidence_limit=5,
    )

    assert state.task == "improvement_planning"
    assert state.filters["max_rating"] == 3
    assert state.answer == "Supported answer [review-1]"
    assert all(step.status == "completed" for step in state.plan)
    assert state.analytics["verification"]["passed"]


def test_agent_preserves_tool_outputs_when_generation_fails() -> None:
    agent = ReviewAgent.__new__(ReviewAgent)
    agent.tools = FakeTools()
    agent.gemini_service = FailingGemini()

    state = agent.run(
        "What are the root causes of complaints?",
        {"regions": [], "max_rating": None},
    )

    assert "temporarily unavailable" in state.answer
    assert state.evidence
    assert state.analytics["statistics"]["review_count"] == 12
    assert state.analytics["generation_error"] == "RuntimeError"
    assert state.plan[-1].status == "failed"
