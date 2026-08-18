import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from google import genai

logger = logging.getLogger(__name__)


class GeminiService:
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
        self.client = genai.Client(api_key=api_key)

    def generate_answer(
        self,
        query: str,
        evidence_text: str,
    ) -> str:
        prompt = f"""
You are an internal consumer-review analysis assistant for
Tokyo Disneyland.

Answer only from the review evidence provided below.
Do not use external knowledge or unsupported assumptions.

Requirements:
1. Answer in the same language as the user's question.
2. Summarize two to four main findings.
3. Cite at least one review_id after every main finding,
   using the format [review_id].
4. Use a review only when it directly supports the finding.
5. Do not generalize a small number of reviews to all visitors.
6. Do not invent percentages, counts, or statistics.
7. Clearly state when the evidence is insufficient.
8. End with an Evidence scope statement explaining that
   the answer is based only on the retrieved reviews.

Question:
{query}

Review evidence:
{evidence_text}
"""

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
                return response.text or "Gemini returned an empty response."
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Gemini model unavailable; trying fallback",
                    extra={"model": model_name},
                )

        assert last_error is not None
        raise last_error
