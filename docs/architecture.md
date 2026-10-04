# Architecture and design decisions

## Request flow

1. A manager enters any review-related question and optional filters in Streamlit.
2. Streamlit sends the question and filters to FastAPI. FastAPI validates market codes, rating bounds, date ordering, and evidence count.
3. The Agent router selects one bounded task plan: evidence Q&A, root-cause analysis, market comparison, or improvement planning.
4. The plan calls deterministic statistics and topic tools when the task requires full-dataset counts or comparisons.
5. BGE-M3 encodes the query, and Qdrant applies metadata filters before Dense Top 5 retrieval. This evaluated dense path is the interactive default.
6. The evidence verifier checks that the selected reviews contain the required IDs and content.
7. Gemini receives only the deterministic tool outputs and selected evidence, then generates an answer with review ID citations.
8. FastAPI returns the answer, evidence, applied filters, Agent steps, tool outputs, and timings to Streamlit.

Gemini does not read all 2,049 review texts for each question. Full-dataset counts come from deterministic code over the precomputed private topic-label store; generation receives only those aggregates and the small retrieved evidence set.

## Component boundaries

| Component | Responsibility |
|---|---|
| `src/prepare_data.py` | Validate and normalize raw multilingual reviews |
| `src/build_index.py` | Produce deterministic dense+sparse Qdrant points |
| `RagService` | Metadata, filtering, retrieval, fusion, and reranking |
| `ReviewAgent` | Route the task and execute a bounded, auditable tool plan |
| `ReviewTools` | Review statistics, topic analytics, retrieval, and evidence verification |
| `TopicService` | Deterministic aggregation over private AI-assisted topic labels |
| `GeminiService` | Evidence-constrained answer generation |
| FastAPI | Validation, Agent orchestration, response contract, and trace |
| Streamlit | Business question, filters, summary, evidence inspection |
| Regression runner | Repeatable behavior and filter-contract checks |
| Retrieval evaluator | Candidate pooling, human labels, Recall/MRR/nDCG and latency comparison |
| JSON access logger | Request correlation, HTTP status, and end-to-end request duration |

## Why dense retrieval is the interactive default

Dense retrieval helps when the user's wording differs from the review. In the human-verified Top-5 benchmark, Dense achieved the strongest Recall@5 and nDCG@5 while remaining interactive, so it is the default path used by the UI and Agent.

Sparse retrieval preserves exact multilingual terms, attraction names, and complaint phrases. RRF combines dense and sparse rankings without score calibration, while the cross-encoder provides a more expensive relevance judgment. These hybrid and reranker paths remain available through the evaluation endpoint for reproducible offline comparison, but they are not applied to every interactive request.

## Grounding and failure behavior

- Gemini is instructed to use only retrieved reviews and cite review IDs.
- Evidence verification and the regression runner reject citations that do not belong to returned evidence.
- If filters return no reviews, generation is skipped.
- If Gemini is temporarily unavailable, the API returns a degraded answer plus the retrieved evidence instead of failing the entire request.
- Filter values and ranking changes are returned so an engineer can reproduce the decision path.

## Data reproducibility and safety

- Normalization fails on malformed JSON, unsupported locale, missing ID/text, duplicate ID, invalid rating, or invalid date.
- Normalized output is written to a temporary file and atomically replaced.
- Qdrant point IDs are deterministic UUID5 values derived from review IDs.
- Index replacement requires `--yes`, and the destination must be inside the project directory.
- Secrets and the generated vector database are excluded from Git.

## Evaluation status

The 20-case regression suite tests API contracts, filter compliance, evidence counts, citation containment, graceful degradation, and multilingual execution. A separate benchmark contains 241 human-verified judgments over 15 questions and reports Recall and nDCG at Top 5 and Top 10, plus latency across dense, hybrid RRF, and reranked configurations. The next layer expands question coverage, adds confidence intervals, and separates warm-up from steady-state latency.

## Container topology

Docker Compose runs one FastAPI container and one Streamlit container. Only FastAPI opens the embedded Qdrant directory; Streamlit calls FastAPI over HTTP. This ownership boundary prevents the file-lock conflict caused by opening local Qdrant storage from multiple processes.
