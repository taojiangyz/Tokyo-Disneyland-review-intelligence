import json
import os
from pathlib import Path
import re

from dotenv import load_dotenv
from google import genai

KOREAN_PATTERN = re.compile(r"[\uac00-\ud7a3]")
DEFAULT_CACHE_PATH = Path("evals/annotations/translation_cache.json")


def contains_korean(text: str) -> bool:
    return bool(KOREAN_PATTERN.search(text))


def load_cache(path: Path = DEFAULT_CACHE_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_cache(cache: dict[str, str], path: Path = DEFAULT_CACHE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def translate_batch_to_chinese(items: list[dict[str, str]]) -> dict[str, str]:
    if not items:
        return {}
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL")
    if not api_key or not model_name:
        raise RuntimeError("Gemini translation configuration is missing")
    prompt_items = json.dumps(items, ensure_ascii=False)
    prompt = f"""
Translate each Korean customer review into natural Simplified Chinese.
Preserve meaning, tone, and concrete details. Do not summarize or add facts.
Return only a valid JSON object mapping each review_id to its Chinese translation.

Reviews:
{prompt_items}
"""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
    )
    raw_text = (response.text or "").strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.removeprefix("```json").removeprefix("```")
        raw_text = raw_text.removesuffix("```").strip()
    translations = json.loads(raw_text)
    expected_ids = {item["review_id"] for item in items}
    if set(translations) != expected_ids:
        raise ValueError("Translation response IDs do not match the request")
    return {str(key): str(value) for key, value in translations.items()}
