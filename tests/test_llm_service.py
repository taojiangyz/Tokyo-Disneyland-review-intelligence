import json

import pytest

from app.services.llm_service import OpenAICompatibleService, build_llm_service


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


class FakeSession:
    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.requests = []

    def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return FakeResponse(self.bodies.pop(0))


def test_openai_compatible_generation_records_usage() -> None:
    session = FakeSession(
        [
            {
                "model": "qwen-test",
                "choices": [{"message": {"content": "Answer [r1]"}}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
            }
        ]
    )
    service = OpenAICompatibleService(
        base_url="http://model.local/v1",
        model_name="qwen-test",
        session=session,
    )
    answer = service.generate_answer("Question", "[r1] Evidence")
    assert answer == "Answer [r1]"
    assert service.last_usage["total_tokens"] == 120
    assert session.requests[0][0].endswith("/chat/completions")


def test_openai_compatible_parses_function_call() -> None:
    arguments = {
        "task": "evidence_qa",
        "calls": [
            {"tool": "search_reviews", "arguments": {}},
            {"tool": "evidence_verifier", "arguments": {}},
            {"tool": "grounded_generation", "arguments": {}},
        ],
    }
    session = FakeSession(
        [
            {
                "model": "qwen-test",
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "submit_agent_plan",
                                        "arguments": json.dumps(arguments),
                                    }
                                }
                            ]
                        }
                    }
                ],
                "usage": {},
            }
        ]
    )
    service = OpenAICompatibleService(
        base_url="http://model.local/v1",
        model_name="qwen-test",
        session=session,
    )
    plan = service.plan_agent_tools("Question", {"regions": []})
    assert plan.task == "evidence_qa"
    request_payload = session.requests[0][1]["json"]
    assert request_payload["tools"][0]["function"]["name"] == "submit_agent_plan"


def test_provider_factory_rejects_unknown_provider(monkeypatch) -> None:
    monkeypatch.setenv("ALADDIN_LLM_PROVIDER", "unknown")
    with pytest.raises(RuntimeError, match="Unsupported"):
        build_llm_service()
