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
AGENT_API_URL = f"{API_BASE_URL}/api/v1/agent/analyze"
METADATA_URL = f"{API_BASE_URL}/api/v1/metadata"
HERO_IMAGE = Path("assets/tokyo_disney_ai_hero.png")

COPY = {
    "English": {
        "subtitle": "Evidence-based customer review analysis for management decision support",
        "data_source": "Data source: verified ticket-purchaser reviews from Trip.com/Ctrip.com users in Mainland China, South Korea, and Hong Kong",
        "business_question": "Business Question",
        "analysis_mode": "Analysis mode",
        "rag_mode": "RAG Q&A",
        "agent_mode": "Agent Analysis",
        "agent_trace": "Agent execution trace",
        "agent_task": "Selected task",
        "agent_statistics": "Deterministic statistics",
        "topic_insights": "AI-assisted topic insights",
        "topic_coverage": "Topic labels cover {labeled:,} of {matching:,} matching reviews ({share:.1%}). Treat partial coverage as directional, not conclusive.",
        "topic": "Topic",
        "review_share": "Review share",
        "sentiment_distribution": "Sentiment distribution",
        "topics_unavailable": "Topic labels are not available for this analysis yet.",
        "example_questions": "Example questions",
        "example_help": "Choose an example or edit the question below.",
        "ask": "Ask any question about the customer reviews",
        "placeholder": "Example: What do visitors say about food prices?",
        "search_caption": "Searches {count:,} indexed reviews. Filters are optional; no selection means all reviews.",
        "markets": "Markets",
        "all_markets": "All markets",
        "rating_range": "Rating range",
        "evidence_reviews": "Evidence reviews",
        "filter_date": "Filter by date",
        "date_range": "Review date range",
        "analyze": "Analyze Reviews",
        "analyzing": "AI is analyzing customer reviews...",
        "translating": "Translating supporting reviews into English...",
        "translation_target": "English",
        "translation_unavailable": "English translation is temporarily unavailable.",
        "summary": "Executive Summary",
        "no_summary": "No management summary was generated.",
        "degraded_answer": "Answer generation is temporarily unavailable. The retrieved supporting reviews are still shown below.",
        "no_evidence_answer": "No reviews matched the selected filters, so there is not enough evidence to answer this question.",
        "applied_filters": "Applied filters",
        "rating": "Rating",
        "dates": "Dates",
        "all": "All",
        "retrieved": "Reviews Retrieved",
        "supporting": "Supporting Evidence",
        "average": "Average Rating",
        "reviews": "Supporting Customer Reviews",
        "no_reviews": "No matching reviews were found for the selected filters.",
        "market": "Market",
        "date": "Date",
        "translation": "English Translation",
        "original": "Original Review",
        "evidence": "Evidence",
        "technical": "Technical Details",
        "api_unavailable": "Live filter metadata is unavailable. Start the API, then refresh this page.",
        "connection_error": "The analysis API is not running. Start the FastAPI server and try again.",
        "timeout_error": "The analysis request took too long. Please try again.",
        "api_error": "The API returned an error",
        "unexpected_error": "Unexpected error",
    },
    "日本語": {
        "subtitle": "経営判断を支援する、根拠に基づいたカスタマーレビュー分析",
        "data_source": "データ出典：Trip.com/Ctrip.com の中国本土・韓国・香港の実購入者レビュー",
        "business_question": "分析したい質問",
        "analysis_mode": "分析モード",
        "rag_mode": "RAG Q&A",
        "agent_mode": "Agent分析",
        "agent_trace": "Agent実行トレース",
        "agent_task": "選択されたTask",
        "agent_statistics": "決定論的な統計",
        "topic_insights": "AI支援トピック分析",
        "topic_coverage": "該当レビュー{matching:,}件のうち{labeled:,}件にトピックラベルがあります（{share:.1%}）。一部のみの場合は参考傾向であり、最終結論ではありません。",
        "topic": "トピック",
        "review_share": "レビュー比率",
        "sentiment_distribution": "感情分布",
        "topics_unavailable": "この分析で利用できるトピックラベルはまだありません。",
        "example_questions": "質問例",
        "example_help": "質問例を選ぶか、下の入力欄で自由に編集してください。",
        "ask": "カスタマーレビューについて自由に質問してください",
        "placeholder": "例：食事の価格について、来園者はどのように評価していますか？",
        "search_caption": "{count:,}件のレビューを検索します。フィルターは任意で、未選択の場合は全件が対象です。",
        "markets": "市場",
        "all_markets": "すべての市場",
        "rating_range": "評価範囲",
        "evidence_reviews": "表示する根拠レビュー数",
        "filter_date": "日付で絞り込む",
        "date_range": "レビュー投稿日",
        "analyze": "レビューを分析",
        "analyzing": "AIがカスタマーレビューを分析しています…",
        "translating": "根拠レビューを日本語に翻訳しています…",
        "translation_target": "Japanese",
        "translation_unavailable": "日本語訳を一時的に利用できません。",
        "summary": "分析サマリー",
        "no_summary": "分析サマリーは生成されませんでした。",
        "degraded_answer": "回答生成を一時的に利用できません。取得できた根拠レビューは引き続き確認できます。",
        "no_evidence_answer": "選択した条件に一致するレビューがないため、この質問に回答するための根拠が不足しています。",
        "applied_filters": "適用フィルター",
        "rating": "評価",
        "dates": "期間",
        "all": "すべて",
        "retrieved": "取得レビュー",
        "supporting": "根拠レビュー",
        "average": "平均評価",
        "reviews": "根拠となるカスタマーレビュー",
        "no_reviews": "選択した条件に一致するレビューはありません。",
        "market": "市場",
        "date": "投稿日",
        "translation": "日本語訳",
        "original": "原文",
        "evidence": "根拠",
        "technical": "技術構成",
        "api_unavailable": "フィルター情報を取得できません。APIを起動してページを更新してください。",
        "connection_error": "分析APIが起動していません。FastAPIを起動して再試行してください。",
        "timeout_error": "分析に時間がかかりすぎました。もう一度お試しください。",
        "api_error": "APIエラー",
        "unexpected_error": "予期しないエラー",
    },
}

