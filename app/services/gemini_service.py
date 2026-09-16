import os
import logging
import json
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.agent.tool_contracts import AgentPlan, submit_plan_function_schema
from app.prompts import PromptRegistry

logger = logging.getLogger(__name__)


class GeminiService:
    provider_name = "gemini"

    def __init__(self) -> None:
        load_dotenv(dotenv_path=Path(".env"))

        api_key = os.getenv("GEMINI_API_KEY")
        model_name = os.getenv("GEMINI_MODEL")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing")

        if not model_name:
            raise RuntimeError("GEMINI_MODEL is missing")

        self.model_name = model_name
        self.fallback_model_name = os.getenv(
            "GEMINI_FALLBACK_MODEL",
            "gemini-3.5-flash-lite",
        )
        self.last_model_name = model_name
        self.last_prompt_id: str | None = None
        self.last_prompt_version: str | None = None
        self.last_usage: dict[str, int] = {}
        self.prompt_registry = PromptRegistry()
        self.client = genai.Client(api_key=api_key)

    def reset_tracking(self) -> None:
        self.last_prompt_id = None
        self.last_prompt_version = None
        self.last_usage = {}

    def _render_prompt(self, prompt_id: str, **values: str) -> str:
        registry = getattr(self, "prompt_registry", None) or PromptRegistry()
        template = registry.get(prompt_id)
        self.last_prompt_id = template.prompt_id
        self.last_prompt_version = template.version
        return template.render(**values)

    def generate_answer(
        self,
        query: str,
        evidence_text: str,
    ) -> str:
        prompt = self._render_prompt(
            "review_answer",
            query=query,
            evidence_text=evidence_text,
        )

        return self._generate_with_fallback(prompt)

    def generate_agent_answer(
        self,
        query: str,
        task: str,
        evidence_text: str,
        analytics_json: str,
    ) -> str:
        prompt = self._render_prompt(
            "agent_answer",
            query=query,
            task=task,
            evidence_text=evidence_text,
            analytics_json=analytics_json,
        )
        return self._generate_with_fallback(prompt)

    def plan_agent_tools(
        self,
        query: str,
        filters: dict[str, object],
    ) -> AgentPlan:
        """Ask Gemini for one bounded native function call and validate it."""
        prompt = self._render_prompt(
            "tool_planner",
            query=query,
            filters_json=json.dumps(filters, ensure_ascii=False, sort_keys=True),
        )
        declaration = types.FunctionDeclaration(
            name="submit_agent_plan",
            description="Submit a validated, bounded review-analysis tool plan.",
            parametersJsonSchema=submit_plan_function_schema(),
        )
        config = types.GenerateContentConfig(
            temperature=0,
            tools=[types.Tool(functionDeclarations=[declaration])],
            toolConfig=types.ToolConfig(
                functionCallingConfig=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.ANY,
                    allowedFunctionNames=["submit_agent_plan"],
                )
            ),
            automaticFunctionCalling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        last_error: Exception | None = None
        for model_name in dict.fromkeys(
            [self.model_name, self.fallback_model_name]
        ):
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                calls = response.function_calls or []
                if len(calls) != 1 or calls[0].name != "submit_agent_plan":
                    raise ValueError("Model did not return one submit_agent_plan call")
                self.last_model_name = model_name
                return AgentPlan.model_validate(dict(calls[0].args or {}))
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Agent planning failed; trying fallback model",
                    extra={"model": model_name},
                )
        assert last_error is not None
        raise last_error

    def _generate_with_fallback(self, prompt: str) -> str:
        models = list(
            dict.fromkeys(
                [self.model_name, self.fallback_model_name]
            )
        )
        last_error: Exception | None = None
        for model_name in models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                self.last_model_name = model_name
                usage = getattr(response, "usage_metadata", None)
                self.last_usage = {
                    "prompt_tokens": int(
                        getattr(usage, "prompt_token_count", 0) or 0
                    ),
                    "completion_tokens": int(
                        getattr(usage, "candidates_token_count", 0) or 0
                    ),
                    "total_tokens": int(
                        getattr(usage, "total_token_count", 0) or 0
                    ),
                }
                return response.text or "Gemini returned an empty response."
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Gemini model unavailable; trying fallback",
                    extra={"model": model_name},
                )
        assert last_error is not None
        raise last_error
