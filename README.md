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

## Retrieval & Evaluation

The retrieval pipeline uses PostgreSQL + pgvector for dense vector search, followed by optional reranking.

### Retrieval Baseline

The initial baseline uses `BAAI/bge-small-en-v1.5` embeddings with 384 dimensions.

Evaluation was performed on 114 Confluence questions from EnterpriseRAG-Bench, of which 113 were evaluable against the available corpus.

| Metric | Dense Retrieval |
|---|---:|
| Recall@1 | 46.02% |
| Recall@5 | 68.14% |
| Recall@10 | 73.45% |
| MRR | 0.5498 |
| Evaluation time | 12.55s |

### Retrieval Failure Analysis

The baseline produced 30 Recall@10 failures.

- 14 failures had the expected document within the top 100 candidates but ranked below the top 10.
- 16 failures did not retrieve the expected document within the top 100 candidates.

This indicated both ranking and candidate-generation limitations.

### Reranking

A standard Sentence Transformers Cross-Encoder was evaluated on the dense retrieval candidates.

Model:

`cross-encoder/ms-marco-MiniLM-L6-v2`

| Metric | Dense | Dense + Reranking |
|---|---:|---:|
| Recall@1 | 46.02% | 58.41% |
| Recall@5 | 68.14% | 72.57% |
| Recall@10 | 73.45% | 76.99% |
| MRR | 0.5498 | 0.6450 |

Reranking improved Recall@1 by 12.39 percentage points and MRR by 0.0952.

However, local CPU inference required approximately 47 minutes for the 113-question evaluation. The experiment therefore validated reranking as a useful retrieval technique, but local model inference was not selected as the preferred production approach.

### Hybrid Retrieval

PostgreSQL full-text search combined with dense retrieval using Reciprocal Rank Fusion was also investigated.

The experiment produced a small ranking improvement but no Recall@10 improvement:

| Metric | Dense | Dense + FTS + RRF |
|---|---:|---:|
| Recall@1 | 46.02% | 48.67% |
| Recall@5 | 68.14% | 69.03% |
| Recall@10 | 73.45% | 73.45% |
| MRR | 0.5498 | 0.5718 |

The approach was deferred from the MVP because the measured improvement did not justify adding another retrieval path at this stage.

### Current Direction

The production retrieval architecture will use established embedding and reranking APIs where practical:

```text
User Query
    ↓
Embedding API
    ↓
PostgreSQL + pgvector
    ↓
Candidate Retrieval
    ↓
Reranking API
    ↓
Evidence Selection
    ↓
Grounded LLM
    ↓
Answer + Sources
```

The project prioritizes retrieval quality, latency, cost, and maintainability rather than implementing custom retrieval algorithms.

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