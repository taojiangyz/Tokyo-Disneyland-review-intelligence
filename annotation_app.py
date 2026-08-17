import csv
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import streamlit as st

from app.services.translation_service import (
    contains_korean,
    load_cache,
    save_cache,
    translate_batch_to_chinese,
)

CANDIDATE_PATH = Path("evals/annotations/candidate_pool_15.csv")
AI_LABEL_PATH = Path("evals/annotations/ai_suggested_relevance_labels.csv")
HUMAN_LABEL_PATH = Path("evals/annotations/human_verified_relevance_labels.csv")
HUMAN_FIELDS = ["query_id", "review_id", "relevance", "status", "notes", "reviewed_at"]


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def label_key(row: dict[str, str]) -> tuple[str, str]:
    return row["query_id"], row["review_id"]


def load_human_labels() -> dict[tuple[str, str], dict[str, str]]:
    return {label_key(row): row for row in load_csv(HUMAN_LABEL_PATH)}


def save_human_labels(labels: dict[tuple[str, str], dict[str, str]]) -> None:
    HUMAN_LABEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = HUMAN_LABEL_PATH.with_suffix(".csv.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HUMAN_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(labels.values())
    temporary_path.replace(HUMAN_LABEL_PATH)


def save_decision(row: dict[str, str], relevance: str, status: str, notes: str) -> None:
    labels = load_human_labels()
    labels[label_key(row)] = {
        "query_id": row["query_id"],
        "review_id": row["review_id"],
        "relevance": relevance,
        "status": status,
        "notes": notes,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    save_human_labels(labels)


def export_verified_csv(labels: dict[tuple[str, str], dict[str, str]]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=HUMAN_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(labels.values())
    return buffer.getvalue()


st.set_page_config(page_title="Aladdin Relevance Review", page_icon="✅", layout="wide")
st.title("Aladdin Relevance Review")
st.caption("Human verification workspace · AI suggestions are never treated as ground truth")

candidates = load_csv(CANDIDATE_PATH)
if not candidates:
    st.error(f"Candidate pool not found: {CANDIDATE_PATH}")
    st.stop()

ai_suggestions = {label_key(row): row for row in load_csv(AI_LABEL_PATH)}
human_labels = load_human_labels()
translation_cache = load_cache()

if "annotation_index" not in st.session_state:
    first_unreviewed = next(
        (index for index, row in enumerate(candidates) if label_key(row) not in human_labels),
        0,
    )
    st.session_state.annotation_index = first_unreviewed

reviewed_count = len(human_labels)
verified_count = sum(row["status"] == "verified" for row in human_labels.values())
skipped_count = sum(row["status"] == "skipped" for row in human_labels.values())
agreement_pairs = [
    (human_labels[key], suggestion)
    for key, suggestion in ai_suggestions.items()
    if key in human_labels and human_labels[key]["status"] == "verified"
]
agreement_count = sum(
    human["relevance"] == suggestion["relevance"]
    for human, suggestion in agreement_pairs
)
agreement = (
    f"{agreement_count / len(agreement_pairs):.0%}"
    if agreement_pairs
    else "—"
)

metric1, metric2, metric3, metric4, metric5 = st.columns(5)
metric1.metric("Progress", f"{reviewed_count} / {len(candidates)}")
metric2.metric("Verified", verified_count)
metric3.metric("Skipped", skipped_count)
metric4.metric("AI suggestions", len(ai_suggestions))
metric5.metric("Human–AI agreement", agreement)
st.progress(reviewed_count / len(candidates))

query_ids = list(dict.fromkeys(row["query_id"] for row in candidates))
selected_query = st.selectbox("Jump to question", ["All questions", *query_ids])
if selected_query != "All questions":
    matching_indices = [i for i, row in enumerate(candidates) if row["query_id"] == selected_query]
    if st.button("Open first item in this question"):
        st.session_state.annotation_index = matching_indices[0]
        st.rerun()

index = max(0, min(st.session_state.annotation_index, len(candidates) - 1))
row = candidates[index]
key = label_key(row)

st.divider()
st.subheader(f"Item {index + 1} of {len(candidates)} · {row['query_id']}")
st.markdown("**Question**")
st.info(row["question"])

left, right = st.columns([1.2, 1], gap="large")
with left:
    st.markdown("**Original review**")
    st.write(row["text"])
    st.caption(
        f"Market: {row['region']} · Rating: {row['rating']} · "
        f"Date: {row['review_date']} · Retrieved by: {row['retrieved_by']}"
    )

with right:
    st.markdown("**Chinese translation (AI-generated)**")
    translation = translation_cache.get(row["review_id"])
    if translation:
        st.success(translation)
    elif contains_korean(row["text"]):
        st.warning("Translation is not cached yet.")
        if st.button("Translate this Korean review"):
            with st.spinner("Translating..."):
                translated = translate_batch_to_chinese(
                    [{"review_id": row["review_id"], "text": row["text"]}]
                )
                translation_cache.update(translated)
                save_cache(translation_cache)
            st.rerun()
    else:
        st.write("The original review is already readable as Chinese or English.")

suggestion = ai_suggestions.get(key)
if suggestion:
    st.markdown(
        f"**Codex suggestion (not ground truth): {suggestion['relevance']}** — "
        f"{suggestion['notes']}"
    )
else:
    st.caption("No Codex suggestion is available for this item.")

existing = human_labels.get(key)
if existing:
    if existing["status"] == "verified":
        st.success(f"Saved human label: {existing['relevance']}")
    else:
        st.warning("This item was skipped.")

notes = st.text_input(
    "Optional reviewer note",
    value=existing["notes"] if existing else "",
    key=f"notes-{row['query_id']}-{row['review_id']}",
)

st.markdown("**Your final decision**")
button0, button1, button2, button_skip = st.columns(4)


def decide(relevance: str, status: str) -> None:
    save_decision(row, relevance, status, notes)
    st.session_state.annotation_index = min(index + 1, len(candidates) - 1)
    st.rerun()


if button0.button("0 · Unrelated", use_container_width=True):
    decide("0", "verified")
if button1.button("1 · Partly relevant", use_container_width=True):
    decide("1", "verified")
if button2.button("2 · Directly relevant", type="primary", use_container_width=True):
    decide("2", "verified")
if button_skip.button("Skip / Unsure", use_container_width=True):
    decide("", "skipped")

previous, next_item, next_unreviewed = st.columns(3)
if previous.button("← Previous", disabled=index == 0, use_container_width=True):
    st.session_state.annotation_index = index - 1
    st.rerun()
if next_item.button("Next →", disabled=index == len(candidates) - 1, use_container_width=True):
    st.session_state.annotation_index = index + 1
    st.rerun()
if next_unreviewed.button("Next unreviewed", use_container_width=True):
    target = next(
        (
            candidate_index
            for candidate_index in range(index + 1, len(candidates))
            if label_key(candidates[candidate_index]) not in human_labels
        ),
        index,
    )
    st.session_state.annotation_index = target
    st.rerun()

st.download_button(
    "Download current human labels",
    data=export_verified_csv(human_labels),
    file_name="human_verified_relevance_labels.csv",
    mime="text/csv",
)
