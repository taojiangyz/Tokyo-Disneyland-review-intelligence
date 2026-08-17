# Human-verified retrieval baseline

## Purpose

This baseline compares retrieval configurations against 241 human-verified query/review judgments covering 15 questions. Each candidate was graded as irrelevant (0), partly relevant (1), or directly relevant (2).

## Results

| Retrieval mode | Recall@10 | MRR@10 | nDCG@10 | Mean pipeline latency |
|---|---:|---:|---:|---:|
| Dense | 0.673 | 0.850 | 0.792 | 410 ms |
| Hybrid RRF | 0.616 | 0.832 | 0.732 | 222 ms |
| Hybrid + Reranker (10 candidates) | 0.607 | 0.872 | 0.745 | 3,301 ms |
| Hybrid + Reranker (20 candidates) | **0.674** | **0.872** | **0.800** | 6,163 ms |

Environment: local Apple laptop, 15 questions, `k=10`. Latency includes query embedding; reranked modes also include local cross-encoder scoring. The first dense request included model warm-up, so latency should be rerun with an explicit warm-up phase before making production capacity claims.

## Interpretation

- Reranking 20 candidates achieved the strongest overall Recall, MRR, and graded ranking quality.
- Dense retrieval was within 0.001 Recall and 0.009 nDCG of that result while avoiding several seconds of CPU reranking latency.
- Hybrid RRF did not automatically outperform dense retrieval on this multilingual review set.
- A 10-candidate reranker pool improved MRR over dense retrieval but lost recall because relevant reviews outside its candidate pool could not be recovered.
- For an interactive CPU-hosted demo, dense retrieval is the pragmatic default. The 20-candidate reranker is a quality-oriented option for offline analysis or stronger hardware.

## Next experiment

Add an explicit warm-up pass, report latency percentiles, expand the evaluation set to 30–50 questions, and calculate bootstrap confidence intervals before making a production-wide claim.
