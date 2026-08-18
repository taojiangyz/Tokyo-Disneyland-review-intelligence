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
