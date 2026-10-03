import argparse
import time

from sentence_transformers import SentenceTransformer
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Chunk


DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_LIMIT = 5_000
DEFAULT_BATCH_SIZE = 32


def load_chunks(limit: int) -> list[Chunk]:
    db = SessionLocal()

    try:
        statement = (
            select(Chunk)
            .where(Chunk.embedding.is_(None))
            .order_by(Chunk.id)
            .limit(limit)
        )

        return list(db.scalars(statement).all())

    finally:
        db.close()


def benchmark(
    model_name: str,
    chunks: list[Chunk],
    batch_size: int,
) -> None:
    print(f"Model:              {model_name}")
    print(f"Chunks:              {len(chunks)}")
    print(f"Batch size:          {batch_size}")
    print()

    print("Loading model...")

    load_start = time.perf_counter()

    model = SentenceTransformer(
        model_name,
        device="cpu",
    )

    load_time = time.perf_counter() - load_start

    print(f"Model load time:     {load_time:.2f}s")
    print()

    texts = [chunk.content for chunk in chunks]

    print("Generating embeddings...")

    embedding_start = time.perf_counter()

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    embedding_time = time.perf_counter() - embedding_start

    print("Persisting embeddings...")

    db = SessionLocal()

    try:
        for chunk, embedding in zip(chunks, embeddings):
            db.execute(
                Chunk.__table__.update()
                .where(Chunk.id == chunk.id)
                .values(embedding = embedding.tolist())
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    total_chunks = len(chunks)
    throughput = total_chunks / embedding_time if embedding_time else 0.0

    print()
    print("Embedding benchmark")
    print("-------------------")
    print(f"Chunks embedded:     {total_chunks}")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    print(f"Embedding time:      {embedding_time:.2f}s")
    print(f"Throughput:          {throughput:.2f} chunks/sec")
    print("Embeddings persisted: yes")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate and persist local embeddings."
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Sentence Transformers model to benchmark.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum number of chunks to embed.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Embedding batch size.",
    )

    args = parser.parse_args()

    chunks = load_chunks(args.limit)

    if not chunks:
        raise RuntimeError("No chunks without embeddings found.")

    benchmark(
        model_name=args.model,
        chunks=chunks,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()