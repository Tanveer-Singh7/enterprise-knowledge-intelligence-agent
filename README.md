# Enterprise Knowledge Intelligence & Support Agent

A production-oriented enterprise knowledge and support agent focused on reliable knowledge ingestion, retrieval engineering, grounded generation, evaluation, and controlled tool calling.

## Project Status

🚧 **In active development**

The current milestone establishes the knowledge ingestion foundation.

## Current Architecture

```text
Source Files
    ↓
File Discovery
    ↓
Format Classification
    ↓
Parsing
    ↓
Structure-Aware Chunking
    ↓
Metadata Preservation
    ↓
PostgreSQL
```

## Current Implementation

### Knowledge Ingestion

The ingestion pipeline currently supports:

- Markdown (`.md`)
- Plain text (`.txt`)
- Python (`.py`)
- YAML (`.yaml`, `.yml`)
- JSON (`.json`)
- TOML (`.toml`)

The pipeline:

1. Discovers supported files recursively.
2. Classifies files by extension.
3. Parses files into a common `SourceDocument` representation.
4. Performs structure-aware chunking where appropriate.
5. Preserves source and structural metadata.
6. Persists documents and chunks in PostgreSQL.

Markdown documents currently use heading-aware chunking with preserved heading hierarchy.

### Persistence

The current persistence layer uses:

- PostgreSQL
- SQLAlchemy
- Alembic

Documents track:

- source URI
- title
- content
- SHA-256 content hash
- creation timestamp
- update timestamp

Chunks track:

- document relationship
- chunk content
- chunk index
- metadata

### Ingestion Safety

The ingestion pipeline handles:

- **New documents** → create
- **Unchanged documents** → skip
- **Changed documents** → update document and replace chunks

Content changes are detected using SHA-256 hashing.

## Project Structure

```text
app/
├── core/
│   └── config.py
├── db/
│   └── session.py
├── ingestion/
│   ├── chunker.py
│   ├── discovery.py
│   ├── models.py
│   ├── parser.py
│   ├── pipeline.py
│   └── run.py
├── models/
│   ├── chunk.py
│   └── document.py
├── services/
│   └── ingestion.py
└── main.py

alembic/
├── versions/
└── env.py

data/
└── sample/

docker-compose.yml
alembic.ini
pyproject.toml
uv.lock
README.md
```

## Local Development

Install dependencies:

```bash
uv sync
```

Configure the database connection through `.env`:

```env
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:<port>/<database>
```

Apply database migrations:

```bash
uv run alembic upgrade head
```

Run the sample ingestion pipeline:

```bash
uv run python -m app.ingestion.run
```

The sample pipeline demonstrates discovery, parsing, chunking, metadata preservation, persistence, and change detection.

## Roadmap

- [ ] Select and ingest a real enterprise-oriented document corpus
- [ ] PDF ingestion
- [ ] DOCX ingestion
- [ ] Evaluate whether XLSX ingestion provides sufficient retrieval value
- [ ] Embedding model benchmark
- [ ] Vector storage with pgvector
- [ ] Retrieval baseline
- [ ] Retrieval evaluation
- [ ] Retrieval improvements where justified by evaluation
- [ ] Grounded LLM generation
- [ ] Evidence/source presentation
- [ ] Controlled support tools
- [ ] End-to-end evaluation
- [ ] Minimal frontend
- [ ] Dockerized deployment

## Engineering Focus

The project prioritizes:

- Retrieval quality over unnecessary architectural complexity
- Measurable evaluation
- Grounded responses and evidence attribution
- Reliable ingestion and change detection
- Controlled tool execution
- Maintainability and clear trade-offs
- Practical production-oriented engineering

The system is intentionally being developed incrementally rather than as a large multi-agent architecture.