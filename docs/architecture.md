# Architecture and design decisions

## Request flow

1. A manager enters any review-related question and optional filters in Streamlit.
2. FastAPI validates market codes, rating bounds, date ordering, and evidence count.
3. BGE-M3 encodes the query into dense and sparse representations.
4. Qdrant applies metadata filters before retrieving candidates from both vector spaces.
5. Reciprocal Rank Fusion combines dense semantic and sparse lexical rankings.
6. `bge-reranker-v2-m3` scores query/review pairs and selects the final evidence.
7. Gemini receives only the selected evidence and must cite review IDs.
8. The API returns the answer, evidence, applied filters, rank changes, and timings.

## Component boundaries

| Component | Responsibility |
|---|---|
| `src/prepare_data.py` | Validate and normalize raw multilingual reviews |
| `src/build_index.py` | Produce deterministic dense+sparse Qdrant points |
| `RagService` | Metadata, filtering, retrieval, fusion, and reranking |
| `GeminiService` | Evidence-constrained answer generation |
| FastAPI | Validation, orchestration, response contract, trace |
| Streamlit | Business question, filters, summary, evidence inspection |
| Regression runner | Repeatable behavior and filter-contract checks |

## Why hybrid retrieval

Dense retrieval helps when the user's wording differs from the review. Sparse retrieval preserves exact multilingual terms, attraction names, and complaint phrases. RRF combines both without requiring score calibration, while the cross-encoder provides a more expensive final relevance judgment over a small candidate set.

## Grounding and failure behavior

- Gemini is instructed to use only retrieved reviews and cite review IDs.
- The regression runner rejects citations that do not belong to returned evidence.
- If filters return no reviews, generation is skipped.
- If Gemini is temporarily unavailable, the API returns a degraded answer plus the retrieved evidence instead of failing the entire request.
- Filter values and ranking changes are returned so an engineer can reproduce the decision path.

## Data reproducibility and safety

- Normalization fails on malformed JSON, unsupported locale, missing ID/text, duplicate ID, invalid rating, or invalid date.
- Normalized output is written to a temporary file and atomically replaced.
- Qdrant point IDs are deterministic UUID5 values derived from review IDs.
- Index replacement requires `--yes`, and the destination must be inside the project directory.
- Secrets and the generated vector database are excluded from Git.

## Next evaluation layer

The current 20-case suite tests API contracts, filter compliance, evidence counts, citation containment, graceful degradation, and multilingual execution. The next layer will add human-labeled relevant review IDs and calculate Recall@K, MRR, nDCG, citation precision, latency, and cost across three retrieval configurations.
