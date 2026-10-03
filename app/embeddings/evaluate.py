import time

from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Chunk, Document


MODEL_NAME = "BAAI/bge-small-en-v1.5"
TOP_K = 10


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


def load_embeddings():
    db = SessionLocal()

    try:
        statement = (
            select(Chunk, Document.external_id)
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.embedding.is_not(None))
            .order_by(Chunk.id)
        )

        return list(db.execute(statement).all())

    finally:
        db.close()


def cosine_search(query_embedding, chunks, top_k: int):
    scored = []

    for chunk, external_id in chunks:
        score = float(chunk.embedding @ query_embedding)
        scored.append((score, external_id))

    scored.sort(reverse=True, key=lambda x: x[0])

    return scored[:top_k]


def reciprocal_rank(retrieved_ids: list[str], expected_ids: set[str]) -> float:
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in expected_ids:
            return 1.0 / rank

    return 0.0


def main():
    print("Loading benchmark questions...")
    questions = load_questions()

    print(f"Confluence questions: {len(questions)}")

    print("Loading stored embeddings...")
    chunks = load_embeddings()

    print(f"Chunks with embeddings: {len(chunks)}")

    print("Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    recall_1 = 0
    recall_5 = 0
    recall_10 = 0
    mrr = 0.0

    start = time.perf_counter()

    for row in questions:
        expected_ids = set(row["expected_doc_ids"])

        query_embedding = model.encode(
            row["question"],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        results = cosine_search(
            query_embedding,
            chunks,
            TOP_K,
        )

        retrieved_ids = [external_id for _, external_id in results]

        if any(doc_id in expected_ids for doc_id in retrieved_ids[:1]):
            recall_1 += 1

        if any(doc_id in expected_ids for doc_id in retrieved_ids[:5]):
            recall_5 += 1

        if any(doc_id in expected_ids for doc_id in retrieved_ids[:10]):
            recall_10 += 1

        mrr += reciprocal_rank(
            retrieved_ids,
            expected_ids,
        )

    elapsed = time.perf_counter() - start
    total = len(questions)

    print()
    print("Retrieval baseline")
    print("------------------")
    print(f"Model:       {MODEL_NAME}")
    print(f"Questions:   {total}")
    print(f"Chunks:      {len(chunks)}")
    print(f"Recall@1:    {recall_1 / total:.4f}")
    print(f"Recall@5:    {recall_5 / total:.4f}")
    print(f"Recall@10:   {recall_10 / total:.4f}")
    print(f"MRR:         {mrr / total:.4f}")
    print(f"Eval time:   {elapsed:.2f}s")


if __name__ == "__main__":
    main()