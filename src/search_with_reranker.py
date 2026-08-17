from pathlib import Path

from FlagEmbedding import BGEM3FlagModel, FlagReranker
from qdrant_client import QdrantClient, models

QDRANT_PATH = Path("data/qdrant_db")
COLLECTION_NAME = "disney_reviews"

EMBEDDING_MODEL = "BAAI/bge-m3"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"

PREFETCH_LIMIT = 20
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


def main() -> None:
    query = "排队时间太长，游客感到疲惫"

    client = QdrantClient(path=str(QDRANT_PATH))

    embedding_model = BGEM3FlagModel(
        EMBEDDING_MODEL,
        use_fp16=False,
    )

    reranker = FlagReranker(
        RERANKER_MODEL,
        use_fp16=False,
    )

    output = embedding_model.encode(
        [query],
        batch_size=1,
        max_length=1024,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )

    dense_query = output["dense_vecs"][0].tolist()
    sparse_query = to_sparse_vector(
        output["lexical_weights"][0]
    )

    hybrid_candidates = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            models.Prefetch(
                query=dense_query,
                using=DENSE_VECTOR_NAME,
                limit=PREFETCH_LIMIT,
            ),
            models.Prefetch(
                query=sparse_query,
                using=SPARSE_VECTOR_NAME,
                limit=PREFETCH_LIMIT,
            ),
        ],
        query=models.FusionQuery(
            fusion=models.Fusion.RRF,
        ),
        limit=PREFETCH_LIMIT,
        with_payload=True,
    ).points

    pairs = [
        [query, point.payload["text"]]
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
    )

    print(f"Query: {query}")
    print("\nRERANKED RESULTS")

    for rank, (point, reranker_score) in enumerate(
        ranked_results[:FINAL_TOP_K],
        start=1,
    ):
        payload = point.payload or {}

        print("\n" + "-" * 80)
        print(f"Rank: {rank}")
        print(f"Reranker score: {reranker_score:.4f}")
        print(f"RRF score: {point.score:.4f}")
        print(f"Review ID: {payload.get('review_id')}")
        print(f"Region: {payload.get('region')}")
        print(f"Rating: {payload.get('rating')}")
        print(f"Date: {payload.get('review_date')}")
        print(f"Text: {payload.get('text')}")


if __name__ == "__main__":
    main()
