# Private dataset boundary

The full review dataset is intentionally not distributed in this public portfolio repository. It contains customer review text and source-platform user identifiers from Trip.com/Ctrip.com.

The local pipeline expects:

- `data/tdr_land_reviews_clean.jsonl`: authorized source export;
- `data/disney_reviews_normalized.jsonl`: generated normalized records;
- `data/qdrant_db/`: generated local vector index.

All three paths are excluded from Git. If you have an authorized dataset with the same schema, run:

```bash
make validate-data
make prepare-data
make rebuild-index
```

The public repository retains aggregate dataset statistics, evaluation methodology, graded relevance labels without review text, application code, and automated tests.
