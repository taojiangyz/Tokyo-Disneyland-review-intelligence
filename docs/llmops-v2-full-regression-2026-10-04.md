# Full v2 prompt regression — 2026-10-04

## Scope and controls

Replayed the existing 20-case development suite through the local API using
`gemini-3.5-flash-lite`, prompt `v2-language-evidence`, dense retrieval and no
reranking. One retrieval-only warm-up preceded the run; requests were spaced by
five seconds. Warm-up and pauses are excluded from request latency. UI translation
and browser rendering are outside this run.

All 20 cases returned the same ordered evidence IDs and source text as the v1
baseline. This controls observed retrieval differences, but one sequential sample
per case does not establish statistical significance or held-out generalization.
The baseline structural results below use the repaired citation scorer.

## Results

| Measure | v1 baseline | v2 full rerun |
| --- | ---: | ---: |
| Structural checks passed | 20/20 | 20/20 |
| Successful model calls | 18/18 | 18/18 |
| No-evidence skips | 2 | 2 |
| Language matched question (Codex review) | 11/20 | 20/20 |
| Input tokens | 10,472 | 12,581 |
| Output tokens | 4,553 | 4,548 |
| Total reported tokens | 15,025 | 17,129 |
| Estimated standard paid USD | 0.0145241 | 0.0151443 |
| SDK attempt P50 / P95, ms (18 calls) | 1502.65 / 1795.13 | 1690.27 / 2025.73 |
| API P50 / P95, ms (18 generated answers) | 1693.18 / 2062.27 | 1876.88 / 2228.58 |

All-case API latency including the two skips: P50 1862.42 ms, P95 2220.62 ms.
No model fallback or failed SDK attempt occurred in this rerun. Billing tier was
declared free; paid-price estimates are comparative estimates, not an invoice.
Actual billed amount is unknown. Unreported thinking/cache fields remain null.

## Qualitative observations and remaining issues

These are Codex-assisted observations, not independent human accuracy labels.

- All previously observed language mismatches were absent in this rerun, including
  the Chinese no-evidence response.
- Case 05 now says there is insufficient evidence about dining prices rather than
  treating a generic price comparison as a food-price statement.
- Cases 08, 12 and 18 explicitly limit claims about frequency to the retrieved
  examples. Retrieved Top-K examples cannot establish population rankings.
- Case 16 still includes praise of a driver/tour guide. The source supports the
  statement, but its relevance to park service is uncertain. The answer also
  introduced the unnecessary typo/correction “非常号（非常好）”.
- Case 17 should more explicitly attribute assertions about show access and unfair
  treatment to the reviewer, rather than letting them sound like verified policy.
- Some answers repeat technical Top-K/population-frequency caveats unnecessarily;
  grouped citations can make clause-level attribution less precise.

Structural checks cover response shape, generation status, filters and citation
IDs; they do not prove semantic faithfulness, relevance or answer completeness.
Independent human review and fresh held-out questions remain pending. No new
Docker deployment or browser end-to-end validation was performed in this rerun.

## Local evidence and next validation

Private artifacts are under `evals/results/2026-10-04-v2-full/`: manifest with
source/data hashes, regression results, per-call usage logs, saved responses and
comparison metrics. Raw review text and answers are not intended for publication.
An eight-case independent-review worksheet was prepared separately with blank
judgment fields. Review it before claiming human-validated answer quality; then
freeze an unseen question set before any further prompt tuning.
