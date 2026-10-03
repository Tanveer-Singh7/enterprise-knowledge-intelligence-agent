from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384),
        nullable=True
    )
    
    document = relationship("Document", back_populates="chunks")