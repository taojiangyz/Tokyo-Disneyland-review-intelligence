# Two-to-three-minute demo script

## 0:00–0:20 — Problem

“This project is Aladdin, a multilingual review intelligence assistant for Tokyo Disney. It helps a manager analyze 2,049 reviews using open-ended questions instead of relying on a fixed dashboard, while showing the original evidence behind every answer.”

Show the title, indexed-review count, free-form question field, and filters.

## 0:20–1:05 — Core workflow

Ask: “What are the main complaints about waiting time and crowding at Tokyo Disney?”

Keep all markets selected and use five evidence reviews. Point out:

- the generated executive summary;
- applied filters and evidence count;
- expandable source reviews;
- review ID, market, rating, date, translation, and original text.

Say: “The model is instructed to answer only from these retrieved reviews, and returned citations are checked against the evidence set.”

## 1:05–1:30 — Dynamic analysis

Change the market to Korea or China and restrict ratings to 1–3. Rerun either the same question or “What are the main complaints in low-rated reviews?”

Say: “Filters are applied during retrieval, not after generation, so the evidence and answer represent the selected customer segment.”

## 1:30–2:10 — Evaluation

Show the README evaluation table.

Say: “I created 241 human relevance judgments across 15 questions and compared dense, hybrid, and reranked retrieval. The 20-candidate reranker had the best nDCG, but took about 6.2 seconds on CPU. Dense retrieval was almost as accurate and much faster, so I recommend it as the interactive default.”

## 2:10–2:35 — Reliability

Say: “If no reviews match, generation is skipped. If Gemini is unavailable, the system keeps the retrieved evidence visible and returns a degraded status instead of failing completely. Every API request also has a correlation ID and structured timing logs.”

Optionally demonstrate the degraded state only after recording a successful main flow.

## 2:35–2:55 — Close

“This project demonstrates the full applied-AI workflow: data ingestion, retrieval, grounded generation, human evaluation, observability, testing, and containerization. The next production steps would be expanding the evaluation set, using server Qdrant, adding authentication, and deploying to cloud infrastructure.”

## Recording checklist

- Start FastAPI and Streamlit before recording.
- Confirm Gemini works with one test question.
- Use browser zoom that keeps evidence and metrics readable.
- Hide terminals, `.env`, API keys, and personal notifications.
- Record at 1080p and keep the final video under three minutes.
- Do not claim a public cloud deployment until it has actually been verified.
