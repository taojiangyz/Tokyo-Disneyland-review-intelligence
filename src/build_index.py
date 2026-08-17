import argparse
import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient, models

DATA_PATH = Path("data/disney_reviews_normalized.jsonl")
DEFAULT_QDRANT_PATH = Path("data/qdrant_db")
COLLECTION_NAME = "disney_reviews"

MODEL_NAME = "BAAI/bge-m3"

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"

DENSE_VECTOR_SIZE = 1024
BATCH_SIZE = 16


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path.resolve()}")

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

            if not record.get("review_id"):
                raise ValueError(f"Missing review_id on line {line_number}")

            if not record.get("text"):
                raise ValueError(f"Missing text on line {line_number}")

            records.append(record)

    return records


def stable_point_id(review_id: str) -> str:
    """Generate the same Qdrant point ID for the same review."""
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"disney-review:{review_id}",
        )
    )


def recreate_database(qdrant_path: Path) -> QdrantClient:
    resolved_path = qdrant_path.resolve()
    project_root = Path.cwd().resolve()

    if resolved_path == project_root or project_root not in resolved_path.parents:
        raise ValueError("Qdrant path must be inside the project directory")

    if qdrant_path.exists():
        shutil.rmtree(qdrant_path)

    qdrant_path.parent.mkdir(parents=True, exist_ok=True)

    client = QdrantClient(path=str(qdrant_path))

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            DENSE_VECTOR_NAME: models.VectorParams(
                size=DENSE_VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            SPARSE_VECTOR_NAME: models.SparseVectorParams(
                index=models.SparseIndexParams(
                    on_disk=False,
                ),
            ),
        },
    )

    return client


def to_qdrant_sparse_vector(
    lexical_weights: dict[str, float],
) -> models.SparseVector:
    """
    Convert BGE-M3 lexical weights into Qdrant sparse-vector format.
    """
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the local Qdrant review index")
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    parser.add_argument("--qdrant-path", type=Path, default=DEFAULT_QDRANT_PATH)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--yes", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.yes:
        raise SystemExit(
            "Refusing to replace the index without --yes. "
            "Stop the API and rerun with explicit confirmation."
        )
    started_at = time.perf_counter()

    records = load_records(args.data)

    print(f"Loaded records: {len(records)}")
    print(f"Model: {MODEL_NAME}")
    print(f"Batch size: {args.batch_size}")
    print("Dense: BGE-M3")
    print("Sparse: BGE-M3 lexical weights")

    model = BGEM3FlagModel(
        MODEL_NAME,
        use_fp16=False,
    )

    client = recreate_database(args.qdrant_path)
    uploaded = 0

    for start_index in range(0, len(records), args.batch_size):
        end_index = min(
            start_index + args.batch_size,
            len(records),
        )

        batch_records = records[start_index:end_index]
        batch_texts = [
            record["text"]
            for record in batch_records
        ]

        output = model.encode(
            batch_texts,
            batch_size=args.batch_size,
            max_length=1024,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )

        dense_vectors = output["dense_vecs"]
        sparse_vectors = output["lexical_weights"]

        points: list[models.PointStruct] = []

        for record, dense_vector, lexical_weights in zip(
            batch_records,
            dense_vectors,
            sparse_vectors,
            strict=True,
        ):
            point = models.PointStruct(
                id=stable_point_id(record["review_id"]),
                vector={
                    DENSE_VECTOR_NAME: dense_vector.tolist(),
                    SPARSE_VECTOR_NAME: to_qdrant_sparse_vector(
                        lexical_weights
                    ),
                },
                payload=record,
            )

            points.append(point)

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )

        uploaded += len(points)
        elapsed = time.perf_counter() - started_at

        print(
            f"Uploaded {uploaded}/{len(records)} "
            f"| elapsed: {elapsed:.1f}s"
        )

    collection_info = client.get_collection(
        collection_name=COLLECTION_NAME
    )

    elapsed = time.perf_counter() - started_at

    print("\nIndex build completed")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Points count: {collection_info.points_count}")
    print(f"Database path: {args.qdrant_path.resolve()}")
    print(f"Total time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
