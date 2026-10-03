# Retrieval Baseline — Engineering Notes

## Embedding Persistence

### Problem

The initial embedding benchmark successfully generated embeddings but
the database contained zero persisted embeddings.

### Investigation

A direct database write using the SQLAlchemy `Chunk` model was tested
independently and successfully persisted a 384-dimensional vector.

This isolated the issue to the benchmark persistence path rather than
PostgreSQL, pgvector, or the ORM mapping.

### Resolution

Embedding persistence was changed to explicit SQLAlchemy UPDATE
operations followed by a transaction commit.

Verification:

- Total chunks: 5,006
- Chunks with embeddings: 5,006
- Chunks without embeddings: 0

## Retrieval Baseline

The baseline was evaluated against 114 Confluence questions from
EnterpriseRAG-Bench.

Results:

| Metric | Result |
|---|---:|
| Recall@1 | 45.61% |
| Recall@5 | 67.54% |
| Recall@10 | 72.81% |
| MRR | 0.5408 |

The next step is failure analysis before selecting a retrieval
improvement.