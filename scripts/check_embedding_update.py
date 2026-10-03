from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Chunk


db = SessionLocal()

try:
    chunk = db.scalars(
        select(Chunk)
        .where(Chunk.embedding.is_(None))
        .limit(1)
    ).first()

    if chunk is None:
        raise RuntimeError("No chunk without an embedding found.")

    test_embedding = [0.0] * 384

    db.execute(
        Chunk.__table__.update()
        .where(Chunk.id == chunk.id)
        .values(embedding=test_embedding)
    )

    db.commit()

    persisted = db.scalar(
        select(Chunk.embedding)
        .where(Chunk.id == chunk.id)
    )

    print(f"Chunk: {chunk.id}")
    print(f"Embedding dimension: {len(persisted)}")
    print("Persisted:", persisted is not None)

finally:
    db.close()