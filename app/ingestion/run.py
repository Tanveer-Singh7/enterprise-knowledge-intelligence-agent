import argparse
import time
from pathlib import Path

from app.db.session import SessionLocal
from app.ingestion.chunker import chunk_document
from app.ingestion.discovery import discover_files
from app.ingestion.parser import parse_file
from app.services.ingestion import DocumentPersistenceService


def ingest_directory_to_db(source_dir: Path) -> tuple[int, int, int, int]:
    db = SessionLocal()
    discovered = 0
    created = 0
    updated = 0
    skipped = 0
    persistence_service = DocumentPersistenceService()

    try:
        for path in discover_files(source_dir):
            discovered += 1
            
            # start = time.perf_counter()
            document = parse_file(path)
            # parse_time += time.perf_counter() - start

            # start = time.perf_counter()
            chunks = chunk_document(document)
            # chunk_time += time.perf_counter() - start

            
            # start = time.perf_counter()
            result = persistence_service.persist_document(
                db=db,
                document=document,
                chunks=chunks,
            )
            # persistence_time = time.perf_counter() - start

            if result.status == "created":
                created += 1

            if result.status == "updated":
                updated += 1

            elif result.status == "skipped":
                skipped += 1
    # We're not gonna return timings; instead instrumentation around the operation

        return discovered, created, updated, skipped, #parse_time, chunk_time, persistence_time

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest documents from a directory into PostgreSQL."
    )
    parser.add_argument(
        "source_dir",
        nargs="?",
        type=Path,
        default=Path("data/sample"),
        help="Directory containing documents to ingest.",
    )

    args = parser.parse_args()

    start = time.perf_counter() 

    discovered, created, updated, skipped = ingest_directory_to_db(
        args.source_dir
    )
    elapsed = time.perf_counter() - start

    print(f"Discovered: {discovered}")
    print(f"Created:    {created}")
    print(f"Updated:    {updated}")
    print(f"Skipped:    {skipped}")
    print(f"Time: {elapsed: 2f}s")
    print(f"Rate: {discovered/elapsed: 2f} doc/sec")

if __name__ == "__main__":
    main()