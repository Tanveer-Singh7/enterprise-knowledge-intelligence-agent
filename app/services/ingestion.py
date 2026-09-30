from dataclasses import dataclass
import hashlib
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import DocumentChunk, SourceDocument
from app.models.chunk import Chunk
from app.models.document import Document


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    document: Document
    status: str

class DocumentPersistenceService:
    """Persist documents and synchronize their chunks."""

    @staticmethod
    def _calculate_content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def persist_document(
        self,
        db: Session,
        document: SourceDocument,
        chunks: list[DocumentChunk],
    ) -> PersistenceResult:
        content_hash = self._calculate_content_hash(document.content)

        existing_document = db.scalar(
            select(Document).where(
                Document.source_uri == document.source_uri
            )
        )

        if existing_document is None:
            db_document = self._create_document(
                db,
                document,
                chunks,
                content_hash,
            )

            return PersistenceResult(
                document=db_document,
                status="created",
            )

        if existing_document.content_hash == content_hash:
            return PersistenceResult(
                document=existing_document,
                status="skipped",
            )

        db_document = self._update_document(
            db,
            existing_document,
            document,
            chunks,
            content_hash,
        )

        return PersistenceResult(
            document=db_document,
            status="updated",
        )

    @staticmethod
    def _create_document(
        db: Session,
        document: SourceDocument,
        chunks: list[DocumentChunk],
        content_hash: str,
    ) -> Document:
        db_document = Document(
            source_uri=document.source_uri,
            title=document.title,
            content=document.content,
            content_hash=content_hash,
        )

        for chunk in chunks:
            db_document.chunks.append(
                Chunk(
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    chunk_metadata=chunk.metadata,
                )
            )

        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        return db_document

    @staticmethod
    def _update_document(
        db: Session,
        db_document: Document,
        document: SourceDocument,
        chunks: list[DocumentChunk],
        content_hash: str,
    ) -> Document:
        db_document.title = document.title
        db_document.content = document.content
        db_document.content_hash = content_hash

        db_document.chunks.clear()

        for chunk in chunks:
            db_document.chunks.append(
                Chunk(
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    chunk_metadata=chunk.metadata,
                )
            )

        db.commit()
        db.refresh(db_document)

        return db_document