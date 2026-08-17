# Retrieval baseline

## Purpose

This first baseline validates the end-to-end evaluation machinery. It is deliberately small: two manually labeled questions and pooled top-five candidates from Dense, Hybrid RRF, and Hybrid + Reranker. It must not be presented as a statistically reliable model comparison.

## Initial results

| Retrieval mode | Recall@5 | MRR@5 | nDCG@5 | Mean pipeline latency |
|---|---:|---:|---:|---:|
| Dense | 0.639 | 1.000 | 0.878 | 184 ms |
| Hybrid RRF | 0.528 | 1.000 | 0.749 | 203 ms |
| Hybrid + Reranker (10 candidates) | 0.583 | 1.000 | 0.798 | 1,971 ms |
| Hybrid + Reranker (20 candidates) | 0.639 | 1.000 | 0.927 | 6,768 ms |

Environment: local Apple laptop, warm model process, two questions (`topic_waiting_en` and `topic_crowding_zh`), `k=5`. Latency includes query embedding; the reranked mode also includes cross-encoder scoring over 20 candidates.

## Interpretation

- All three systems placed a relevant result first on both questions.
- The reranker achieved the strongest graded ranking quality in this tiny sample.
- The reranker added several seconds of CPU latency, making candidate count and caching important deployment decisions.
- Reducing the reranker pool from 20 to 10 cut measured latency by about 71%, but nDCG@5 fell from 0.927 to 0.798 in this sample.
- Hybrid retrieval did not automatically outperform dense retrieval. On the English waiting-time question, sparse fusion promoted two irrelevant candidates into the top five.
- More labels are required before selecting a production retrieval configuration.

## Next experiment

The 15-query candidate pool now contains 241 unique query/review pairs in `evals/annotations/candidate_pool_15.csv`. Complete those judgments, report per-category metrics and confidence intervals, and retest candidate-pool sizes before selecting a production default.
