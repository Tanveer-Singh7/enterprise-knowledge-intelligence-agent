from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceDocument:
    source_uri: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentChunk:
    content: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)