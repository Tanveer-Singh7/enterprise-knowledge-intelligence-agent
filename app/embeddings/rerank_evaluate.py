import time

from sentence_transformers import CrossEncoder, SentenceTransformer
from sqlalchemy import select

from app.db.session import SessionLocal
from app.embeddings.evaluate import (
    CANDIDATE_K,
    EVAL_KS,
    load_corpus_document_ids,
    load_questions,
    reciprocal_rank,
)
from app.models import Chunk, Document


EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2"

# Number of dense candidates passed to the reranker.
RERANK_CANDIDATE_K = CANDIDATE_K

# Standard practical batch size for CrossEncoder inference.
RERANK_BATCH_SIZE = 32


def retrieve_dense_candidates(
    query_embedding,
    candidate_k: int,
) -> list[tuple[float, str, str]]:
    """
    Retrieve dense candidates while preserving the best matching chunk text.

    Returns:
        (dense_score, document_external_id, chunk_content)
    """
    db = SessionLocal()

    try:
        distance = Chunk.embedding.cosine_distance(query_embedding)

        statement = (
            select(
                Document.external_id,
                Chunk.content,
                distance.label("distance"),
            )
            .join(
                Document,
                Chunk.document_id == Document.id,
            )
            .where(
                Chunk.embedding.is_not(None),
                Chunk.content.is_not(None),
            )
            .order_by(distance)
            .limit(candidate_k)
        )

        rows = db.execute(statement).all()

    finally:
        db.close()

    # Multiple chunks can belong to the same document.
    # Keep the highest-scoring chunk for each document.
    best_document_candidates: dict[str, tuple[float, str]] = {}

    for external_id, content, cosine_distance in rows:
        dense_score = 1.0 - float(cosine_distance)

        current = best_document_candidates.get(external_id)

        if current is None or dense_score > current[0]:
            best_document_candidates[external_id] = (
                dense_score,
                content,
            )

    return sorted(
        (
            (score, external_id, content)
            for external_id, (score, content) in best_document_candidates.items()
        ),
        reverse=True,
        key=lambda item: item[0],
    )


def rerank_candidates(
    reranker: CrossEncoder,
    query: str,
    candidates: list[tuple[float, str, str]],
) -> list[tuple[float, str]]:
    """
    Rerank dense candidates using a CrossEncoder.

    Returns:
        (reranker_score, document_external_id)
    """
    pairs = [
        (query, content)
        for _, _, content in candidates
    ]

    if not pairs:
        return []

    scores = reranker.predict(
        pairs,
        batch_size=RERANK_BATCH_SIZE,
        show_progress_bar=False,
    )

    reranked = [
        (float(score), external_id)
        for (_, external_id, _), score in zip(candidates, scores)
    ]

    return sorted(
        reranked,
        reverse=True,
        key=lambda item: item[0],
    )


def evaluate(
    embedding_model: SentenceTransformer,
    reranker: CrossEncoder,
    questions: list[dict],
    corpus_document_ids: set[str],
) -> tuple[dict[int, int], float, float]:
    """
    Evaluate dense retrieval followed by CrossEncoder reranking.
    """
    recall_counts = {k: 0 for k in EVAL_KS}
    mrr = 0.0

    start = time.perf_counter()

    for index, row in enumerate(questions, start=1):
        expected_ids = (
            set(row["expected_doc_ids"])
            & corpus_document_ids
        )

        query = row["question"]

        query_embedding = embedding_model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        dense_candidates = retrieve_dense_candidates(
            query_embedding,
            RERANK_CANDIDATE_K,
        )

        reranked_results = rerank_candidates(
            reranker,
            query,
            dense_candidates,
        )

        retrieved_ids = [
            document_id
            for _, document_id in reranked_results
        ]

        for k in EVAL_KS:
            if any(
                document_id in expected_ids
                for document_id in retrieved_ids[:k]
            ):
                recall_counts[k] += 1

        mrr += reciprocal_rank(
            retrieved_ids,
            expected_ids,
        )

        if index % 10 == 0:
            print(
                f"Processed {index}/{len(questions)} questions..."
            )

    elapsed = time.perf_counter() - start

    return recall_counts, mrr, elapsed


def main() -> None:
    print("Loading benchmark questions...")

    questions = load_questions()

    print(f"Confluence questions: {len(questions)}")

    print("Loading corpus document IDs...")

    corpus_document_ids = load_corpus_document_ids()

    evaluable_questions = [
        row
        for row in questions
        if set(row["expected_doc_ids"])
        & corpus_document_ids
    ]

    excluded_questions = (
        len(questions) - len(evaluable_questions)
    )

    print(f"Corpus documents: {len(corpus_document_ids)}")
    print(f"Evaluable questions: {len(evaluable_questions)}")
    print(f"Excluded questions: {excluded_questions}")

    print()
    print("Loading embedding model...")

    embedding_model = SentenceTransformer(
        EMBEDDING_MODEL_NAME,
        device="cpu",
    )

    print("Loading CrossEncoder reranker...")

    reranker = CrossEncoder(
        RERANKER_MODEL_NAME,
        device="cpu",
    )

    print()
    print("Running dense retrieval + reranking...")

    recall_counts, mrr, elapsed = evaluate(
        embedding_model=embedding_model,
        reranker=reranker,
        questions=evaluable_questions,
        corpus_document_ids=corpus_document_ids,
    )

    total = len(evaluable_questions)

    print()
    print("Dense retrieval + CrossEncoder reranking")
    print("----------------------------------------")
    print(f"Embedding model:   {EMBEDDING_MODEL_NAME}")
    print(f"Reranker model:    {RERANKER_MODEL_NAME}")
    print(f"Questions:         {total}")
    print(f"Excluded:          {excluded_questions}")
    print(f"Candidates:        {RERANK_CANDIDATE_K}")
    print(f"Batch size:        {RERANK_BATCH_SIZE}")

    print(
        f"Recall@1:          "
        f"{recall_counts[1] / total:.4f}"
    )

    print(
        f"Recall@5:          "
        f"{recall_counts[5] / total:.4f}"
    )

    print(
        f"Recall@10:         "
        f"{recall_counts[10] / total:.4f}"
    )

    print(f"MRR:               {mrr / total:.4f}")
    print(f"Eval time:         {elapsed:.2f}s")


if __name__ == "__main__":
    main()