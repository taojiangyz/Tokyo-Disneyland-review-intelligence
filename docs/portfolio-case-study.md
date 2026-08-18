# Portfolio case study

## One-line pitch

Aladdin is a multilingual, evidence-grounded review intelligence assistant that turns 2,049 Tokyo Disney customer reviews into filterable management insights while keeping every claim auditable against its source reviews.

## Business problem

Managers cannot reliably read thousands of Chinese, Korean, and English-language reviews one by one. A fixed dashboard answers only anticipated questions, while a generic chatbot can produce unsupported summaries. The product goal was therefore to support open-ended questions without losing traceability.

## What I built

- A validation and normalization pipeline for 2,049 multilingual reviews.
- Dense and sparse BGE-M3 embeddings stored in local Qdrant.
- Dense, hybrid RRF, and cross-encoder reranking configurations.
- FastAPI endpoints for metadata, retrieval experiments, and grounded analysis.
- A Streamlit interface with free-form questions, market/rating/date filters, and expandable evidence.
- Gemini generation constrained to retrieved reviews, with citation containment checks and graceful degradation.
- A 20-case behavioral regression suite and a separate human relevance benchmark.
- Structured JSON request logs, request correlation IDs, Docker configuration, and reproducible Make targets.

## Evaluation approach

I pooled candidates from all retrieval configurations so that one system could not define its own ground truth. I then reviewed 241 query/review pairs across 15 questions and assigned graded relevance labels: 0 for unrelated, 1 for partly relevant, and 2 for directly relevant.

The 20-candidate reranker achieved the best nDCG@10 (0.800), but required about 6.16 seconds on local CPU. Dense retrieval achieved 0.792 nDCG@10 and essentially the same Recall@10 (0.673 versus 0.674). This led to an engineering recommendation: use dense retrieval for interactive CPU-hosted requests and reserve the reranker for offline analysis or stronger infrastructure.

## Reliability decisions

- Empty filter results skip generation instead of asking the model to guess.
- Gemini failures return retrieved evidence with a degraded status.
- Returned citations are checked against the evidence set.
- Data and index builds validate inputs and use deterministic identifiers.
- AI-assisted annotation suggestions are stored separately from human-verified labels.
- Korean annotation translations are cached locally to avoid repeated API usage.

## Honest limitations

- The benchmark covers 15 questions; 30–50 questions and confidence intervals would support stronger generalization claims.
- Local embedded Qdrant permits a single owning process and is not a production multi-instance architecture.
- Local CPU reranking is too slow for a strong interactive latency target.
- Authentication, authorization, tenant isolation, monitoring dashboards, and a public cloud deployment remain future production work.

## Interview talking points

1. Start with the business need: flexible analysis plus source-level trust.
2. Explain why RAG was used: the answer must be grounded in private review data.
3. Show the evidence cards and dynamic filters before discussing model details.
4. Explain candidate pooling and human relevance labels.
5. Present the quality-versus-latency result and the dense-default recommendation.
6. End with failure handling and the changes required for production scale.

## Resume bullets

- Built a multilingual RAG review-intelligence assistant over 2,049 customer reviews using FastAPI, Streamlit, Qdrant, BGE-M3, cross-encoder reranking, and Gemini, with dynamic market/date/rating filters and source-level evidence.
- Created a human-verified retrieval benchmark with 241 graded judgments across 15 questions; compared four retrieval configurations and identified a dense retrieval default that retained near-best nDCG@10 while avoiding multi-second CPU reranking latency.
- Added reproducible data/index pipelines, 17 automated tests, structured JSON logging, request correlation, graceful LLM degradation, and Docker Compose configuration.
