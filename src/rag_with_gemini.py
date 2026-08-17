import os
from pathlib import Path

from dotenv import load_dotenv
from FlagEmbedding import BGEM3FlagModel, FlagReranker
from google import genai
from qdrant_client import QdrantClient, models

QDRANT_PATH = Path("data/qdrant_db")
COLLECTION_NAME = "disney_reviews"
ENV_PATH = Path(".env")

EMBEDDING_MODEL = "BAAI/bge-m3"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"

PREFETCH_LIMIT = 30
FINAL_TOP_K = 5


def to_sparse_vector(
    lexical_weights: dict[str, float],
) -> models.SparseVector:
    items = sorted(
        (
            (int(token_id), float(weight))
            for token_id, weight in lexical_weights.items()
        ),
        key=lambda item: item[0],
    )

    return models.SparseVector(
        indices=[item[0] for item in items],
        values=[item[1] for item in items],
    )


def build_filter(
    region: str | None = None,
    max_rating: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> models.Filter | None:
    conditions: list[models.Condition] = []

    if region:
        conditions.append(
            models.FieldCondition(
                key="region",
                match=models.MatchValue(value=region),
            )
        )

    if max_rating is not None:
        conditions.append(
            models.FieldCondition(
                key="rating",
                range=models.Range(lte=max_rating),
            )
        )

    if date_from or date_to:
        conditions.append(
            models.FieldCondition(
                key="review_date",
                range=models.DatetimeRange(
                    gte=date_from,
                    lte=date_to,
                ),
            )
        )

    if not conditions:
        return None

    return models.Filter(must=conditions)


def main() -> None:
    load_dotenv(dotenv_path=ENV_PATH)

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing")

    if not model_name:
        raise RuntimeError("GEMINI_MODEL is missing")

    query = (
        "How do Korean visitors describe the staff service "
        "at Tokyo Disneyland between October and December 2025?"
    )

    # Use the complete user question for retrieval.
    # This avoids manually narrowing or changing the user's intent.
    search_query = query

    region = "KR"
    max_rating = None
    date_from = "2025-10-01"
    date_to = "2025-12-31"

    query_filter = build_filter(
        region=region,
        max_rating=max_rating,
        date_from=date_from,
        date_to=date_to,
    )

    qdrant = QdrantClient(path=str(QDRANT_PATH))

    embedding_model = BGEM3FlagModel(
        EMBEDDING_MODEL,
        use_fp16=False,
    )

    reranker = FlagReranker(
        RERANKER_MODEL,
        use_fp16=False,
    )

    embedding_output = embedding_model.encode(
        [search_query],
        batch_size=1,
        max_length=1024,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )

    dense_query = embedding_output["dense_vecs"][0].tolist()

    sparse_query = to_sparse_vector(
        embedding_output["lexical_weights"][0]
    )

    hybrid_candidates = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            models.Prefetch(
                query=dense_query,
                using=DENSE_VECTOR_NAME,
                limit=PREFETCH_LIMIT,
                filter=query_filter,
            ),
            models.Prefetch(
                query=sparse_query,
                using=SPARSE_VECTOR_NAME,
                limit=PREFETCH_LIMIT,
                filter=query_filter,
            ),
        ],
        query=models.FusionQuery(
            fusion=models.Fusion.RRF,
        ),
        limit=PREFETCH_LIMIT,
        with_payload=True,
    ).points

    if not hybrid_candidates:
        print("No reviews matched the query and filters.")
        return

    pairs = [
        [search_query, point.payload["text"]]
        for point in hybrid_candidates
    ]

    reranker_scores = reranker.compute_score(
        pairs,
        normalize=True,
        max_length=1024,
    )

    ranked_results = sorted(
        zip(
            hybrid_candidates,
            reranker_scores,
            strict=True,
        ),
        key=lambda item: item[1],
        reverse=True,
    )[:FINAL_TOP_K]

    evidence_blocks: list[str] = []

    for point, reranker_score in ranked_results:
        payload = point.payload or {}

        evidence_blocks.append(
            "\n".join(
                [
                    f"[{payload.get('review_id')}]",
                    f"Region: {payload.get('region')}",
                    f"Rating: {payload.get('rating')}",
                    f"Date: {payload.get('review_date')}",
                    f"Reranker score: {reranker_score:.4f}",
                    f"Review: {payload.get('text')}",
                ]
            )
        )

    evidence_text = "\n\n".join(evidence_blocks)

    prompt = f"""
You are an internal consumer-review analysis assistant.

Answer only from the review evidence provided below.
Do not use external knowledge or make unsupported assumptions.

Requirements:
1. Answer in English.
2. Summarize two to four main findings.
3. Cite at least one review_id after every main finding, using the format
   [review_id].
4. Use a review as evidence only when it directly and explicitly supports
   the specific finding being made. Do not infer a topic from vague praise
   or criticism alone.
5. Do not describe a small number of reviews as the opinion of all visitors.
6. Do not invent percentages, visitor counts, or statistical conclusions.
7. Clearly state when the evidence is insufficient.
8. End with an "Evidence scope" sentence explaining that the findings are
   based only on the currently retrieved reviews.

Question:
{query}

Review evidence:
{evidence_text}
"""

    gemini = genai.Client(api_key=api_key)

    response = gemini.models.generate_content(
        model=model_name,
        contents=prompt,
    )

    print("\nQUESTION")
    print(query)

    print("\nTOP EVIDENCE")
    print(evidence_text)

    print("\nGEMINI ANSWER")
    print(response.text)


if __name__ == "__main__":
    main()
