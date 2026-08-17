from qdrant_client import models


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
    regions: list[str] | None = None,
    min_rating: int | None = None,
    max_rating: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> models.Filter | None:
    conditions: list[models.Condition] = []

    selected_regions = list(regions or [])

    if region and region not in selected_regions:
        selected_regions.append(region)

    if selected_regions:
        conditions.append(
            models.FieldCondition(
                key="region",
                match=models.MatchAny(any=selected_regions),
            )
        )

    if min_rating is not None or max_rating is not None:
        conditions.append(
            models.FieldCondition(
                key="rating",
                range=models.Range(
                    gte=min_rating,
                    lte=max_rating,
                ),
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

from pathlib import Path
from time import perf_counter

from FlagEmbedding import BGEM3FlagModel, FlagReranker
from qdrant_client import QdrantClient


QDRANT_PATH = Path("data/qdrant_db")
COLLECTION_NAME = "disney_reviews"

EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"


def create_qdrant_client() -> QdrantClient:
    return QdrantClient(path=str(QDRANT_PATH))


def create_embedding_model() -> BGEM3FlagModel:
    return BGEM3FlagModel(
        EMBEDDING_MODEL_NAME,
        use_fp16=False,
    )


def create_reranker() -> FlagReranker:
    return FlagReranker(
        RERANKER_MODEL_NAME,
        use_fp16=False,
    )


DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"
PREFETCH_LIMIT = 20


def search_hybrid(
    query: str,
    region: str | None = None,
    min_rating: int | None = None,
    max_rating: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 5,
):
    client = create_qdrant_client()
    embedding_model = create_embedding_model()

    try:
        query_filter = build_filter(
            region=region,
            min_rating=min_rating,
            max_rating=max_rating,
            date_from=date_from,
            date_to=date_to,
        )

        embedding_start = perf_counter()

        output = embedding_model.encode(
            [query],
            batch_size=1,
            max_length=1024,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )

        embedding_ms = (
            perf_counter() - embedding_start
        ) * 1000

        dense_query = output["dense_vecs"][0].tolist()
        sparse_query = to_sparse_vector(
            output["lexical_weights"][0]
        )

        results = client.query_points(
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
            limit=limit,
            with_payload=True,
        ).points

        return results
    finally:
        client.close()


def search_with_reranker(
    query: str,
    region: str | None = None,
    min_rating: int | None = None,
    max_rating: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    candidate_limit: int = 20,
    final_limit: int = 5,
):
    client = create_qdrant_client()
    embedding_model = create_embedding_model()
    reranker = create_reranker()

    try:
        query_filter = build_filter(
            region=region,
            min_rating=min_rating,
            max_rating=max_rating,
            date_from=date_from,
            date_to=date_to,
        )

        embedding_start = perf_counter()

        output = embedding_model.encode(
            [query],
            batch_size=1,
            max_length=1024,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )

        embedding_ms = (
            perf_counter() - embedding_start
        ) * 1000

        dense_query = output["dense_vecs"][0].tolist()
        sparse_query = to_sparse_vector(
            output["lexical_weights"][0]
        )

        retrieval_start = perf_counter()

        hybrid_candidates = client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                models.Prefetch(
                    query=dense_query,
                    using=DENSE_VECTOR_NAME,
                    limit=candidate_limit,
                    filter=query_filter,
                ),
                models.Prefetch(
                    query=sparse_query,
                    using=SPARSE_VECTOR_NAME,
                    limit=candidate_limit,
                    filter=query_filter,
                ),
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF,
            ),
            limit=candidate_limit,
            with_payload=True,
        ).points

        retrieval_ms = (
            perf_counter() - retrieval_start
        ) * 1000

        if not hybrid_candidates:
            debug_info = {
                "hybrid_candidate_count": 0,
                "final_selected_count": 0,
                "reranking_trace": [],
                "timing_ms": {
                    "embedding": round(embedding_ms, 2),
                    "retrieval": round(retrieval_ms, 2),
                    "reranking": 0.0,
                    "retrieval_pipeline": round(
                        embedding_ms + retrieval_ms,
                        2,
                    ),
                },
            }

            return [], debug_info

        pairs = [
            [query, (point.payload or {}).get("text", "")]
            for point in hybrid_candidates
        ]

        reranking_start = perf_counter()

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

        reranking_ms = (
            perf_counter() - reranking_start
        ) * 1000

        rrf_rank_by_id = {
            str((point.payload or {}).get("review_id", "")): rank
            for rank, point in enumerate(
                hybrid_candidates,
                start=1,
            )
        }

        selected_results = ranked_results[:final_limit]

        reranking_trace = []

        for reranker_rank, (point, reranker_score) in enumerate(
            selected_results,
            start=1,
        ):
            payload = point.payload or {}
            review_id = str(payload.get("review_id", ""))

            reranking_trace.append(
                {
                    "review_id": review_id,
                    "rrf_rank": rrf_rank_by_id.get(review_id),
                    "reranker_rank": reranker_rank,
                    "rrf_score": float(point.score),
                    "reranker_score": float(reranker_score),
                }
            )

        debug_info = {
            "hybrid_candidate_count": len(hybrid_candidates),
            "final_selected_count": len(selected_results),
            "reranking_trace": reranking_trace,
            "timing_ms": {
                "embedding": round(embedding_ms, 2),
                "retrieval": round(retrieval_ms, 2),
                "reranking": round(reranking_ms, 2),
                "retrieval_pipeline": round(
                    embedding_ms
                    + retrieval_ms
                    + reranking_ms,
                    2,
                ),
            },
        }

        return selected_results, debug_info
    finally:
        client.close()


