import json 
import tomllib
from pathlib import Path

import yaml
from app.ingestion.models import SourceDocument
from app.ingestion.discovery import classify_file

def parse_file(path: Path) -> SourceDocument:
    """Parse a supported file into a normalized SourceDocument."""
    document_type = classify_file(path)

    if document_type in {"markdown", "text", "python"}:
        content = path.read_text(encoding="utf-8")

    elif document_type == "json":
        data = json.loads(path.read_text(encoding="utf-8"))
        content = json.dumps(data, indent=2, ensure_ascii=False)

    elif document_type == "yaml":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        content = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)

    elif document_type == "toml":
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        content = _format_mapping(data)

    else:
        raise ValueError(f"Unsupported document type: {document_type}")

    return SourceDocument(
        source_uri=str(path.resolve()),
        title=path.stem,
        content=content,
        metadata={
            "document_type": document_type,
            "extension": path.suffix.lower(),
        },
    )


def _format_mapping(data: dict) -> str:
    """Convert structured data into readable text."""
    return json.dumps(data, indent=2, ensure_ascii=False)