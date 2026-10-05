from app.agent.executor import ReviewAgent, resolve_agent_filters
from app.agent.planner import build_plan
from app.agent.router import infer_markets, route_task
from app.agent.tools import verify_evidence
from app.agent.tool_contracts import AgentPlan


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
    assert route_task("What are the main causes of low-rated reviews?") == (
        "root_cause_analysis"
    )
    assert route_task("低评分评论的主要原因是什么？") == "root_cause_analysis"
    assert route_task("低評価レビューの主な原因は何ですか？") == (
        "root_cause_analysis"
    )
    assert route_task("What should management prioritize improving?") == (
        "improvement_planning"
    )
    assert route_task("What do visitors say about food?") == "evidence_qa"


def test_router_infers_multilingual_market_names() -> None:
    assert infer_markets("Compare Korean and Hong Kong visitors") == ["HK", "KR"]
    assert infer_markets("比较中国大陆和韩国游客") == ["CN", "KR"]


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


def test_market_complaint_comparison_infers_markets_and_low_ratings() -> None:
    agent = ReviewAgent.__new__(ReviewAgent)
    agent.tools = FakeTools()
    agent.gemini_service = FakeGemini()
    state = agent.run(
        "Compare the main complaints from Korean and Hong Kong visitors.",
        {"regions": [], "max_rating": None},
    )
    assert state.task == "market_comparison"
    assert state.filters["regions"] == ["HK", "KR"]
    assert state.filters["max_rating"] == 3


def test_explicit_filters_override_query_inference() -> None:
    resolved = resolve_agent_filters(
        "Compare complaints from Korean and Hong Kong visitors",
        "market_comparison",
        {"regions": ["CN"], "max_rating": 2},
    )
    assert resolved["regions"] == ["CN"]
    assert resolved["max_rating"] == 2


def test_agent_skips_gemini_when_no_evidence_matches() -> None:
    class EmptyTools(FakeTools):
        def search_reviews(self, query, filters, limit):
            return [], {"retrieval_mode": "dense"}

        def search_reviews_by_market(self, query, filters, limit):
            return self.search_reviews(query, filters, limit)

    class GeminiMustNotRun:
        def generate_agent_answer(self, **kwargs):
            raise AssertionError("Gemini should not run without evidence")

    agent = ReviewAgent.__new__(ReviewAgent)
    agent.tools = EmptyTools()
    agent.gemini_service = GeminiMustNotRun()
    state = agent.run(
        "What do visitors say about queues?",
        {"regions": [], "max_rating": None},
    )
    assert state.analytics["generation"]["status"] == "skipped_no_evidence"
    assert "not enough evidence" in state.answer


def test_agent_uses_validated_function_call_plan_when_enabled(monkeypatch) -> None:
    class PlanningGemini(FakeGemini):
        def plan_agent_tools(self, query, filters):
            return AgentPlan.model_validate(
                {
                    "task": "evidence_qa",
                    "calls": [
                        {"tool": "search_reviews", "arguments": {}},
                        {"tool": "evidence_verifier", "arguments": {}},
                        {"tool": "grounded_generation", "arguments": {}},
                    ],
                }
            )

    monkeypatch.setenv("ALADDIN_LLM_PLANNER_ENABLED", "true")
    agent = ReviewAgent.__new__(ReviewAgent)
    agent.tools = FakeTools()
    agent.gemini_service = PlanningGemini()
    state = agent.run("What do visitors say about queues?", {"regions": []})
    assert state.analytics["planning"] == {
        "source": "gemini_function_call",
        "fallback_used": False,
    }


def test_agent_falls_back_when_function_call_plan_is_invalid(monkeypatch) -> None:
    class BrokenPlanningGemini(FakeGemini):
        def plan_agent_tools(self, query, filters):
            raise ValueError("invalid tool plan")

    monkeypatch.setenv("ALADDIN_LLM_PLANNER_ENABLED", "true")
    agent = ReviewAgent.__new__(ReviewAgent)
    agent.tools = FakeTools()
    agent.gemini_service = BrokenPlanningGemini()
    state = agent.run("What do visitors say about queues?", {"regions": []})
    assert state.analytics["planning"] == {
        "source": "deterministic_router",
        "fallback_used": True,
        "failure_type": "ValueError",
    }


def test_implicit_market_comparison_routes_to_balanced_retrieval():
    for query in (
        "不同市场的游客关注哪些主题？",
        "各市场的游客关注什么？",
        "What topics do visitors discuss across markets?",
        "Show topics by market",
        "市場別に関心のあるテーマを教えて",
    ):
        assert route_task(query) == "market_comparison"
    assert route_task("游客对不同游乐项目有什么评价？") == "evidence_qa"


def test_comparison_requires_market_context():
    for query in (
        "比较两个游乐项目", "Compare two rides", "二つのアトラクションを比較して",
        "Compare food and ticket prices in Korea",
    ):
        assert route_task(query) == "evidence_qa"
    for query in (
        "比较中国大陆和韩国游客", "Compare Korea and Hong Kong",
        "韓国と香港の違いは？", "比较不同市场的投诉",
    ):
        assert route_task(query) == "market_comparison"
    assert route_task("Compare complaints about two rides") == "root_cause_analysis"
    assert infer_markets("Discuss chinaware") == []


def test_market_retrieval_covers_available_markets_and_preserves_filters():
    from app.agent.tools import ReviewTools

    class RecordingTools(ReviewTools):
        def __init__(self, empty=()):
            self.calls = []
            self.empty = empty

        def search_reviews(self, query, filters, limit):
            self.calls.append(dict(filters))
            market = filters["regions"][0]
            return ([{"review_id": f"{market}-{i}", "region": market}
                     for i in range(limit)] if market not in self.empty else []), {}

    filters = {"regions": [], "min_rating": 2, "max_rating": 4,
               "date_from": "2025-01-01", "date_to": "2025-12-31"}
    tools = RecordingTools()
    evidence, _ = tools.search_reviews_by_market("不同市场的游客关注哪些主题？", filters, 5)
    assert len(evidence) == 5
    assert {r["region"] for r in evidence} == {"CN", "HK", "KR"}
    assert all(all(call[k] == filters[k] for k in filters if k != "regions")
               for call in tools.calls)
    assert filters["regions"] == []
    tools = RecordingTools(empty=("KR",))
    evidence, _ = tools.search_reviews_by_market("compare markets", {"regions": ["HK", "KR"]}, 5)
    assert [c["regions"] for c in tools.calls] == [["HK"], ["KR"]]
    assert {r["region"] for r in evidence} == {"HK"}
