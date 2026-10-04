# Real API regression and qualitative review — 2026-10-04

## Protocol

The existing 20 regression questions were run sequentially through the local API
using the configured gemini-3.5-flash-lite model. A dense retrieval warm-up preceded
the run and did not call Gemini; cases were spaced by five seconds. The default
Dense Top 5 retrieval, existing index and original v1 generation prompt were used.
All requests were local; retrieved evidence was sent to the configured Gemini API
as in normal operation. Source hashes and baseline metadata were saved locally.

Private responses, source text and detailed review records remain in Git-ignored
`evals/results/2026-10-04-live/`. Only aggregate findings are published here.
This is a development regression, not a held-out production benchmark.

## Measured results (baseline v1)

- 20 API responses: 18 completed generations, two no-evidence skips.
- 18 model calls completed; zero application fallback attempts in this run.
- Reported input: 10,472 tokens; output: 4,553; total: 15,025.
- Estimated standard paid price: **USD 0.0145241**, based on the versioned rate
  configuration. This is not actual spending; actual billing remains unverified.
- SDK call latency (18 calls): P50 **1,502.65 ms**, P95 **1,795.13 ms**.
- API pipeline latency (20 responses, including skips): P50 **1,676.64 ms**,
  P95 **2,036.93 ms**.
- API pipeline latency for the 18 generated responses: P50 **1,693.18 ms**,
  P95 **2,062.27 ms**.

These values exclude UI translation, browser rendering, between-case pauses and
warm-up. They must not be presented as whole-product cost or a production SLA.
Thought/cache fields were omitted in these responses, while prompt + output
reconciled exactly to total. Missing fields remain null in telemetry.

## Scorer correction

The original citation checker treated `[id1, id2]` as one unknown ID. The initial
score was 4/20, with 16 false citation failures. A bounded fix splits grouped IDs
and still rejects unknown IDs. Re-scoring the **same saved responses**, without
another model call, yielded 20/20 structural checks. The original report is retained.
This is a corrected structural regression score, **not 100% answer accuracy**.

## Qualitative findings

Codex read all 20 responses against their retrieved evidence. This is an AI-assisted
qualitative review, not independent human adjudication or a calibrated quality score.

- Eight of 11 English questions with generated answers received Chinese or Korean
  answers. The static Chinese no-evidence case also returned English.
- The food-price answer interpreted a vague statement about lower prices as evidence
  that dining prices were cheaper. The cited review did not identify that category.
- Questions about "most" or "最常" need an explicit statement that retrieved Top-K
  samples cannot establish population frequency or a most-common ranking.
- A date-filtered praise answer used a review about a driver/tour guide. Its content
  was cited correctly, but domain relevance needs human checking before treating it
  as evidence about park operations.

## Changes and limited follow-up

The v2-language-evidence prompt explicitly sets English/Chinese output based on the
question, warns against inferring a price category from vague evidence, and states
the limits of Top-K frequency claims. The no-evidence Chinese response is localized.
The model name is request-local; usage tracking continues through these changes.

Four saved cases were tested directly with the new generation service: English
queues, Chinese dining prices, Chinese Hong Kong frequency, and English Korean
visitor experience. The two English answers were in English; the dining answer
acknowledged insufficient price evidence, and the Hong Kong answer explicitly
rejected inferring population frequency. These checks used saved evidence and a
simplified evidence serialization; they are targeted checks, not a full matched A/B
experiment. At this targeted-check stage, no full-suite language/semantic conclusion was available.
Small attribution/scope details still merit independent human review.

This follow-up is stored separately in `evals/results/2026-10-04-targeted/`.
Its costs are excluded from the baseline totals above. A subsequent
[full v2 rerun](llmops-v2-full-regression-2026-10-04.md) completed all 20 cases.
Fresh held-out evaluation and independent human answer review remain pending.

## Résumé wording supported now

Implemented Gemini API tracing, response-token accounting, stage-level latency
measurement and versioned paid-cost estimates for a multilingual RAG application.
Executed a 20-case regression with 18 model calls and two no-evidence skips, and
used qualitative evidence review to identify language and grounding failures.

Do not claim autonomous Agent tool selection, independently verified answer
accuracy, actual billed cost, or production MLOps operation from this run.
