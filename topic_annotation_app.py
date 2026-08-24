import json
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from app.services.translation_service import (
    contains_korean,
    load_cache,
    save_cache,
    translate_batch_to_chinese,
)


SAMPLE_PATH = Path("data/topic_audit_sample.jsonl")
HUMAN_PATH = Path("data/topic_audit_reviews.jsonl")
TAXONOMY_PATH = Path("config/topic_taxonomy.json")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_reviews(rows: dict[str, dict]) -> None:
    temporary = HUMAN_PATH.with_suffix(".jsonl.tmp")
    temporary.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows.values()),
        encoding="utf-8",
    )
    temporary.replace(HUMAN_PATH)


st.set_page_config(page_title="Aladdin Topic Audit", page_icon="🏷️", layout="wide")
st.title("Aladdin Topic Label Audit")
st.caption("Human verification of Gemini-assisted topics and sentiment · progress saves locally")

sample = load_jsonl(SAMPLE_PATH)
if not sample:
    st.error("Audit sample missing. Run: make topic-audit-sample")
    st.stop()
taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
topic_options = [item["id"] for item in taxonomy["topics"]]
sentiment_options = taxonomy["sentiments"]
human = {row["review_id"]: row for row in load_jsonl(HUMAN_PATH)}

if "topic_audit_index" not in st.session_state:
    st.session_state.topic_audit_index = next(
        (i for i, row in enumerate(sample) if row["review_id"] not in human), 0
    )
index = max(0, min(st.session_state.topic_audit_index, len(sample) - 1))
row = sample[index]
existing = human.get(row["review_id"])

verified = [item for item in human.values() if item["status"] == "verified"]
topic_exact = sum(set(x["human_topics"]) == set(x["ai_topics"]) for x in verified)
sentiment_match = sum(x["human_sentiment"] == x["ai_sentiment"] for x in verified)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Progress", f"{len(human)} / {len(sample)}")
c2.metric("Verified", len(verified))
c3.metric("Exact topic agreement", f"{topic_exact / len(verified):.1%}" if verified else "—")
c4.metric("Sentiment agreement", f"{sentiment_match / len(verified):.1%}" if verified else "—")
st.progress(len(human) / len(sample))

st.subheader(f"Item {index + 1} of {len(sample)}")
left, right = st.columns([1.2, 1], gap="large")
with left:
    st.markdown("**Original review**")
    st.info(row["text"])
    st.caption(
        f"Market: {row['region']} · Rating: {row['rating']} · Date: {row.get('review_date')}"
    )
with right:
    cache = load_cache()
    translation = cache.get(row["review_id"])
    st.markdown("**Chinese translation**")
    if translation:
        st.success(translation)
    elif contains_korean(row["text"]):
        if st.button("Translate this Korean review"):
            with st.spinner("Translating..."):
                cache.update(translate_batch_to_chinese([{"review_id": row["review_id"], "text": row["text"]}]))
                save_cache(cache)
            st.rerun()
        st.warning("Translation is not cached yet.")
    else:
        st.write("Original is Chinese or English; no translation required.")

st.markdown("**Gemini suggestion (not ground truth)**")
st.code(
    f"topics={row['ai_topics']}\nsentiment={row['ai_sentiment']}\nconfidence={row['ai_confidence']}"
)
default_topics = existing["human_topics"] if existing else row["ai_topics"]
default_sentiment = existing["human_sentiment"] if existing else row["ai_sentiment"]
human_topics = st.multiselect("Correct topics", topic_options, default=default_topics, key=f"topics-{row['review_id']}")
human_sentiment = st.selectbox(
    "Correct sentiment",
    sentiment_options,
    index=sentiment_options.index(default_sentiment),
    key=f"sentiment-{row['review_id']}",
)
notes = st.text_input("Optional note", value=existing.get("notes", "") if existing else "", key=f"note-{row['review_id']}")


def decide(status: str) -> None:
    human[row["review_id"]] = {
        **{key: row[key] for key in ["review_id", "region", "rating", "ai_topics", "ai_sentiment", "ai_confidence"]},
        "human_topics": human_topics if status == "verified" else [],
        "human_sentiment": human_sentiment if status == "verified" else "",
        "status": status,
        "notes": notes,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    save_reviews(human)
    st.session_state.topic_audit_index = min(index + 1, len(sample) - 1)
    st.rerun()


b1, b2, b3, b4 = st.columns(4)
if b1.button("Confirm / Save", type="primary", use_container_width=True):
    decide("verified")
if b2.button("Skip / Unsure", use_container_width=True):
    decide("skipped")
if b3.button("← Previous", disabled=index == 0, use_container_width=True):
    st.session_state.topic_audit_index = index - 1
    st.rerun()
if b4.button("Next →", disabled=index == len(sample) - 1, use_container_width=True):
    st.session_state.topic_audit_index = index + 1
    st.rerun()
