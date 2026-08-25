# Two-to-three-minute demo script

## 0:00–0:20 — Problem

“This project is Aladdin, a multilingual review intelligence assistant for Tokyo Disney. It helps a manager analyze 2,049 reviews using open-ended questions instead of relying on a fixed dashboard, while showing the original evidence behind every answer.”

Show the title, indexed-review count, free-form question field, and filters.

## 0:20–1:10 — Agent workflow

Select Agent Analysis and ask in Japanese: “韓国と香港の来園者の主な不満を比較してください。”

Leave the market and rating filters unselected. Point out:

- automatic market inference and the low-rating default;
- the selected `market_comparison` task;
- deterministic review and topic statistics calculated over the matching segment;
- the bounded, auditable tool trace;
- the generated executive summary;
- expandable source reviews;
- review ID, market, rating, date, translation, and original text.

Say: “Gemini does not read all 2,049 reviews. Code calculates the full-segment statistics, retrieval selects five qualitative examples, and Gemini receives only those tool outputs and evidence. Returned citations are checked against the evidence set.”

## 1:10–1:35 — Dynamic analysis

Change the market to Korea or China and restrict ratings to 1–3. Rerun either the same question or “What are the main complaints in low-rated reviews?”

Say: “Filters are applied during retrieval, not after generation, so the evidence and answer represent the selected customer segment.”

## 1:35–2:15 — Evaluation

Show the README evaluation table.

Say: “I created 241 human relevance judgments across 15 questions and compared dense, hybrid, and reranked retrieval. Dense had the best Top-5 recall and ranking quality for the actual five-evidence UI, so it is the interactive default. I also maintain 40 multilingual Agent cases for routing, inferred filters, tool plans, deterministic statistics, citation containment, and failure behavior.”

## 2:10–2:35 — Reliability

Say: “If no reviews match, generation is skipped. If Gemini is unavailable, the system keeps the retrieved evidence visible and returns a degraded status instead of failing completely. Every API request also has a correlation ID and structured timing logs.”

Optionally demonstrate the degraded state only after recording a successful main flow.

## 2:35–2:55 — Close

“This project demonstrates the full applied-AI workflow: data ingestion, retrieval, grounded generation, human evaluation, Agent evaluation, observability, testing, containerization, and controlled external demonstration. Permanent cloud infrastructure and multi-tenant authentication remain production extensions.”

## Recording checklist

- Run `make demo-up` before a remote interactive interview, or start FastAPI and Streamlit locally before recording.
- Confirm Gemini works with one test question.
- Use browser zoom that keeps evidence and metrics readable.
- Hide terminals, `.env`, API keys, and personal notifications.
- Record at 1080p and keep the final video under three minutes.
- Do not claim a public cloud deployment until it has actually been verified.
