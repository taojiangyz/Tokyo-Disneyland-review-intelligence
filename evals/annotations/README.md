# Relevance annotation

Generate a pooled candidate file from all three retrieval systems:

```bash
python scripts/export_annotation_pool.py
```

`candidate_pool_15.csv` is the current review batch: 15 questions and 241 unique candidates.

For each query/review pair, assign:

- `2`: directly relevant and useful evidence;
- `1`: partially relevant or useful as supporting context;
- `0`: irrelevant to the question.

Judge the review text without looking at `retrieved_by` or `best_rank` when possible. Add a short note for ambiguous decisions. Keep completed relevance labels in Git so experiments share the same human ground truth.

Start the review workspace with:

```bash
make run-annotation
```

Open `http://127.0.0.1:8502`. The page shows the original review and a cached Chinese translation for Korean text. Translation and Codex relevance suggestions are AI-generated aids, not ground truth. Only decisions saved with the 0/1/2 buttons are written to `human_verified_relevance_labels.csv` and consumed by the evaluator.

`ai_suggested_relevance_labels.csv` contains the initial Codex suggestions used for workflow testing and reviewer assistance. Never describe it as human-labeled data. Candidate pools can be regenerated whenever retrieval systems change.

After labeling at least several queries, run:

```bash
python scripts/evaluate_retrieval.py
```

The evaluator reports Recall@K, MRR@K, nDCG@K, and mean retrieval-pipeline latency for Dense, Hybrid RRF, and Hybrid + Reranker.
