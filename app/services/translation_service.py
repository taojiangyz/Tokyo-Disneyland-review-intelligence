import json
import os
from pathlib import Path
import re

from dotenv import load_dotenv
from google import genai
from app.services.llm_telemetry import generate_text
from app.services.translation_parsing import parse_translation

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
    expected_ids = {item["review_id"] for item in items}
    raw_text = generate_text(
        client, [model_name], prompt, operation="annotation_translation",
        validator=lambda text: parse_translation(text, ids=expected_ids),
    )
    return parse_translation(raw_text, ids=expected_ids)
