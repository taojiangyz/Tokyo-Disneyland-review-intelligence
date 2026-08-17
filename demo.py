import base64
from pathlib import Path

import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000/api/v1/analyze"

DISPLAY_QUESTION = (
    "What are the main complaints about waiting time "
    "and crowding at Tokyo Disney?"
)

# Extra instruction is sent to Gemini but not displayed on the page.
API_QUERY = (
    f"{DISPLAY_QUESTION} "
    "Please provide the complete answer in English."
)

HERO_IMAGE = Path("assets/tokyo_disney_ai_hero.png")


def image_to_base64(image_path: Path) -> str:
    """Convert the local hero image into a browser-safe data URL."""
    if not image_path.exists():
        return ""

    return base64.b64encode(
        image_path.read_bytes()
    ).decode("utf-8")


st.set_page_config(
    page_title="Tokyo Disney Review Intelligence Prototype",
    page_icon="🏰",
    layout="wide",
)


# ---------- Page styling ----------
st.markdown(
    """
    <style>
    .stApp {
        background: #f5f7fb;
    }

    .block-container {
        max-width: 1440px;
        padding-top: 0.6rem;
        padding-bottom: 3rem;
    }

    .hero-banner {
        position: relative;
        height: 360px;
        border-radius: 16px;
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        overflow: hidden;
        margin-bottom: 22px;
    }

    .hero-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 46%;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 34px 42px;
        background: linear-gradient(
            90deg,
            rgba(4, 19, 71, 0.96) 0%,
            rgba(4, 19, 71, 0.76) 68%,
            rgba(4, 19, 71, 0) 100%
        );
    }

    .hero-label {
        width: fit-content;
        margin-bottom: 14px;
        padding: 6px 12px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.14);
        border: 1px solid rgba(255, 255, 255, 0.28);
        color: white;
        font-size: 13px;
        font-weight: 700;
    }

    .hero-title {
        color: white;
        font-size: 42px;
        line-height: 1.08;
        font-weight: 750;
        letter-spacing: -0.02em;
        margin-bottom: 16px;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.28);
    }

    .hero-subtitle {
        max-width: 440px;
        color: rgba(255, 255, 255, 0.92);
        font-size: 18px;
        line-height: 1.5;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.98);
        border: 1px solid #e2e7f0;
        border-radius: 16px;
        padding: 10px;
        box-shadow: 0 4px 18px rgba(27, 47, 94, 0.06);
    }

    div[data-testid="stMetric"] {
        background: #f7f9ff;
        border: 1px solid #e4e9f4;
        border-radius: 14px;
        padding: 14px 16px;
    }

    div[data-testid="stMetricLabel"] {
        font-weight: 600;
    }

    .stButton > button {
        min-height: 46px;
        border-radius: 8px;
        font-weight: 600;
    }

    h2, h3 {
        color: #12398f;
    }

    .review-meta {
        color: #667085;
        font-size: 0.9rem;
        margin-bottom: 8px;
    }

    .review-card {
        border: 1px solid #e3e8f1;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 10px;
        background: #ffffff;
    }

    .technical-item {
        padding: 8px 14px;
        min-height: 70px;
    }

    .technical-title {
        font-weight: 700;
        color: #163d9f;
        margin-bottom: 4px;
    }

    .technical-text {
        color: #4b5563;
        font-size: 0.92rem;
    }

    div[data-testid="stInfo"] {
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Hero banner ----------
hero_base64 = image_to_base64(HERO_IMAGE)

if hero_base64:
    st.markdown(
        f"""
        <div
            class="hero-banner"
            style="
                background-image:
                url('data:image/png;base64,{hero_base64}');
            "
        >
            <div class="hero-overlay">
                <div class="hero-label">
                    MBA Thesis Prototype
                </div>

                <div class="hero-title">
                    Tokyo Disney<br>
                    Review Intelligence
                </div>

                <div class="hero-subtitle">
                    Evidence-based customer review analysis
                    for management decision support
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.warning(
        "Hero image not found. Please place it at "
        "assets/tokyo_disney_ai_hero.png"
    )


# ---------- Analysis controls ----------
with st.container(border=True):
    st.subheader("Business Question")
    st.info(DISPLAY_QUESTION)

    col1, col2, col3, col4, col5 = st.columns(
        [1.2, 1.1, 1.3, 1.0, 1.2]
    )

    with col1:
        market = st.selectbox(
            "Market",
            options=["China", "Hong Kong", "Korea"],
            index=0,
        )

    with col2:
        review_year = st.selectbox(
            "Review Year",
            options=[2025, 2024, 2023],
            index=0,
        )

    with col3:
        maximum_rating = st.selectbox(
            "Maximum Rating",
            options=[
                "3 stars and below",
                "2 stars and below",
                "1 star only",
                "All reviews",
            ],
            index=0,
        )

    with col4:
        evidence_count = st.selectbox(
            "Evidence Reviews",
            options=[3, 5, 10],
            index=1,
        )

    with col5:
        st.write("")
        st.write("")

        analyze_clicked = st.button(
            "Analyze Reviews",
            type="primary",
            use_container_width=True,
        )


region_map = {
    "China": "CN",
    "Hong Kong": "HK",
    "Korea": "KR",
}

rating_map = {
    "3 stars and below": 3,
    "2 stars and below": 2,
    "1 star only": 1,
    "All reviews": None,
}


# ---------- API request ----------
if analyze_clicked:
    payload = {
        "query": API_QUERY,
        "region": region_map[market],
        "min_rating": None,
        "max_rating": rating_map[maximum_rating],
        "date_from": f"{review_year}-01-01",
        "date_to": f"{review_year}-12-31",
        "top_k": evidence_count,
    }

    try:
        with st.spinner("Analyzing customer reviews..."):
            response = requests.post(
                API_URL,
                json=payload,
                timeout=120,
            )

            response.raise_for_status()
            result = response.json()

        evidence = result.get("evidence", [])
        answer = result.get(
            "answer",
            "No management summary was generated.",
        )

        st.subheader("Executive Summary")

        with st.container(border=True):
            st.write(answer)

        metric1, metric2, metric3, metric4 = st.columns(4)

        metric1.metric(
            "Market",
            market,
        )

        metric2.metric(
            "Review Year",
            str(review_year),
        )

        metric3.metric(
            "Evidence Used",
            len(evidence),
        )

        ratings = [
            item.get("rating")
            for item in evidence
            if isinstance(item.get("rating"), (int, float))
        ]

        average_rating = (
            sum(ratings) / len(ratings)
            if ratings
            else None
        )

        metric4.metric(
            "Average Rating",
            (
                f"{average_rating:.1f} / 5"
                if average_rating is not None
                else "N/A"
            ),
        )

        st.subheader("Supporting Customer Reviews")

        if not evidence:
            st.info(
                "No matching reviews were found for "
                "the selected filters."
            )

        for index, item in enumerate(evidence, start=1):
            review_id = item.get("review_id", "Unknown")
            region = item.get("region", "Unknown")
            rating = item.get("rating")
            review_date = item.get("review_date", "Unknown")
            text = item.get("text", "")

            with st.container(border=True):
                st.markdown(
                    f"#### Evidence {index}"
                )

                st.caption(
                    f"Review ID: {review_id}  ·  "
                    f"Market: {region}  ·  "
                    f"Rating: {rating}/5  ·  "
                    f"Date: {review_date}"
                )

                st.write(text)

        with st.expander("Technical Details"):
            technical1, technical2, technical3, technical4 = (
                st.columns(4)
            )

            technical1.markdown(
                "**Hybrid Retrieval**  \n"
                "Dense + Sparse + RRF"
            )

            technical2.markdown(
                "**Reranking**  \n"
                "BGE Reranker"
            )

            technical3.markdown(
                "**Language Model**  \n"
                "Gemini"
            )

            technical4.markdown(
                "**Vector Database**  \n"
                "Qdrant"
            )

    except requests.exceptions.ConnectionError:
        st.error(
            "The analysis API is not running. "
            "Please start the FastAPI server first."
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
