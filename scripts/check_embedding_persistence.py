
from sqlalchemy import select, text
from app.db.session import SessionLocal
from app.models import Chunk

db = SessionLocal()

try:
    chunk = db.scalars(
        select(Chunk).where(Chunk.embedding.is_(None)).limit(1)
    ).first()

    print("Chunk:", chunk.id)

    chunk.embedding = [0.0] * 384
    db.commit()

    print("Committed.")

    result = db.execute(
        text("SELECT embedding IS NOT NULL FROM chunks WHERE id = :id"),
        {"id": chunk.id},
    ).scalar()

    print("Persisted:", result)

finally:
    db.close()
