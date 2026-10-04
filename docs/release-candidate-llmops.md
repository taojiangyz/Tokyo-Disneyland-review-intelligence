# LLMOps and answer-quality release candidate — 2026-10-04

This update makes the multilingual review-analysis workflow measurable and easier to audit. It adds Gemini attempt tracing, usage/cost summaries, stricter regression checks, evidence-focused generation, and reversible exclusion of a confirmed out-of-domain review. It is proposed in PR #8; it has not been merged into main.

## Delivered

- Correlated request IDs across API and UI translation; per-attempt status, model, prompt version, token usage and latency. Content-free local JSONL logs distinguish unknown usage from zero.
- Versioned model prices and estimated standard paid cost; actual billed amounts remain unknown. Free-tier configuration is a declaration, not account verification.
- Explicit generation statuses and citation-ID checks. Empty or malformed translation output can trigger fallback rather than silently pass.
- v3-topic-focused generation, plus a separately versioned deterministic presentation policy for localized scope labels and ranking limitations.
- A reversible review-ID quarantine applied before retrieval limits. 2,049 indexed source records remain intact; 2,048 are eligible after excluding one confirmed Mount Fuji review.
- Dense Top 5 remains the default. Hybrid and reranking remain experimental alternatives.

## Validation and provenance

- 39 automated tests passed after the presentation-policy change.
- Before that presentation change, a full API run of 26 development cases completed: 22 successful Gemini calls, four no-evidence skips, and 26/26 structural checks. Total reported usage was 24,170 tokens; generated-answer API P50/P95 was 1.79/2.27 seconds in that single local run. These are not semantic accuracy or capacity claims.
- The final presentation policy was replayed offline on those 26 saved answers. Citation sequences and four no-evidence responses were preserved. No fresh full live run of the final presentation stage or Docker/browser deployment was performed.
- The user reviewed eight earlier v2 answers: language 8 passed; evidence support 7 passed/1 partial; answering the question 6 passed/1 partial/1 unanswered; insufficient-evidence handling 8 passed. These labels do not grade later regenerated v3 answers.
- Sixteen user relevance labels supplement the original 241, yielding 257 query/review judgments across 15 existing questions. The original label file is preserved; the dated merged file contains IDs and grades only, not review text or user notes.
- Re-scoring the saved pre-quarantine rankings with the same expanded labels gave dense vs dense-20-rerank nDCG@5 0.771/0.762, Recall@5 0.345/0.320 and MRR@5 0.850/0.883. Recall uses the judged pool, not exhaustive corpus relevance. Reranking added about 2.27 seconds on average. The small development set does not establish statistical significance.

## Reproduce

```bash
make test
# Requires the authorized private dataset/index, a configured Gemini key and running API.
python scripts/run_regression.py --cases evals/regression_cases_v3.jsonl --output evals/results/v3-current.json
python scripts/summarize_llm_usage.py
```

`evals/annotations/human_verified_relevance_labels_2026-10-04.csv` is the expanded label snapshot. Rankings measured before quarantine must not be conflated with fresh retrieval using the current filter. Raw responses, reviews, local index and telemetry output are not included in the public source tree.

## Known limitations

After integration with main, this portfolio application includes evidence RAG and a bounded tool-using Agent. It is not an unrestricted autonomous system or production service. Evidence relevance varies with question wording; the original dining-price question still retrieves weak evidence. Some source comments mention guides without enough context to establish their domain. A ranking caveat cannot repair unsupported claims in the body, and fixed label localization does not guarantee whole-answer language quality. Fine-grained citation attribution, generated typos and unsupported causal wording still require review. Ranking detection is rule-based and may miss paraphrases.

Main supplies demo password/token checks and rate limits; enterprise authentication and multi-tenant isolation are not implemented. Qdrant local mode is single-process. Final UI/Docker verification and fresh held-out human answer evaluation remain outstanding. The repository does not distribute private source reviews, so cloning alone does not reproduce the private-data results.

## Main integration — 2026-10-05

Preserves main's Agent tools, optional function-calling planner, OpenAI-compatible provider, demo controls, CPU Docker setup and prompt registry. The review prompt is now `prompts/review_answer_v3.txt`, registry version `3.0.0`; Agent/planner templates retain their versions. Review presentation supports kana-bearing Japanese queries; kanji-only detection remains ambiguous.

The presentation policy applies to review Q&A, not Agent analytical answers using aggregate statistics. Gemini text attempts, including Agent answer text, use the telemetry wrapper. Native function-call planning and OpenAI-compatible requests are not covered by its per-attempt cost ledger; existing provider traces remain available. Request IDs propagate into Gemini text logs, and tracking fields are isolated by execution context. Topic aggregation applies quarantine consistently with review statistics and retrieval.

Historical live-model results predate integration and are not integrated results. No new live provider calls or Docker/browser validation occurred during conflict resolution.

Integrated validation: 95 automated tests passed; structural Agent evaluation passed 40/40 with fixtures (not live LLM accuracy).
