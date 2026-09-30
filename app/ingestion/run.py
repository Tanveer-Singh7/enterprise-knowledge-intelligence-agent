from pathlib import Path

from app.db.session import SessionLocal
from app.ingestion.chunker import chunk_document
from app.ingestion.discovery import discover_files
from app.ingestion.parser import parse_file
from app.services.ingestion import DocumentPersistenceService


def ingest_directory_to_db(source_dir: Path) -> tuple[int, int, int]:

    db = SessionLocal()
    discovered = 0
    created = 0
    updated = 0
    skipped = 0
    persistence_service = DocumentPersistenceService()

    try:
        for path in discover_files(source_dir):
            discovered += 1
            document = parse_file(path)
            chunks = chunk_document(document)

            result = persistence_service.persist_document(
                db=db,
                document=document,
                chunks=chunks,
            )

            if result.status == "created":
                created += 1

            if result.status =="updated":
                updated += 1

            else:
                skipped += 1

        return discovered, created, updated, skipped

    finally:
        db.close()


if __name__ == "__main__":
    source_dir = Path("data/sample")
    discovered, created, updated, skipped = ingest_directory_to_db(source_dir)
    print(f"Discovered: {discovered}")
    print(f"Created:    {created}")
    print(f"Updated:    {updated}")
    print(f"Skipped:    {skipped}")