# Private dataset boundary

The full review dataset is intentionally not distributed in this public portfolio repository. It contains customer review text and source-platform user identifiers from Trip.com/Ctrip.com.

The local pipeline expects:

- `data/tdr_land_reviews_clean.jsonl`: authorized source export;
- `data/disney_reviews_normalized.jsonl`: generated normalized records;
- `data/qdrant_db/`: generated local vector index.
- `data/topic_labels.jsonl`: generated AI-assisted topic, sentiment, and confidence labels without review text.

All three paths are excluded from Git. If you have an authorized dataset with the same schema, run:

```bash
make validate-data
make prepare-data
make rebuild-index
```

The public repository retains aggregate dataset statistics, evaluation methodology, graded relevance labels without review text, application code, and automated tests.

Topic labels are derived from private reviews and remain excluded from Git. Generate a small batch with `python scripts/build_topic_labels.py --limit 40`, inspect its quality, and resume with `make topic-labels`. Existing review IDs are skipped automatically. These AI-assisted labels must be sampled and corrected by a human before they are treated as evaluation data or used for high-impact decisions.
