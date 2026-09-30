from pathlib import Path

from app.ingestion.chunker import chunk_document
from app.ingestion.discovery import discover_files
from app.ingestion.models import DocumentChunk
from app.ingestion.parser import parse_file

def ingest_directory(source_dir: Path) -> list[DocumentChunk]:
    """Discover, parse, and chunk supported documents"""

    chunks: list[DocumentChunk] = []

    for path in discover_files(source_dir):
        document = parse_file(path)
        chunks.extend(chunk_document(document))

    return chunks