# Review quarantine — 2026-10-04

A user relevance annotation identified review `221035459` as describing Mount Fuji rather than Tokyo Disneyland. Its text also describes a guide, pirate ship and cable car. The shared retrieval filter now excludes this review ID before candidate selection for dense, hybrid and reranked retrieval. Original data and indexed points are retained.

The audit entry is in `config/review_quarantine.json`. To reverse the exclusion, change its status from `excluded` to `released`. Rules are read when constructing each query filter; no index rebuild is needed. Existing server processes need a restart to load the new Python code. Docker images need rebuilding because configuration is included in the image.

Two other guide-related reviews (`03ec7a99327cd9b058210418a3297e3d`, `670a3e8ea3170f4c7bf7357afbde85c1`) remain eligible: their text alone does not establish a different attraction. Keyword matching is a candidate discovery method, not grounds for automatic deletion. Comparisons with Shanghai/Hong Kong or mentions of DisneySea are not automatically excluded.

Validation: 30 tests passed. An in-memory Qdrant test verifies exclusion before the top-K limit, preserved market/rating filters, and no deletion. A release test verifies reversal. Against a local copy of the real index, total records remained 2,049 and eligible records became 2,048 (433 KR records). No Gemini request or full post-quarantine answer regression was run. Existing metadata counts still describe the full indexed corpus, not the eligible subset.

Historical retrieval/answer metrics remain results for the pre-quarantine corpus and are not silently recomputed. The 16 additional human labels and recalculated comparison are retained separately in the task outputs; this change does not alter those judgments. No new accuracy improvement is claimed, and the default remains dense retrieval with five final reviews.
