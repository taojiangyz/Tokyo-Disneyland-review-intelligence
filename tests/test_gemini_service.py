from types import SimpleNamespace

from app.services.gemini_service import GeminiService


class FakeModels:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_content(self, model: str, contents: str):
        self.calls.append(model)
        if model == "primary-model":
            raise RuntimeError("temporary overload")
        return SimpleNamespace(text="fallback answer")


class FakePlannerModels:
    def generate_content(self, model: str, contents: str, config):
        assert "submit_agent_plan" in str(config.tools)
        return SimpleNamespace(
            function_calls=[
                SimpleNamespace(
                    name="submit_agent_plan",
                    args={
                        "task": "evidence_qa",
                        "calls": [
                            {"tool": "search_reviews", "arguments": {}},
                            {"tool": "evidence_verifier", "arguments": {}},
                            {"tool": "grounded_generation", "arguments": {}},
                        ],
                    },
                )
            ]
        )


def test_generate_answer_uses_fallback_model() -> None:
    service = GeminiService.__new__(GeminiService)
    service.model_name = "primary-model"
    service.fallback_model_name = "fallback-model"
    service.last_model_name = service.model_name
    fake_models = FakeModels()
    service.client = SimpleNamespace(models=fake_models)

    answer = service.generate_answer("Question", "Evidence")

    assert answer == "fallback answer"
    assert fake_models.calls == ["primary-model", "fallback-model"]
    assert service.last_model_name == "fallback-model"


def test_plan_agent_tools_parses_native_function_call() -> None:
    service = GeminiService.__new__(GeminiService)
    service.model_name = "planner-model"
    service.fallback_model_name = "fallback-model"
    service.last_model_name = service.model_name
    service.client = SimpleNamespace(models=FakePlannerModels())

    plan = service.plan_agent_tools("What do visitors say?", {"regions": []})

    assert plan.task == "evidence_qa"
    assert [call.tool for call in plan.calls] == [
        "search_reviews",
        "evidence_verifier",
        "grounded_generation",
    ]
    assert service.last_prompt_id == "tool_planner"
    assert service.last_prompt_version == "1.0.0"
