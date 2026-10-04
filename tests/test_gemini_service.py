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


def test_generate_answer_uses_fallback_model(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LLM_TELEMETRY_DIR", str(tmp_path))
    service = GeminiService.__new__(GeminiService)
    service.model_name = "primary-model"
    service.fallback_model_name = "fallback-model"
    fake_models = FakeModels()
    service.client = SimpleNamespace(models=fake_models)

    attempts = []
    answer = service.generate_answer("Question", "Evidence", request_id="test", attempts=attempts)

    assert answer.startswith("fallback answer")
    assert "Evidence scope statement:" in answer
    assert fake_models.calls == ["primary-model", "fallback-model"]
    assert [a["status"] for a in attempts] == ["failed", "completed"]
    assert attempts[-1]["model"] == "fallback-model"


def test_prompt_explicit_language_and_evidence_boundaries(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_TELEMETRY_DIR', str(tmp_path))
    service = GeminiService.__new__(GeminiService)
    service.model_name = service.fallback_model_name = 'test-model'
    from unittest.mock import Mock
    service.client = SimpleNamespace(models=Mock())
    service.client.models.generate_content.return_value = SimpleNamespace(text='answer')
    service.generate_answer('What about food?', '价格便宜')
    prompt = service.client.models.generate_content.call_args.kwargs['contents']
    assert 'Respond only in English' in prompt
    assert 'does not establish that food prices are cheaper' in prompt
    service.generate_answer('餐饮贵吗？', 'cheap')
    assert 'Respond only in Simplified Chinese' in service.client.models.generate_content.call_args.kwargs['contents']


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
