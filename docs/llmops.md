# LLMOps: request tracing, usage and evaluation

## Implemented scope

This is a fixed RAG workflow, not an autonomous tool-selecting agent. Existing
retrieval evaluation and citation-ID regression checks remain in place. This change
adds request-local Gemini attempt records, including fallback attempts, usage and
paid-price estimates. It removes the shared `last_model_name` field, which could
misattribute a model under concurrency or when generation was skipped.

Covered call sites:

- API answer generation (`answer`).
- Streamlit evidence translation (`ui_translation`), linked to the same request ID.
- Offline Korean annotation translation (`annotation_translation`), with independent IDs.

Each application-level SDK attempt records model, operation, prompt version, call ID,
request ID, timestamp, duration, status, error type, token metadata and price version.
Empty output or malformed translation is a failed attempt; returned usage is retained.
Exceptions without usage retain null counts, not zeros. SDK-internal transport retries
are not individually observable, so records are not a network-attempt ledger.

Files default to `evals/results/llm_calls/calls-HOST-PID.jsonl`, excluded from Git.
API/UI containers share the results directory via Compose. The append uses one write
per record. A write failure is logged without discarding a valid answer or repeating
its model call. No prompts, review text, response text, or API keys are logged.

## Configuration and reporting

Optional settings in `.env`:

```dotenv
LLM_BILLING_TIER=free
LLM_TELEMETRY_DIR=evals/results/llm_calls
LLM_PRICE_FILE=config/llm_prices.json
```

`LLM_BILLING_TIER` is a declaration, not account verification or a billing switch.
It defaults to `unknown` if unset. Do not edit or expose the API key to enable logging.
Restart the API and UI after updating code.

```bash
make llm-summary
python scripts/summarize_llm_usage.py --request-id REQUEST_ID
```

Token sums are known subtotals, with unknown counts alongside them. Thought/cache
fields may be omitted by the provider. Cost calculation treats omitted optional
fields as zero only with a reconciled prompt + candidate + thought total; unsupported
or inconsistent totals are not priced. Cached input is subtracted from ordinary
input, and thinking is included in output pricing. The estimator covers standard
text generation only, not tool charges, cache storage, taxes or invoice adjustments.
Unknown models or expired prices return null estimates. `actual_billed_usd` always
remains null until an actual billing reconciliation is implemented; free-tier use is
not represented as verified zero expenditure.

The checked-in rates were read on 2026-10-04, valid through 2026-12-31:

| Model | Input / 1M | Cached input / 1M | Output incl. thinking / 1M |
|---|---:|---:|---:|
| gemini-3.5-flash-lite | $0.30 | $0.03 | $2.50 |
| gemini-3.6-flash | $0.75 | $0.075 | $3.75 |

Source: [Google pricing](https://ai.google.dev/gemini-api/docs/pricing).
Usage fields: [Google token documentation](https://ai.google.dev/gemini-api/docs/generate-content/tokens).
Rates must be reviewed when changing models or after expiration; estimates are not
provider invoices. No new cloud services or paid subscription are enabled here.

## Evaluation

Normal cases in `scripts/run_regression.py` require `completed` generation unless
an expected alternative status is explicitly specified. No-evidence cases still
require `skipped_no_evidence`. Reports include request IDs, attempt records, code
commit/dirty status, case-file hash and P50/P95 API latency. A full regression run
makes model calls; it is not automatically run by unit tests.

Use a fresh telemetry directory for each benchmark. Record data/index and annotation
versions with the experiment, perform a separately marked warm-up, and keep cold
start separate. The API timing excludes UI translation; the UI interaction event
covers waiting for API and translation, but not browser rendering. Exceptions before
that completion event do not contribute a UI latency sample. Report their failures
separately rather than calling the completion-only latency a universal user SLA.
Percentiles from very small samples are diagnostic only. Per-attempt latency pools
successful and failed attempts; inspect records by operation/model for comparisons.

Citation IDs being present and in-range do not prove support for the answer. The next
manual evaluation should grade each main claim for evidence support, coverage of the
question, and appropriate abstention. Use 0 (incorrect), 1 (partial), 2 (supported),
record reviewer/reasons, and keep a held-out question set distinct from tuning cases.
No semantic-answer quality score or tool-selection accuracy is claimed here.

## Verification, 2026-10-04

- 28 tests passed, including fallback, unknown/expired pricing, thinking/cache cost,
  empty output, malformed translation, concurrent correlation, failed log writes,
  no-evidence API behavior and degraded-regression rejection.
- One real request used the existing configured Gemini model with synthetic review
  text only. Input 202 tokens, output 44 tokens, total 246; SDK duration 1,201.9 ms.
  Estimated standard paid cost: $0.0001706; actual billed amount is unknown.
- A subsequent [real-data baseline](llmops-regression-2026-10-04.md) and
  [full v2 prompt rerun](llmops-v2-full-regression-2026-10-04.md) each covered
  20 cases: 18 successful model calls and two no-evidence skips. The v2 run used
  17,129 reported tokens; structural checks passed 20/20. This is not a semantic
  accuracy score or capacity benchmark. Independent human answer evaluation,
  fresh held-out questions and Docker deployment remain pending.
