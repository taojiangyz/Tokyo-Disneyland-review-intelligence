# Human-verified retrieval baseline

## Purpose

This baseline compares retrieval configurations against 241 human-verified query/review judgments covering 15 questions. Each candidate was graded as irrelevant (0), partly relevant (1), or directly relevant (2).

## Results

### Production depth (`k=5`)

| Retrieval mode | Recall@5 | MRR@5 | nDCG@5 | Mean pipeline latency |
|---|---:|---:|---:|---:|
| **Dense** | **0.365** | 0.850 | **0.772** | **387 ms** |
| Hybrid RRF | 0.314 | 0.822 | 0.707 | 243 ms |
| Hybrid + Reranker (10 candidates) | 0.344 | **0.872** | 0.758 | 3,467 ms |
| Hybrid + Reranker (20 candidates) | 0.335 | **0.872** | 0.744 | 6,834 ms |

Dense is the production default because the answer endpoint supplies five reviews to Gemini and dense achieved the best Recall@5 and nDCG@5. The rerankers improved MRR, but not enough to justify an additional 3–6 seconds in the interactive path.

### Diagnostic depth (`k=10`)

| Retrieval mode | Recall@10 | MRR@10 | nDCG@10 | Mean pipeline latency |
|---|---:|---:|---:|---:|
| Dense | 0.673 | 0.850 | 0.792 | 410 ms |
| Hybrid RRF | 0.616 | 0.832 | 0.732 | 222 ms |
| Hybrid + Reranker (10 candidates) | 0.607 | 0.872 | 0.745 | 3,301 ms |
| Hybrid + Reranker (20 candidates) | **0.674** | **0.872** | **0.800** | 6,163 ms |

Environment: local Apple laptop, 15 questions. Latency includes query embedding; reranked modes also include local cross-encoder scoring. The first dense request included model warm-up, so latency should be rerun with an explicit warm-up phase before making production capacity claims.

## Interpretation

- At the production depth of five reviews, dense retrieval achieved the strongest Recall and graded ranking quality.
- At the diagnostic depth of ten reviews, reranking 20 candidates was only 0.001 higher in Recall and 0.008 higher in nDCG while adding several seconds of CPU latency.
- Hybrid RRF did not automatically outperform dense retrieval on this multilingual review set.
- A 10-candidate reranker pool improved MRR over dense retrieval but lost recall because relevant reviews outside its candidate pool could not be recovered.
- For an interactive CPU-hosted demo, dense retrieval is the pragmatic default. The 20-candidate reranker is a quality-oriented option for offline analysis or stronger hardware.

## Next experiment

Add an explicit warm-up pass, report latency percentiles, expand the evaluation set to 30–50 questions, and calculate bootstrap confidence intervals before making a production-wide claim.
