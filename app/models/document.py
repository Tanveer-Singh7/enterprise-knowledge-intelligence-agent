from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)

    external_id: Mapped[int] = mapped_column(
        String(255),
        nullable=True,
    )

    source_uri: Mapped[str] = mapped_column(
        String(1024), unique=True, nullable=False
        )
    
    title: Mapped[str] = mapped_column(
        String(512), nullable=False
        )
    content: Mapped[str] = mapped_column(
        Text, nullable=False
        )

    content_hash : Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chunks = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )