from pathlib import Path

from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient, models

QDRANT_PATH = Path("data/qdrant_db")
COLLECTION_NAME = "disney_reviews"

MODEL_NAME = "BAAI/bge-m3"

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"

TOP_K = 5
PREFETCH_LIMIT = 20


def to_qdrant_sparse_vector(
    lexical_weights: dict[str, float],
) -> models.SparseVector:
    sorted_items = sorted(
        (
            (int(token_id), float(weight))
            for token_id, weight in lexical_weights.items()
        ),
        key=lambda item: item[0],
    )

    return models.SparseVector(
        indices=[item[0] for item in sorted_items],
        values=[item[1] for item in sorted_items],
    )


def print_results(title: str, results) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    if not results:
        print("No results")
        return

    for rank, point in enumerate(results, start=1):
        payload = point.payload or {}

        print(f"\nRank: {rank}")
        print(f"Score: {point.score:.4f}")
        print(f"Review ID: {payload.get('review_id')}")
        print(f"Region: {payload.get('region')}")
        print(f"Rating: {payload.get('rating')}")
        print(f"Date: {payload.get('review_date')}")
        print(f"Text: {payload.get('text')}")


def main() -> None:
    query = "排队时间太长，游客感到疲惫"

    client = QdrantClient(path=str(QDRANT_PATH))

    model = BGEM3FlagModel(
        MODEL_NAME,
        use_fp16=False,
    )

    output = model.encode(
        [query],
        batch_size=1,
        max_length=1024,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )

    dense_query = output["dense_vecs"][0].tolist()

    sparse_query = to_qdrant_sparse_vector(
        output["lexical_weights"][0]
    )

    dense_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=dense_query,
        using=DENSE_VECTOR_NAME,
        limit=TOP_K,
        with_payload=True,
    ).points

    sparse_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=sparse_query,
        using=SPARSE_VECTOR_NAME,
        limit=TOP_K,
        with_payload=True,
    ).points

    hybrid_results = client.query_points(
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
        limit=TOP_K,
        with_payload=True,
    ).points

    print(f"Query: {query}")
    print(
        "Sparse query terms:",
        len(output["lexical_weights"][0]),
    )

    print_results("DENSE RESULTS", dense_results)
    print_results("BGE-M3 SPARSE RESULTS", sparse_results)
    print_results("HYBRID RRF RESULTS", hybrid_results)


if __name__ == "__main__":
    main()
