from __future__ import annotations

import json
import os
from typing import Any, Protocol

import requests

from app.agent.tool_contracts import AgentPlan, submit_plan_function_schema
from app.prompts import PromptRegistry
from app.services.gemini_service import GeminiService


class ReviewLLMService(Protocol):
    provider_name: str
    last_model_name: str
    last_prompt_id: str | None
    last_prompt_version: str | None
    last_usage: dict[str, int]

    def reset_tracking(self) -> None: ...

    def generate_answer(self, query: str, evidence_text: str) -> str: ...

    def generate_agent_answer(
        self,
        query: str,
        task: str,
        evidence_text: str,
        analytics_json: str,
    ) -> str: ...

    def plan_agent_tools(
        self,
        query: str,
        filters: dict[str, object],
    ) -> AgentPlan: ...


class OpenAICompatibleService:
    """Review LLM service for Ollama, vLLM, and OpenAI-compatible endpoints."""

    provider_name = "openai_compatible"

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        session: Any | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("OPENAI_COMPAT_BASE_URL", "http://host.docker.internal:11434/v1")
        ).rstrip("/")
        self.model_name = model_name or os.getenv("OPENAI_COMPAT_MODEL", "")
        if not self.model_name:
            raise RuntimeError("OPENAI_COMPAT_MODEL is missing")
        self.api_key = api_key if api_key is not None else os.getenv(
            "OPENAI_COMPAT_API_KEY", ""
        )
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("OPENAI_COMPAT_TIMEOUT_SECONDS", "180")
        )
        self.session = session or requests.Session()
        self.prompt_registry = PromptRegistry()
        self.last_model_name = self.model_name
        self.last_prompt_id: str | None = None
        self.last_prompt_version: str | None = None
        self.last_usage: dict[str, int] = {}

    def reset_tracking(self) -> None:
        self.last_prompt_id = None
        self.last_prompt_version = None
        self.last_usage = {}

    def _render_prompt(self, prompt_id: str, **values: str) -> str:
        template = self.prompt_registry.get(prompt_id)
        self.last_prompt_id = template.prompt_id
        self.last_prompt_version = template.version
        return template.render(**values)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        usage = body.get("usage") or {}
        self.last_usage = {
            key: int(value)
            for key, value in usage.items()
            if isinstance(value, (int, float))
        }
        self.last_model_name = str(body.get("model") or self.model_name)
        return body

    def _generate_text(self, prompt: str) -> str:
        body = self._post(
            {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
        )
        content = body["choices"][0]["message"].get("content")
        if not content:
            raise RuntimeError("OpenAI-compatible provider returned empty content")
        return str(content)

    def generate_answer(self, query: str, evidence_text: str) -> str:
        return self._generate_text(
            self._render_prompt(
                "review_answer",
                query=query,
                evidence_text=evidence_text,
            )
        )

    def generate_agent_answer(
        self,
        query: str,
        task: str,
        evidence_text: str,
        analytics_json: str,
    ) -> str:
        return self._generate_text(
            self._render_prompt(
                "agent_answer",
                query=query,
                task=task,
                evidence_text=evidence_text,
                analytics_json=analytics_json,
            )
        )

    def plan_agent_tools(
        self,
        query: str,
        filters: dict[str, object],
    ) -> AgentPlan:
        prompt = self._render_prompt(
            "tool_planner",
            query=query,
            filters_json=json.dumps(filters, ensure_ascii=False, sort_keys=True),
        )
        body = self._post(
            {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "submit_agent_plan",
                            "description": "Submit a bounded review-analysis tool plan.",
                            "parameters": submit_plan_function_schema(),
                        },
                    }
                ],
                "tool_choice": {
                    "type": "function",
                    "function": {"name": "submit_agent_plan"},
                },
            }
        )
        calls = body["choices"][0]["message"].get("tool_calls") or []
        if len(calls) != 1:
            raise ValueError("Provider did not return one submit_agent_plan call")
        function = calls[0].get("function") or {}
        if function.get("name") != "submit_agent_plan":
            raise ValueError("Provider called an unexpected function")
        arguments = function.get("arguments") or "{}"
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        return AgentPlan.model_validate(arguments)


def build_llm_service() -> ReviewLLMService:
    provider = os.getenv("ALADDIN_LLM_PROVIDER", "gemini").strip().casefold()
    if provider == "gemini":
        return GeminiService()
    if provider in {"openai_compatible", "openai-compatible", "ollama", "vllm"}:
        return OpenAICompatibleService()
    raise RuntimeError(f"Unsupported ALADDIN_LLM_PROVIDER: {provider}")
