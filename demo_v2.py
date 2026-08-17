import base64
import html
import json
import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv
from google import genai


API_BASE_URL = os.getenv("ALADDIN_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_URL = f"{API_BASE_URL}/api/v1/analyze"
METADATA_URL = f"{API_BASE_URL}/api/v1/metadata"
HERO_IMAGE = Path("assets/tokyo_disney_ai_hero.png")

DEFAULT_QUESTION = (
    "What are the main complaints about waiting time "
    "and crowding at Tokyo Disney?"
)

EXAMPLE_QUESTIONS = [
    DEFAULT_QUESTION,
    "What do visitors say about staff service?",
    "What are the main complaints in low-rated reviews?",
    "What do visitors like most about their park experience?",
]


def image_to_base64(image_path: Path) -> str:
    """Convert a local image to base64 for the Hero banner."""
    if not image_path.exists():
        return ""

    return base64.b64encode(
        image_path.read_bytes()
    ).decode("utf-8")


def safe_text(value: object) -> str:
    """Escape review content before inserting it into HTML."""
    return html.escape(str(value or ""))


def format_stars(rating: object) -> str:
    """Return a five-star text representation."""
    try:
        score = max(0, min(5, int(float(rating))))
    except (TypeError, ValueError):
        score = 0

    return "★" * score + "☆" * (5 - score)


@st.cache_data(ttl=300, show_spinner=False)
def load_metadata() -> dict:
    response = requests.get(METADATA_URL, timeout=10)
    response.raise_for_status()
    return response.json()



def translate_reviews_to_english(
    evidence: list[dict],
) -> list[str]:
    """Translate the visible evidence reviews in one Gemini request."""
    visible_items = evidence

    if not visible_items:
        return []

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL")

    if not api_key or not model_name:
        return [
            "English translation is temporarily unavailable."
            for _ in visible_items
        ]

    numbered_reviews = "\n\n".join(
        (
            f"Review {index}:\n"
            f"{item.get('text', '')}"
        )
        for index, item in enumerate(
            visible_items,
            start=1,
        )
    )

    prompt = f"""
Translate the following customer reviews into natural English.

Requirements:
1. Preserve the original meaning.
2. Do not summarize or add information.
3. Return only a valid JSON array of English strings.
4. Keep the translations in exactly the same order.
5. Return exactly {len(visible_items)} strings.

Reviews:
{numbered_reviews}
"""

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        raw_text = (response.text or "").strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.removeprefix("```json")
            raw_text = raw_text.removeprefix("```")
            raw_text = raw_text.removesuffix("```").strip()

        translations = json.loads(raw_text)

        if (
            not isinstance(translations, list)
            or len(translations) != len(visible_items)
        ):
            raise ValueError(
                "Gemini returned an unexpected translation format."
            )

        return [str(item) for item in translations]

    except Exception:
        return [
            "English translation is temporarily unavailable."
            for _ in visible_items
        ]


st.set_page_config(
    page_title="Tokyo Disney Review Intelligence",
    page_icon="🏰",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# -----------------------------
# Page styling
# -----------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: #f4f7fc;
    }

    .block-container {
        max-width: 1440px;
        padding-top: 1rem;
        padding-bottom: 3rem;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    .hero-banner {
        position: relative;
        height: 420px;
        overflow: hidden;
        margin-bottom: 22px;
        border-radius: 20px;
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        box-shadow: 0 12px 32px rgba(13, 31, 85, 0.16);
    }

    .hero-overlay {
        position: absolute;
        inset: 0;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 42px 54px;
        background: linear-gradient(
            90deg,
            rgba(3, 18, 70, 0.96) 0%,
            rgba(3, 18, 70, 0.82) 34%,
            rgba(3, 18, 70, 0.28) 58%,
            rgba(3, 18, 70, 0) 76%
        );
    }

    .hero-label {
        width: fit-content;
        margin-bottom: 16px;
        padding: 7px 13px;
        border: 1px solid rgba(255, 255, 255, 0.34);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.13);
        color: #ffffff;
        font-size: 14px;
        font-weight: 700;
    }

    .hero-title {
        max-width: 620px;
        margin-bottom: 18px;
        color: #ffffff;
        font-size: 46px;
        line-height: 1.08;
        font-weight: 760;
        letter-spacing: -0.025em;
        text-shadow: 0 3px 12px rgba(0, 0, 0, 0.28);
    }

    .hero-subtitle {
        max-width: 530px;
        color: rgba(255, 255, 255, 0.94);
        font-size: 19px;
        line-height: 1.5;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #e1e7f0;
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.98);
        box-shadow: 0 5px 18px rgba(23, 48, 101, 0.055);
    }

    div[data-testid="stMetric"] {
        min-height: 112px;
        padding: 16px 18px;
        border: 1px solid #e2e8f3;
        border-radius: 14px;
        background: #f7f9fe;
    }

    div[data-testid="stMetricLabel"] {
        font-weight: 650;
        color: #334155;
    }

    div[data-testid="stMetricValue"] {
        color: #102c78;
    }

    .stButton > button {
        min-height: 47px;
        border-radius: 9px;
        font-weight: 700;
        background: #2563eb;
        border-color: #2563eb;
        color: #ffffff;
    }

    .stButton > button:hover {
        background: #1d4ed8;
        border-color: #1d4ed8;
        color: #ffffff;
    }

    h2, h3 {
        color: #153a91;
    }

    .question-box {
        margin-bottom: 18px;
        padding: 16px 18px;
        border: 1px solid #cfe0fb;
        border-radius: 11px;
        background: #edf5ff;
        color: #164b8d;
        font-size: 17px;
        font-weight: 600;
    }

    .review-card {
        margin-bottom: 11px;
        padding: 14px 16px;
        border: 1px solid #e1e7f0;
        border-radius: 12px;
        background: #ffffff;
    }

    .review-heading {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 5px;
        color: #172554;
        font-weight: 700;
    }

    .review-stars {
        white-space: nowrap;
        color: #e53935;
        letter-spacing: 1px;
    }

    .review-meta {
        margin-bottom: 9px;
        color: #667085;
        font-size: 13px;
    }

    .review-text {
        color: #202939;
        line-height: 1.55;
    }

    .tech-item {
        min-height: 84px;
        padding: 10px 14px;
        border-left: 3px solid #2563eb;
    }

    .tech-title {
        margin-bottom: 5px;
        color: #153a91;
        font-weight: 750;
    }

    .tech-description {
        color: #5b6475;
        font-size: 14px;
        line-height: 1.4;
    }

    @media (max-width: 800px) {
        .hero-banner {
            height: 330px;
        }

        .hero-overlay {
            padding: 30px;
            background: rgba(3, 18, 70, 0.74);
        }

        .hero-title {
            font-size: 35px;
        }

        .hero-subtitle {
            font-size: 16px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Hero banner
# -----------------------------
hero_base64 = image_to_base64(HERO_IMAGE)

if hero_base64:
    hero_html = (
        f'<div class="hero-banner" '
        f'style="background-image: '
        f'url(&quot;data:image/png;base64,{hero_base64}&quot;);">'
        f'<div class="hero-overlay">'
        f'<div class="hero-label">MBA Thesis Prototype</div>'
        f'<div class="hero-title">'
        f'Tokyo Disney<br/>Review Intelligence'
        f'</div>'
        f'<div class="hero-subtitle">'
        f'Evidence-based customer review analysis '
        f'for management decision support'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    st.markdown(
        hero_html,
        unsafe_allow_html=True,
    )
else:
    st.error(
        "Hero image not found at "
        "assets/tokyo_disney_ai_hero.png"
    )


# -----------------------------
# Analysis controls
# -----------------------------
try:
    metadata = load_metadata()
except requests.RequestException:
    metadata = {
        "total_reviews": 0,
        "markets": [],
        "min_rating": 1,
        "max_rating": 5,
        "min_date": "2023-01-01",
        "max_date": "2025-12-31",
        "evidence_count_options": [3, 5, 10],
    }
    st.warning(
        "Live filter metadata is unavailable. "
        "Start the API, then refresh this page."
    )

market_label_to_code = {
    f"{item['label']} ({item['count']:,})": item["code"]
    for item in metadata["markets"]
}

with st.container(border=True):
    st.subheader("Business Question")

    selected_example = st.selectbox(
        "Example questions",
        options=EXAMPLE_QUESTIONS,
        help="Choose an example or edit the question below.",
    )

    question = st.text_area(
        "Ask any question about the customer reviews",
        value=selected_example,
        height=100,
        placeholder="Example: What do visitors say about food prices?",
    )

    st.caption(
        f"Searches {metadata['total_reviews']:,} indexed reviews. "
        "Filters are optional; no selection means all reviews."
    )

    control1, control2, control3, control4 = st.columns(
        [1.35, 1.1, 1.0, 0.9],
        gap="medium",
    )

    with control1:
        selected_market_labels = st.multiselect(
            "Markets",
            options=list(market_label_to_code),
            placeholder="All markets",
        )

    with control2:
        rating_range = st.slider(
            "Rating range",
            min_value=int(metadata["min_rating"]),
            max_value=int(metadata["max_rating"]),
            value=(
                int(metadata["min_rating"]),
                int(metadata["max_rating"]),
            ),
        )

    with control3:
        evidence_count = st.selectbox(
            "Evidence reviews",
            options=metadata["evidence_count_options"],
            index=1,
        )

    with control4:
        use_date_filter = st.checkbox(
            "Filter by date",
            value=False,
        )

    selected_dates = None

    if use_date_filter:
        from datetime import date

        selected_dates = st.date_input(
            "Review date range",
            value=(
                date.fromisoformat(metadata["min_date"]),
                date.fromisoformat(metadata["max_date"]),
            ),
            min_value=date.fromisoformat(metadata["min_date"]),
            max_value=date.fromisoformat(metadata["max_date"]),
        )

    analyze_clicked = st.button(
        "Analyze Reviews",
        type="primary",
        use_container_width=True,
        disabled=not question.strip(),
    )


# -----------------------------
# API request and results
# -----------------------------
if analyze_clicked:
    selected_regions = [
        market_label_to_code[label]
        for label in selected_market_labels
    ]
    date_from = None
    date_to = None

    if selected_dates and len(selected_dates) == 2:
        date_from = selected_dates[0].isoformat()
        date_to = selected_dates[1].isoformat()

    payload = {
        "query": question.strip(),
        "regions": selected_regions,
        "min_rating": rating_range[0],
        "max_rating": rating_range[1],
        "date_from": date_from,
        "date_to": date_to,
        "top_k": evidence_count,
    }

    try:
        with st.spinner(
            "AI is analyzing customer reviews..."
        ):
            response = requests.post(
                API_URL,
                json=payload,
                timeout=180,
            )

            response.raise_for_status()
            result = response.json()

        answer = result.get(
            "answer",
            "No management summary was generated.",
        )

        evidence = result.get("evidence", [])
        applied_filters = result.get("filters", {})

        with st.spinner(
            "Translating supporting reviews into English..."
        ):
            english_translations = (
                translate_reviews_to_english(evidence)
            )

        ratings = [
            float(item["rating"])
            for item in evidence
            if isinstance(item.get("rating"), (int, float))
        ]

        average_rating = (
            sum(ratings) / len(ratings)
            if ratings
            else None
        )

        left_column, right_column = st.columns(
            [1.05, 1],
            gap="medium",
        )

        with left_column:
            with st.container(border=True):
                st.subheader("Executive Summary")
                st.write(answer)

                applied_markets = applied_filters.get("regions") or [
                    "All markets"
                ]
                st.caption(
                    "Applied filters — "
                    f"Markets: {', '.join(applied_markets)} · "
                    f"Rating: {rating_range[0]}–{rating_range[1]} · "
                    f"Dates: {date_from or 'All'} to {date_to or 'All'}"
                )

                metric1, metric2, metric3 = st.columns(3)

                metric1.metric(
                    "Reviews Retrieved",
                    len(evidence),
                )

                metric2.metric(
                    "Supporting Evidence",
                    len(evidence),
                )

                metric3.metric(
                    "Average Rating",
                    (
                        f"{average_rating:.1f} / 5"
                        if average_rating is not None
                        else "N/A"
                    ),
                )

        with right_column:
            with st.container(border=True):
                st.subheader(
                    "Supporting Customer Reviews"
                )

                if not evidence:
                    st.info(
                        "No matching reviews were found "
                        "for the selected filters."
                    )

                for index, item in enumerate(evidence, start=1):
                    review_id = safe_text(
                        item.get("review_id", "Unknown")
                    )
                    region = safe_text(
                        item.get("region", "Unknown")
                    )
                    rating = item.get("rating")
                    review_date = safe_text(
                        item.get(
                            "review_date",
                            "Unknown",
                        )
                    )
                    translated_text = safe_text(
                        english_translations[index - 1]
                    )
                    original_text = safe_text(
                        item.get("text", "")
                    )
                    stars = format_stars(rating)

                    review_html = (
                        f'<div class="review-card">'
                        f'<div class="review-heading">'
                        f'<span>{index}. {review_id}</span>'
                        f'<span class="review-stars">{stars}</span>'
                        f'</div>'
                        f'<div class="review-meta">'
                        f'Market: {region} · '
                        f'Rating: {safe_text(rating)}/5 · '
                        f'Date: {review_date}'
                        f'</div>'
                        f'<div class="review-text">'
                        f'<strong>English Translation</strong><br>'
                        f'{translated_text}'
                        f'<br><br><strong>Original Review</strong><br>'
                        f'{original_text}'
                        f'</div>'
                        f'</div>'
                    )

                    expander_label = (
                        f"Evidence {index} · "
                        f"{item.get('review_id', 'Unknown')} · {stars}"
                    )

                    with st.expander(
                        expander_label,
                        expanded=index == 1,
                    ):
                        st.html(review_html)

        with st.container(border=True):
            st.subheader("Technical Details")

            tech1, tech2, tech3, tech4 = st.columns(4)

            with tech1:
                st.markdown(
                    """
                    <div class="tech-item">
                        <div class="tech-title">
                            Hybrid Retrieval
                        </div>
                        <div class="tech-description">
                            Dense and sparse retrieval
                            combined with RRF
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with tech2:
                st.markdown(
                    """
                    <div class="tech-item">
                        <div class="tech-title">
                            Reranking
                        </div>
                        <div class="tech-description">
                            BGE cross-encoder reranker
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with tech3:
                st.markdown(
                    """
                    <div class="tech-item">
                        <div class="tech-title">
                            Language Model
                        </div>
                        <div class="tech-description">
                            Gemini evidence-based
                            answer generation
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with tech4:
                st.markdown(
                    """
                    <div class="tech-item">
                        <div class="tech-title">
                            Vector Database
                        </div>
                        <div class="tech-description">
                            Qdrant review storage
                            and metadata filtering
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    except requests.exceptions.ConnectionError:
        st.error(
            "The analysis API is not running. "
            "Start the FastAPI server and try again."
        )

    except requests.exceptions.Timeout:
        st.error(
            "The analysis request took too long. "
            "Please try again."
        )

    except requests.exceptions.HTTPError:
        st.error(
            f"The API returned an error: "
            f"{response.status_code}"
        )
        st.code(response.text)

    except Exception as error:
        st.error(
            f"Unexpected error: {error}"
        )
