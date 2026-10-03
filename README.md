```md
# Enterprise Knowledge Intelligence & Support Agent

A production-oriented enterprise knowledge and support agent focused on reliable knowledge ingestion, retrieval engineering, grounded generation, evaluation, and controlled tool calling.

## Project Status

🚧 **In active development**

The project is being developed incrementally with an emphasis on measurable retrieval quality, grounded responses, reliability, and practical engineering trade-offs.

The current milestone establishes the knowledge ingestion foundation, benchmark corpus, embedding persistence, and an initial dense retrieval baseline.

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
Document Persistence
    ↓
PostgreSQL
    ↓
Embedding Generation
    ↓
pgvector
    ↓
Dense Retrieval
```

Grounded generation, evidence presentation, and controlled support tools are subsequent stages.

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

The persistence layer uses:

- PostgreSQL
- SQLAlchemy
- Alembic
- pgvector

Documents track:

- internal database ID
- external source/document ID
- source URI
- title
- content
- SHA-256 content hash
- creation timestamp
- update timestamp

The external document ID is kept separate from the internal database ID so that benchmark/source-system identities can be preserved for retrieval evaluation.

Chunks track:

- document relationship
- chunk content
- chunk index
- metadata
- optional 384-dimensional embedding

### Ingestion Safety

The ingestion pipeline handles:

- **New documents** → create
- **Unchanged documents** → skip
- **Changed documents** → update document and replace chunks

Content changes are detected using SHA-256 hashing.

### Benchmark Corpus

The project uses **EnterpriseRAG-Bench** as the initial enterprise-oriented retrieval benchmark.

Rather than downloading the complete benchmark corpus, the current workflow uses streaming extraction to materialize the required Confluence corpus locally.

Current benchmark corpus:

- Source type: Confluence
- Documents extracted: 5,000
- Local size: approximately 59 MB
- Storage: `data/benchmark/confluence/`
- Benchmark document IDs are preserved as external document IDs

The generated benchmark corpus is intentionally **not committed to Git**. The extraction tooling is version-controlled so the corpus can be reproduced.

### Embedding Baseline

The initial embedding baseline uses:

```text
BAAI/bge-small-en-v1.5
```

The model produces 384-dimensional embeddings.

Embeddings are persisted in PostgreSQL using pgvector rather than being kept only in application memory.

Current database state:

- Documents: 5,003
- Chunks: 5,006
- Chunks with persisted embeddings: 5,006

### Retrieval Evaluation

The retrieval baseline uses questions from the `questions` configuration of EnterpriseRAG-Bench.

The test split contains:

- 114 Confluence questions
- 113 questions whose expected document IDs are present in the current benchmark corpus
- 99.1% benchmark-document coverage

An initial dense retrieval evaluation produced:

| Metric | Result |
|---|---:|
| Recall@1 | 45.61% |
| Recall@5 | 67.54% |
| Recall@10 | 72.81% |
| MRR | 0.5408 |

These results establish the initial retrieval baseline. Retrieval evaluation and methodology will be refined before comparing subsequent retrieval improvements.

The project follows a:

```text
Baseline
   ↓
Measure
   ↓
Identify Weakness
   ↓
Improve
   ↓
Measure Again
```

workflow.

## Project Structure

```text
app/
├── api/
├── core/
│   └── config.py
├── db/
│   └── session.py
├── embeddings/
│   ├── benchmark.py
│   ├── evaluate.py
│   ├── models.py
│   └── __init__.py
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

scripts/
├── extract_confluence.py
└── ...

data/
├── sample/
└── benchmark/
    └── confluence/    # generated locally; ignored by Git

docs/
└── engineering-notes/

alembic.ini
docker-compose.yml
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

### Benchmark Corpus Extraction

The benchmark extraction utility uses Hugging Face dataset streaming and does not require downloading the complete benchmark corpus.

```bash
uv run python scripts/extract_confluence.py
```

The extracted documents are written to:

```text
data/benchmark/confluence/
```

This directory is ignored by Git.

## Roadmap

### Completed

- [x] Knowledge ingestion foundation
- [x] Structure-aware Markdown chunking
- [x] Metadata preservation
- [x] Incremental ingestion and change detection
- [x] External document ID preservation
- [x] Select enterprise-oriented benchmark corpus
- [x] Extract initial Confluence benchmark corpus
- [x] Ingest benchmark corpus into PostgreSQL
- [x] Embedding baseline
- [x] Persist embeddings with pgvector
- [x] Initial dense retrieval evaluation

### In Progress

- [ ] Retrieval failure analysis
- [ ] Retrieval evaluation refinement
- [ ] Retrieval improvements where justified by evaluation

### Planned

- [ ] Grounded LLM generation
- [ ] Evidence/source presentation
- [ ] Controlled support tools
- [ ] End-to-end evaluation
- [ ] Minimal frontend
- [ ] Dockerized deployment
- [ ] Final evaluation and documentation

PDF, DOCX, and XLSX ingestion remain possible future extensions and will be added only if they provide sufficient project or retrieval value.

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

AI frameworks such as LangChain or LangGraph may be introduced when they provide meaningful value for areas such as grounded generation, workflow orchestration, or controlled tool calling. They are not added solely for technology-stack breadth.

## Design Philosophy

The core principle is:

> **Common problem + uncommon engineering quality.**

The project deliberately avoids adding infrastructure, frameworks, agents, or retrieval techniques unless they solve a demonstrated problem or provide meaningful engineering value.

The development approach is:

```text
Baseline
   ↓
Measure
   ↓
Identify Weakness
   ↓
Improve
   ↓
Measure Again
```

Improvements are introduced based on measurable value rather than technology popularity or architectural complexity.