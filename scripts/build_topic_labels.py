"""Create resumable, private AI-assisted topic labels for normalized reviews."""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai


def parse_json_response(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


def validate_labels(
    payload: Any,
    expected_ids: set[str],
    allowed_topics: set[str],
    allowed_sentiments: set[str],
) -> list[dict[str, Any]]:
    rows = payload.get("labels") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Gemini response must contain a labels array")
    output = []
    seen = set()
    for row in rows:
        review_id = str(row.get("review_id", ""))
        topics = row.get("topics")
        sentiment = row.get("sentiment")
        confidence = row.get("confidence")
        if review_id not in expected_ids or review_id in seen:
            raise ValueError(f"Unexpected or duplicate review_id: {review_id}")
        if not isinstance(topics, list) or not topics:
            raise ValueError(f"At least one topic is required for {review_id}")
        topics = list(dict.fromkeys(str(topic) for topic in topics))
        unknown = set(topics) - allowed_topics
        if unknown:
            raise ValueError(f"Unknown topics for {review_id}: {sorted(unknown)}")
        if sentiment not in allowed_sentiments:
            raise ValueError(f"Invalid sentiment for {review_id}: {sentiment}")
        try:
            confidence = float(confidence)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid confidence for {review_id}") from exc
        if not 0 <= confidence <= 1:
            raise ValueError(f"Confidence outside 0..1 for {review_id}")
        seen.add(review_id)
        output.append(
            {
                "review_id": review_id,
                "topics": topics,
                "sentiment": sentiment,
                "confidence": confidence,
            }
        )
    missing = expected_ids - seen
    if missing:
        raise ValueError(f"Missing review IDs: {sorted(missing)}")
    return output


def completed_ids(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    ids = set()
    with output_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                ids.add(str(json.loads(line)["review_id"]))
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValueError(
                    f"Invalid existing label at line {line_number}"
                ) from exc
    return ids


def batches(items: list[Any], size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def build_prompt(batch: list[dict[str, Any]], taxonomy: dict[str, Any]) -> str:
    topic_lines = "\n".join(
        f"- {item['id']}: {item['description']}" for item in taxonomy["topics"]
    )
    inputs = [
        {"review_id": str(row["review_id"]), "text": str(row["text"])}
        for row in batch
    ]
    return f"""You label customer reviews for review-intelligence analytics.
Assign one or more topics, one overall sentiment, and confidence from 0 to 1.
Use only the allowed topic IDs. Use other only when no defined topic fits.
Do not translate, summarize, or alter review_id.

Allowed topics:
{topic_lines}

Allowed sentiments: {', '.join(taxonomy['sentiments'])}

Return strict JSON only:
{{"labels":[{{"review_id":"...","topics":["..."],"sentiment":"negative","confidence":0.9}}]}}
Return exactly one label for every input review.

Reviews:
{json.dumps(inputs, ensure_ascii=False)}
"""


def label_batch(client, model: str, batch, taxonomy) -> list[dict[str, Any]]:
    response = client.models.generate_content(
        model=model,
        contents=build_prompt(batch, taxonomy),
    )
    parsed = parse_json_response(response.text or "")
    return validate_labels(
        parsed,
        {str(row["review_id"]) for row in batch},
        {item["id"] for item in taxonomy["topics"]},
        set(taxonomy["sentiments"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/disney_reviews_normalized.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/topic_labels.jsonl"))
    parser.add_argument("--taxonomy", type=Path, default=Path("config/topic_taxonomy.json"))
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    load_dotenv(Path(".env"))
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")
    if not api_key or not model:
        raise RuntimeError("GEMINI_API_KEY and GEMINI_MODEL are required")
    taxonomy = json.loads(args.taxonomy.read_text(encoding="utf-8"))
    reviews = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.overwrite:
        args.output.unlink(missing_ok=True)
    done = completed_ids(args.output)
    pending = [row for row in reviews if str(row["review_id"]) not in done]
    if args.limit is not None:
        pending = pending[: args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)
    total = len(pending)
    with args.output.open("a", encoding="utf-8") as output:
        for offset, batch in enumerate(batches(pending, args.batch_size)):
            labels = label_batch(client, model, batch, taxonomy)
            source_by_id = {str(row["review_id"]): row for row in batch}
            generated_at = datetime.now(timezone.utc).isoformat()
            for label in labels:
                source = source_by_id[label["review_id"]]
                record = {
                    **label,
                    "region": source.get("region"),
                    "rating": source.get("rating"),
                    "review_date": source.get("review_date"),
                    "model": model,
                    "taxonomy_version": taxonomy["version"],
                    "generated_at": generated_at,
                }
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
            output.flush()
            processed = min((offset + 1) * args.batch_size, total)
            print(f"Labeled {processed}/{total}; previously completed {len(done)}")
            if processed < total:
                time.sleep(args.sleep)


if __name__ == "__main__":
    main()
