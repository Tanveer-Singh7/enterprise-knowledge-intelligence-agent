import time

from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Chunk, Document


MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Retrieve more chunks than the final document-level K so that
# duplicate chunks from the same document do not distort evaluation.
CANDIDATE_K = 100

EVAL_KS = (1, 5, 10)


def load_questions() -> list[dict]:
    dataset = load_dataset(
        "onyx-dot-app/EnterpriseRAG-Bench",
        "questions",
        split="test",
        streaming=True,
    )

    questions = []

    for row in dataset:
        if "confluence" not in row["source_types"]:
            continue

        questions.append(row)

    return questions


def load_corpus_document_ids() -> set[str]:
    db = SessionLocal()

    try:
        statement = select(Document.external_id)
        return set(db.scalars(statement).all())

    finally:
        db.close()


def retrieve_documents(
    query_embedding,
    candidate_k: int,
) -> list[tuple[float, str]]:
    """
    Retrieve chunks using pgvector, then collapse results to documents.

    A document receives the score of its highest-scoring chunk.
    Results are returned as unique documents ranked by that score.
    """
    db = SessionLocal()

    try:
        distance = Chunk.embedding.cosine_distance(query_embedding)

        statement = (
            select(
                Document.external_id,
                distance.label("distance"),
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.embedding.is_not(None))
            .order_by(distance)
            .limit(candidate_k)
        )

        rows = db.execute(statement).all()

    finally:
        db.close()

    # Keep the best-scoring chunk for each document.
    best_document_scores: dict[str, float] = {}

    for external_id, cosine_distance in rows:
        score = 1.0 - float(cosine_distance)

        current_score = best_document_scores.get(external_id)

        if current_score is None or score > current_score:
            best_document_scores[external_id] = score

    ranked_documents = sorted(
        (
            (score, external_id)
            for external_id, score in best_document_scores.items()
        ),
        reverse=True,
        key=lambda item: item[0],
    )

    return ranked_documents


def reciprocal_rank(
    retrieved_ids: list[str],
    expected_ids: set[str],
) -> float:
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in expected_ids:
            return 1.0 / rank

    return 0.0


def main():
    print("Loading benchmark questions...")
    questions = load_questions()

    print(f"Confluence questions: {len(questions)}")

    print("Loading corpus document IDs...")
    corpus_document_ids = load_corpus_document_ids()

    # Only evaluate questions whose expected documents are actually
    # represented in the current retrieval corpus.
    evaluable_questions = [
        row
        for row in questions
        if set(row["expected_doc_ids"]) & corpus_document_ids
    ]

    excluded_questions = len(questions) - len(evaluable_questions)

    print(f"Corpus documents: {len(corpus_document_ids)}")
    print(f"Evaluable questions: {len(evaluable_questions)}")
    print(f"Excluded questions: {excluded_questions}")

    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    recall_counts = {k: 0 for k in EVAL_KS}
    mrr = 0.0

    retrieval_start = time.perf_counter()

    for row in evaluable_questions:
        expected_ids = (
            set(row["expected_doc_ids"]) & corpus_document_ids
        )

        query_embedding = model.encode(
            row["question"],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        results = retrieve_documents(
            query_embedding,
            CANDIDATE_K,
        )

        retrieved_ids = [
            external_id
            for _, external_id in results
        ]

        for k in EVAL_KS:
            if any(
                doc_id in expected_ids
                for doc_id in retrieved_ids[:k]
            ):
                recall_counts[k] += 1

        mrr += reciprocal_rank(
            retrieved_ids,
            expected_ids,
        )

    elapsed = time.perf_counter() - retrieval_start
    total = len(evaluable_questions)

    print()
    print("Retrieval baseline — corrected evaluation")
    print("------------------------------------------")
    print(f"Model:             {MODEL_NAME}")
    print(f"Questions:         {total}")
    print(f"Excluded:          {excluded_questions}")
    print(f"Candidate chunks:  {CANDIDATE_K}")
    print(f"Recall@1:          {recall_counts[1] / total:.4f}")
    print(f"Recall@5:          {recall_counts[5] / total:.4f}")
    print(f"Recall@10:         {recall_counts[10] / total:.4f}")
    print(f"MRR:               {mrr / total:.4f}")
    print(f"Eval time:         {elapsed:.2f}s")


if __name__ == "__main__":
    main()