class RagService:
    def __init__(self) -> None:
        print("Loading Qdrant client...")
        self.client = create_qdrant_client()

        print("Loading BGE-M3 embedding model...")
        self.embedding_model = create_embedding_model()

        print("Loading BGE reranker...")
        self.reranker = create_reranker()

        print("RagService is ready.")

    def close(self) -> None:
        self.client.close()

    def get_metadata(self) -> dict[str, object]:
        records = []
        offset = None

        while True:
            batch, offset = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=256,
                offset=offset,
                with_payload=["region", "rating", "review_date"],
                with_vectors=False,
            )
            records.extend(batch)

            if offset is None:
                break

        region_counts: dict[str, int] = {}
        ratings: list[int] = []
        dates: list[str] = []

        for record in records:
            payload = record.payload or {}
            region = payload.get("region")
            rating = payload.get("rating")
            review_date = payload.get("review_date")

            if region:
                region_code = str(region)
                region_counts[region_code] = (
                    region_counts.get(region_code, 0) + 1
                )

            if rating is not None:
                ratings.append(int(rating))

            if review_date:
                dates.append(str(review_date))

        if not records or not ratings or not dates:
            raise RuntimeError("Review metadata is incomplete")

        market_labels = {
            "CN": "China",
            "HK": "Hong Kong",
            "KR": "Korea",
        }

        return {
            "total_reviews": len(records),
            "markets": [
                {
                    "code": code,
                    "label": market_labels.get(code, code),
                    "count": count,
                }
                for code, count in sorted(region_counts.items())
            ],
            "min_rating": min(ratings),
            "max_rating": max(ratings),
            "min_date": min(dates),
            "max_date": max(dates),
            "evidence_count_options": [3, 5, 10],
        }

    def retrieve_for_evaluation(
        self,
        query: str,
        mode: str,
        regions: list[str] | None = None,
        min_rating: int | None = None,
        max_rating: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 10,
        candidate_limit: int = 20,
    ):
        if mode == "hybrid_rerank":
            return self.search_and_rerank(
                query=query,
                regions=regions,
                min_rating=min_rating,
                max_rating=max_rating,
                date_from=date_from,
                date_to=date_to,
                candidate_limit=max(candidate_limit, limit),
                final_limit=limit,
            )

        query_filter = build_filter(
            regions=regions,
            min_rating=min_rating,
            max_rating=max_rating,
            date_from=date_from,
            date_to=date_to,
        )
        embedding_start = perf_counter()
        output = self.embedding_model.encode(
            [query],
            batch_size=1,
            max_length=1024,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        embedding_ms = (perf_counter() - embedding_start) * 1000
        dense_query = output["dense_vecs"][0].tolist()
        sparse_query = to_sparse_vector(output["lexical_weights"][0])
        retrieval_start = perf_counter()

        if mode == "dense":
            points = self.client.query_points(
                collection_name=COLLECTION_NAME,
                query=dense_query,
                using=DENSE_VECTOR_NAME,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            ).points
        elif mode == "hybrid":
            prefetch_limit = max(candidate_limit, limit)
            points = self.client.query_points(
                collection_name=COLLECTION_NAME,
                prefetch=[
                    models.Prefetch(
                        query=dense_query,
                        using=DENSE_VECTOR_NAME,
                        limit=prefetch_limit,
                        filter=query_filter,
                    ),
                    models.Prefetch(
                        query=sparse_query,
                        using=SPARSE_VECTOR_NAME,
                        limit=prefetch_limit,
                        filter=query_filter,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=limit,
                with_payload=True,
            ).points
        else:
            raise ValueError(f"Unsupported retrieval mode: {mode}")

        retrieval_ms = (perf_counter() - retrieval_start) * 1000
        results = [(point, float(point.score)) for point in points]
        rank_trace = [
            {
                "review_id": str((point.payload or {}).get("review_id", "")),
                "rank": rank,
                "score": float(point.score),
            }
            for rank, point in enumerate(points, start=1)
        ]
        debug_info = {
            "retrieval_mode": mode,
            "hybrid_candidate_count": len(points),
            "final_selected_count": len(points),
            "reranking_trace": rank_trace,
            "timing_ms": {
                "embedding": round(embedding_ms, 2),
                "retrieval": round(retrieval_ms, 2),
                "reranking": 0.0,
                "retrieval_pipeline": round(embedding_ms + retrieval_ms, 2),
            },
        }
        return results, debug_info

    def search_and_rerank(
        self,
        query: str,
        region: str | None = None,
        regions: list[str] | None = None,
        min_rating: int | None = None,
        max_rating: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        candidate_limit: int = 20,
        final_limit: int = 5,
    ):
        query_filter = build_filter(
            region=region,
            regions=regions,
            min_rating=min_rating,
            max_rating=max_rating,
            date_from=date_from,
            date_to=date_to,
        )

        embedding_start = perf_counter()

        output = self.embedding_model.encode(
            [query],
            batch_size=1,
            max_length=1024,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )

        embedding_ms = (
            perf_counter() - embedding_start
        ) * 1000

        dense_query = output["dense_vecs"][0].tolist()
        sparse_query = to_sparse_vector(
            output["lexical_weights"][0]
        )

        retrieval_start = perf_counter()

        hybrid_candidates = self.client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                models.Prefetch(
                    query=dense_query,
                    using=DENSE_VECTOR_NAME,
                    limit=candidate_limit,
                    filter=query_filter,
                ),
                models.Prefetch(
                    query=sparse_query,
                    using=SPARSE_VECTOR_NAME,
                    limit=candidate_limit,
                    filter=query_filter,
                ),
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF,
            ),
            limit=candidate_limit,
            with_payload=True,
        ).points

        retrieval_ms = (
            perf_counter() - retrieval_start
        ) * 1000

        if not hybrid_candidates:
            debug_info = {
                "hybrid_candidate_count": 0,
                "final_selected_count": 0,
                "reranking_trace": [],
                "timing_ms": {
                    "embedding": round(embedding_ms, 2),
                    "retrieval": round(retrieval_ms, 2),
                    "reranking": 0.0,
                    "retrieval_pipeline": round(
                        embedding_ms + retrieval_ms,
                        2,
                    ),
                },
            }

            return [], debug_info

        pairs = [
            [query, (point.payload or {}).get("text", "")]
            for point in hybrid_candidates
        ]

        reranking_start = perf_counter()

        reranker_scores = self.reranker.compute_score(
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

        reranking_ms = (
            perf_counter() - reranking_start
        ) * 1000

        rrf_rank_by_id = {
            str((point.payload or {}).get("review_id", "")): rank
            for rank, point in enumerate(
                hybrid_candidates,
                start=1,
            )
        }

        selected_results = ranked_results[:final_limit]

        reranking_trace = []

        for reranker_rank, (point, reranker_score) in enumerate(
            selected_results,
            start=1,
        ):
            payload = point.payload or {}
            review_id = str(payload.get("review_id", ""))

            reranking_trace.append(
                {
                    "review_id": review_id,
                    "rrf_rank": rrf_rank_by_id.get(review_id),
                    "reranker_rank": reranker_rank,
                    "rrf_score": float(point.score),
                    "reranker_score": float(reranker_score),
                }
            )

        debug_info = {
            "hybrid_candidate_count": len(hybrid_candidates),
            "final_selected_count": len(selected_results),
            "reranking_trace": reranking_trace,
            "timing_ms": {
                "embedding": round(embedding_ms, 2),
                "retrieval": round(retrieval_ms, 2),
                "reranking": round(reranking_ms, 2),
                "retrieval_pipeline": round(
                    embedding_ms
                    + retrieval_ms
                    + reranking_ms,
                    2,
                ),
            },
        }

        return selected_results, debug_info
