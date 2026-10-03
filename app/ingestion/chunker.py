from app.ingestion.models import DocumentChunk, SourceDocument

def chunk_markdown(document: SourceDocument) -> list[DocumentChunk]:
    lines = document.content.splitlines()

    chunks: list[DocumentChunk] = []
    heading_stack: list[tuple[int, str]] = []
    current_lines: list[str] = []

    def flush() -> None:
        content = '.\n'.join(current_lines).strip()

        if not content:
            return

        chunks.append(
            DocumentChunk(
                content=content,
                chunk_index=len(chunks),
                metadata={
                    **document.metadata,
                    "source_uri": document.source_uri,
                    "title": document.title,
                    "heading_path": [heading for _, heading in heading_stack],
                },
            )
        )

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip('#'))

            if level <= 6 and stripped[level: level + 1] == " ":
                flush()
                current_lines.clear()
                heading = stripped[level:].strip()

                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()

                heading_stack.append((level, heading))

                current_lines.append(line)
                continue
        current_lines.append(line)
            
    flush()
    
    return chunks

def chunk_document(document: SourceDocument) -> list[DocumentChunk]:
    document_type = document.metadata.get("document_type")

    if document_type == "markdown":
        return chunk_markdown(document)

    
    return [
        DocumentChunk(
            content=document.content.strip(),
            chunk_index=0,
            metadata={
                **document.metadata,
                "source_uri":document.source_uri,
                "title": document.title,
            },
        )
    ]