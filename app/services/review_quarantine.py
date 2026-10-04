"""Auditable retrieval exclusions; source records remain intact."""
import json
from pathlib import Path

QUARANTINE_PATH = Path(__file__).resolve().parents[2] / "config" / "review_quarantine.json"


def excluded_review_ids() -> list[str]:
    data = json.loads(QUARANTINE_PATH.read_text(encoding="utf-8"))
    result = []
    for row in data["reviews"]:
        if row["status"] not in {"excluded", "released"}:
            raise ValueError("Invalid review quarantine status")
        review_id = row["review_id"]
        if not isinstance(review_id, str) or not review_id.strip():
            raise ValueError("Review quarantine requires a nonempty string ID")
        if row["status"] == "excluded":
            result.append(review_id)
    return sorted(set(result))