EXAMPLE_QUESTIONS = {
    "English": [
        "What are the main complaints about waiting time and crowding at Tokyo Disney?",
        "What do visitors say about staff service?",
        "What are the main complaints in low-rated reviews?",
        "What do visitors like most about their park experience?",
    ],
    "日本語": [
        "東京ディズニーランドの待ち時間と混雑に関する主な不満は何ですか？",
        "スタッフのサービスについて、来園者はどのように評価していますか？",
        "低評価レビューに多い不満は何ですか？",
        "来園者がパーク体験で最も高く評価している点は何ですか？",
    ],
}


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



def translate_reviews(
    evidence: list[dict],
    target_language: str,
    unavailable_message: str,
) -> list[str]:
    """Translate the visible evidence reviews in one Gemini request."""
    visible_items = evidence

    if not visible_items:
        return []

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL")
    fallback_model_name = os.getenv(
        "GEMINI_FALLBACK_MODEL",
        "gemini-3.5-flash-lite",
    )

    if not api_key or not model_name:
        return [
            unavailable_message
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
Translate the following customer reviews into natural {target_language}.

Requirements:
1. Preserve the original meaning.
2. Do not summarize or add information.
3. Return only a valid JSON array of {target_language} strings.
4. Keep the translations in exactly the same order.
5. Return exactly {len(visible_items)} strings.

Reviews:
{numbered_reviews}
"""

    try:
        client = genai.Client(api_key=api_key)

        response = None
        last_error = None
        for candidate_model in dict.fromkeys(
            [model_name, fallback_model_name]
        ):
            try:
                response = client.models.generate_content(
                    model=candidate_model,
                    contents=prompt,
                )
                break
            except Exception as exc:
                last_error = exc

        if response is None:
            assert last_error is not None
            raise last_error

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
            unavailable_message
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

    .hero-source {
        max-width: 680px;
        margin-top: 15px;
        color: rgba(255, 255, 255, 0.82);
        font-size: 14px;
        line-height: 1.45;
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

language_column, _ = st.columns([1, 4])
with language_column:
    language = st.radio(
        "Language / 言語",
        options=["English", "日本語"],
        horizontal=True,
    )
t = COPY[language]


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
        f'<div class="hero-title">'
        f'Tokyo Disney<br/>Review Intelligence'
        f'</div>'
        f'<div class="hero-subtitle">'
        f'{t["subtitle"]}'
        f'</div>'
        f'<div class="hero-source">'
        f'{t["data_source"]}'
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
        t["api_unavailable"]
    )

market_names_ja = {
    "CN": "中国本土",
    "HK": "香港",
    "KR": "韓国",
}
market_label_to_code = {}
for item in metadata["markets"]:
    label = (
        market_names_ja.get(item["code"], item["label"])
        if language == "日本語"
        else item["label"]
    )
    market_label_to_code[f"{label} ({item['count']:,})"] = item["code"]

with st.container(border=True):
    st.subheader(t["business_question"])

    analysis_mode = st.radio(
        t["analysis_mode"],
        options=[t["rag_mode"], t["agent_mode"]],
        horizontal=True,
        help=(
            "RAG answers a focused question. Agent Analysis selects and "
            "executes retrieval, statistics, verification, and generation tools."
            if language == "English"
            else "RAGは単一質問に回答し、Agent分析は検索・統計・検証・生成Toolを選択して実行します。"
        ),
    )

    selected_example = st.selectbox(
        t["example_questions"],
        options=EXAMPLE_QUESTIONS[language],
        help=t["example_help"],
        key=f"examples-{language}",
    )

    question = st.text_area(
        t["ask"],
        value=selected_example,
        height=100,
        placeholder=t["placeholder"],
        key=f"question-{language}",
    )

    st.caption(
        t["search_caption"].format(count=metadata["total_reviews"])
    )

    control1, control2, control3, control4 = st.columns(
        [1.35, 1.1, 1.0, 0.9],
        gap="medium",
    )

    with control1:
        selected_market_labels = st.multiselect(
            t["markets"],
            options=list(market_label_to_code),
            placeholder=t["all_markets"],
        )

    with control2:
        rating_range = st.slider(
            t["rating_range"],
            min_value=int(metadata["min_rating"]),
            max_value=int(metadata["max_rating"]),
            value=(
                int(metadata["min_rating"]),
                int(metadata["max_rating"]),
            ),
        )

    with control3:
        evidence_count = st.selectbox(
            t["evidence_reviews"],
            options=metadata["evidence_count_options"],
            index=1,
        )

    with control4:
        use_date_filter = st.checkbox(
            t["filter_date"],
            value=False,
        )

    selected_dates = None

    if use_date_filter:
        from datetime import date

        selected_dates = st.date_input(
            t["date_range"],
            value=(
                date.fromisoformat(metadata["min_date"]),
                date.fromisoformat(metadata["max_date"]),
            ),
            min_value=date.fromisoformat(metadata["min_date"]),
            max_value=date.fromisoformat(metadata["max_date"]),
        )

    analyze_clicked = st.button(
        t["analyze"],
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
    request_url = API_URL
    if analysis_mode == t["agent_mode"]:
        payload["evidence_limit"] = payload.pop("top_k")
        if rating_range == (
            int(metadata["min_rating"]),
            int(metadata["max_rating"]),
        ):
            payload["min_rating"] = None
            payload["max_rating"] = None
        request_url = AGENT_API_URL

    try:
        with st.spinner(
            t["analyzing"]
        ):
            response = requests.post(
                request_url,
                json=payload,
                timeout=180,
            )

            response.raise_for_status()
            result = response.json()

        answer = result.get(
            "answer",
            t["no_summary"],
        )
        generation_status = (
            result.get("trace", {})
            .get("generation", {})
            .get("status")
        )
        if generation_status == "degraded":
            answer = t["degraded_answer"]
        elif generation_status == "skipped_no_evidence":
            answer = t["no_evidence_answer"]

        evidence = result.get("evidence", [])
        applied_filters = result.get("filters", {})

        if analysis_mode == t["agent_mode"]:
            with st.container(border=True):
                st.subheader(t["agent_trace"])
                st.caption(
                    f"{t['agent_task']}: {result.get('task', 'unknown')}"
                )
                steps = result.get("steps", [])
                if steps:
                    st.dataframe(
                        [
                            {
                                "Step": index,
                                "Tool": step.get("tool"),
                                "Status": step.get("status"),
                                "Summary": step.get("summary"),
                                "ms": step.get("duration_ms"),
                            }
                            for index, step in enumerate(steps, start=1)
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
                statistics = result.get("analytics", {}).get("statistics")
                if statistics:
                    with st.expander(t["agent_statistics"]):
                        st.json(statistics)

                analytics = result.get("analytics", {})
                topic_result = analytics.get("topic_distribution")
                market_topics = analytics.get("topics_by_market")
                if topic_result or market_topics:
                    with st.container(border=True):
                        st.subheader(t["topic_insights"])
                        if topic_result and topic_result.get("available"):
                            labeled = int(topic_result.get("review_count", 0))
                            matching = int(
                                (statistics or {}).get("review_count", labeled)
                            )
                            share = labeled / matching if matching else 0
                            st.caption(
                                t["topic_coverage"].format(
                                    labeled=labeled,
                                    matching=matching,
                                    share=share,
                                )
                            )
                            topic_rows = topic_result.get("topics", [])
                            if topic_rows:
                                st.bar_chart(
                                    topic_rows,
                                    x="topic",
                                    y="review_share",
                                    horizontal=True,
                                )
                                st.dataframe(
                                    [
                                        {
                                            t["topic"]: row.get("topic"),
                                            "Count": row.get("count"),
                                            t["review_share"]: (
                                                f"{float(row.get('review_share', 0)):.1%}"
                                            ),
                                        }
                                        for row in topic_rows
                                    ],
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            sentiments = topic_result.get("sentiments", {})
                            if sentiments:
                                st.caption(t["sentiment_distribution"])
                                st.json(sentiments)
                        elif market_topics and market_topics.get("available"):
                            market_rows = []
                            for market, market_data in market_topics.get(
                                "markets", {}
                            ).items():
                                for row in market_data.get("topics", []):
                                    market_rows.append(
                                        {
                                            t["market"]: market,
                                            t["topic"]: row.get("topic"),
                                            "Count": row.get("count"),
                                            t["review_share"]: (
                                                f"{float(row.get('review_share', 0)):.1%}"
                                            ),
                                        }
                                    )
                            if market_rows:
                                st.dataframe(
                                    market_rows,
                                    use_container_width=True,
                                    hide_index=True,
                                )
                        else:
                            st.info(t["topics_unavailable"])

        with st.spinner(
            t["translating"]
        ):
            review_translations = (
                translate_reviews(
                    evidence,
                    t["translation_target"],
                    t["translation_unavailable"],
                )
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
                st.subheader(t["summary"])
                st.write(answer)

                applied_markets = applied_filters.get("regions") or [
                    t["all_markets"]
                ]
                applied_min_rating = applied_filters.get("min_rating")
                applied_max_rating = applied_filters.get("max_rating")
                applied_rating = (
                    f"{applied_min_rating or t['all']}–"
                    f"{applied_max_rating or t['all']}"
                )
                st.caption(
                    f"{t['applied_filters']} — "
                    f"{t['markets']}: {', '.join(applied_markets)} · "
                    f"{t['rating']}: {applied_rating} · "
                    f"{t['dates']}: {date_from or t['all']} — {date_to or t['all']}"
                )

                metric1, metric2, metric3 = st.columns(3)

                metric1.metric(
                    t["retrieved"],
                    len(evidence),
                )

                metric2.metric(
                    t["supporting"],
                    len(evidence),
                )

                metric3.metric(
                    t["average"],
                    (
                        f"{average_rating:.1f} / 5"
                        if average_rating is not None
                        else "N/A"
                    ),
                )

        with right_column:
            with st.container(border=True):
                st.subheader(
                    t["reviews"]
                )

                if not evidence:
                    st.info(
                        t["no_reviews"]
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
                        review_translations[index - 1]
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
                        f'{t["market"]}: {region} · '
                        f'{t["rating"]}: {safe_text(rating)}/5 · '
                        f'{t["date"]}: {review_date}'
                        f'</div>'
                        f'<div class="review-text">'
                        f'<strong>{t["translation"]}</strong><br>'
                        f'{translated_text}'
                        f'<br><br><strong>{t["original"]}</strong><br>'
                        f'{original_text}'
                        f'</div>'
                        f'</div>'
                    )

                    expander_label = (
                        f"{t['evidence']} {index} · "
                        f"{item.get('review_id', 'Unknown')} · {stars}"
                    )

                    with st.expander(
                        expander_label,
                        expanded=index == 1,
                    ):
                        st.html(review_html)

        with st.container(border=True):
            st.subheader(t["technical"])

            tech_copy = {
                "English": [
                    ("Retrieval", "Evaluation-selected BGE-M3 Dense retrieval"),
                    ("Agent Tools", "Statistics, search, and evidence verification"),
                    ("Language Model", "Gemini grounded explanation and fallback"),
                    ("Vector Database", "Qdrant review storage and metadata filtering"),
                ],
                "日本語": [
                    ("検索", "評価で選定したBGE-M3 Dense検索"),
                    ("Agent Tool", "統計・検索・Evidence検証"),
                    ("言語モデル", "Geminiによる根拠説明とFallback"),
                    ("ベクトルDB", "Qdrantによるレビュー保存とメタデータ絞り込み"),
                ],
            }
            tech_columns = st.columns(4)
            for column, (title, description) in zip(
                tech_columns,
                tech_copy[language],
            ):
                with column:
                    st.markdown(
                        f"""
                        <div class="tech-item">
                            <div class="tech-title">{title}</div>
                            <div class="tech-description">{description}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    except requests.exceptions.ConnectionError:
        st.error(t["connection_error"])

    except requests.exceptions.Timeout:
        st.error(t["timeout_error"])

    except requests.exceptions.HTTPError:
        st.error(
            f"{t['api_error']}: {response.status_code}"
        )
        st.code(response.text)

    except Exception as error:
        st.error(
            f"{t['unexpected_error']}: {error}"
        )
