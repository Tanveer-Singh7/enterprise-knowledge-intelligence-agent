# Retrieval Engineering Notes

## 1. Retrieval Baseline

The first retrieval implementation used dense vector search with:

- Embedding model: `BAAI/bge-small-en-v1.5`
- Embedding dimension: 384
- Database: PostgreSQL + pgvector
- Similarity: cosine distance
- Candidate chunks: 100
- Document-level evaluation using the benchmark's expected document IDs

Evaluation used the Confluence subset of EnterpriseRAG-Bench.

### Baseline Results

| Metric | Result |
|---|---:|
| Questions | 114 |
| Evaluable | 113 |
| Excluded | 1 |
| Recall@1 | 46.02% |
| Recall@5 | 68.14% |
| Recall@10 | 73.45% |
| MRR | 0.5498 |
| Evaluation time | 12.55s |

The evaluation intentionally focused on retrieval quality before adding LLM generation.

---

## 2. Retrieval Failure Analysis

The baseline was analyzed to understand why relevant documents were missed.

Among 30 Recall@10 failures:

- 52 questions had the expected document at rank 1.
- 25 had it at ranks 2–5.
- 6 had it at ranks 6–10.
- 14 had the expected document somewhere in the top 100 but below rank 10.
- 16 did not contain the expected document in the top 100.

This showed two different problems:

1. **Ranking problem:** relevant documents were retrieved but ranked too low.
2. **Candidate-generation problem:** relevant documents were not retrieved into the candidate set.

The 14 ranking failures made reranking a reasonable next step.

---

## 3. Hybrid Retrieval Investigation

PostgreSQL full-text search was tested as a possible lexical retrieval component.

The first implementation used `plainto_tsquery`. It showed that strict lexical matching can fail when a question uses terminology that does not appear exactly in the document.

`websearch_to_tsquery` was then tested with dense retrieval using Reciprocal Rank Fusion (RRF).

### Hybrid Results

| Metric | Dense Baseline | Dense + FTS + RRF |
|---|---:|---:|
| Recall@1 | 46.02% | 48.67% |
| Recall@5 | 68.14% | 69.03% |
| Recall@10 | 73.45% | 73.45% |
| MRR | 0.5498 | 0.5718 |
| Evaluation time | 12.55s | 816.29s |

The experiment showed a small ranking improvement but no Recall@10 improvement.

The implementation also calculated `to_tsvector()` during queries rather than using a persisted/generated tsvector column with a GIN index. Therefore, the measured latency was not representative of a production FTS implementation.

### Decision

Hybrid retrieval was deferred from the MVP.

The result did not justify adding another retrieval path at this stage. A production hybrid implementation can be reconsidered later if evaluation shows a clear need.

---

## 4. Reranking

A standard Cross-Encoder reranker was added using Sentence Transformers:

`cross-encoder/ms-marco-MiniLM-L6-v2`

The retrieval flow was:

```text
Dense retrieval
      ↓
Top 100 candidates
      ↓
Cross-Encoder reranking
      ↓
Document ranking
```

### Reranking Results

| Metric | Dense Baseline | + Cross-Encoder |
|---|---:|---:|
| Recall@1 | 46.02% | 58.41% |
| Recall@5 | 68.14% | 72.57% |
| Recall@10 | 73.45% | 76.99% |
| MRR | 0.5498 | 0.6450 |
| Evaluation time | 12.55s | 2846.94s |

Reranking produced a significant ranking improvement:

- Recall@1: +12.39 percentage points
- Recall@5: +4.43 percentage points
- Recall@10: +3.54 percentage points
- MRR: +0.0952

However, local CPU inference took approximately 47 minutes for 113 questions.

### Decision

The reranking approach was validated as useful for retrieval quality, but local CPU inference was not suitable as the preferred production inference path for this project.

The project will use managed/API-based inference where practical instead of spending additional development time optimizing local model inference.

---

## 5. Retrieval Architecture Decision

The retrieval layer will follow a standard production-oriented retrieve-then-rerank architecture:

```text
User Query
    ↓
Embedding API
    ↓
PostgreSQL + pgvector
    ↓
Initial candidate retrieval
    ↓
Reranking API
    ↓
Relevant evidence
    ↓
Grounded LLM response
```

The existing local dense retrieval implementation remains the reproducible baseline for evaluation.

The local Cross-Encoder experiment remains useful as evidence that reranking improves ranking quality, but it will not become the main inference implementation.

Future API selection will prioritize:

- free or very low development cost
- sufficient rate limits
- embedding support
- reranking support where available
- practical latency
- simple integration
- production usability

The project should avoid implementing custom retrieval or reranking algorithms when established libraries or APIs provide the required capability.

---

## 6. Current Retrieval Status

The retrieval engineering phase has established:

- document ingestion and persistence
- structure-aware chunking
- embedding generation and storage
- pgvector dense retrieval
- retrieval evaluation
- retrieval failure analysis
- hybrid retrieval investigation
- reranking evaluation
- a production-oriented direction for managed inference

The next major stage is **evidence and grounded generation**.

The planned query flow is:

```text
User Query
    ↓
Retrieval
    ↓
Reranking
    ↓
Evidence Selection
    ↓
Grounded LLM
    ↓
Answer + Sources
```

The system should also handle insufficient evidence rather than generating unsupported answers.

---

## 7. Engineering Lessons

### Evaluation before improvement

Retrieval changes are measured against the same benchmark instead of being judged only by example queries.

### Separate candidate generation from ranking

Dense retrieval is responsible for finding candidates. Reranking improves the ordering of those candidates.

### Accuracy and latency must be evaluated together

A retrieval method that improves quality but introduces excessive inference latency may not be appropriate for the final system.

### Prefer established components

The project uses PostgreSQL/pgvector and Sentence Transformers instead of implementing vector search or neural reranking from scratch. Managed APIs will be preferred where they reduce unnecessary local inference cost and complexity.

### Avoid unnecessary experimentation

Experiments are used only when they can influence an engineering decision. Once a strategy has sufficient evidence for a decision, implementation moves forward instead of continuously tuning the experiment.