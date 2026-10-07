from collections import Counter

from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from sqlalchemy import select

from app.db.session import SessionLocal
from app.embeddings.evaluate import (
    CANDIDATE_K,
    load_corpus_document_ids,
    retrieve_documents,
)
from app.models import Document
from app.models.chunk import Chunk

MODEL_NAME = "BAAI/bge-small-en-v1.5"

ANALYSIS_TOP_K = 10


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


def load_document_titles() -> dict[str, str]:
    db = SessionLocal()

    try:
        statement = select(
            Document.external_id,
            Document.title,
        )

        rows = db.execute(statement).all()

        return {
            external_id: title or "<untitled>"
            for external_id, title in rows
        }

    finally:
        db.close()


def find_expected_rank(
    retrieved_ids: list[str],
    expected_ids: set[str],
) -> int | None:
    for rank, document_id in enumerate(retrieved_ids, start=1):
        if document_id in expected_ids:
            return rank

    return None


def inspect_document(external_id: str) -> None:
    db =SessionLocal()

    try:
        document = db.scalar(
            select(Document).where(
                Document.external_id == external_id
            )
        )

        if document is None:
            print(f"\nDocument not found: {external_id}")
            return

        print("\n"+"="*50)
        print(f"DOCUMENT: {external_id}")
        print(f"TITLE: {document.title}")
        print(f"URI: {document.source_uri}")
        print("="*50)

        chunks = db.scalars(
            select(Chunk)
            .where(Chunk.document_id == document.id)
            .order_by(Chunk.chunk_index)
        ).all()

        print(f"Chunks: {len(chunks)}")

        for chunk in chunks:
            print("\n" + "-" * 80)
            print(f"CHUNK {chunk.chunk_index}")
            print(f"METADATA: {chunk.chunk_metadata}")
            print("-" * 80)
            print(chunk.content)

    
    finally:
        db.close()

def main():
    print("Loading benchmark questions...")
    questions = load_questions()

    print(f"Confluence questions: {len(questions)}")

    print("Loading corpus document IDs...")
    corpus_document_ids = load_corpus_document_ids()

    print(f"Corpus documents: {len(corpus_document_ids)}")

    evaluable_questions = [
        row
        for row in questions
        if set(row["expected_doc_ids"]) & corpus_document_ids
    ]

    excluded_questions = len(questions) - len(evaluable_questions)

    print(f"Evaluable questions: {len(evaluable_questions)}")
    print(f"Excluded questions: {excluded_questions}")

    print("Loading document titles...")
    document_titles = load_document_titles()

    print("Loading embedding model...")
    model = SentenceTransformer(
        MODEL_NAME,
        device="cpu",
    )

    failures = []

    rank_buckets = Counter()

    for index, row in enumerate(evaluable_questions, start=1):
        expected_ids = (
            set(row["expected_doc_ids"])
            & corpus_document_ids
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

        expected_rank = find_expected_rank(
            retrieved_ids,
            expected_ids,
        )

        if expected_rank is None:
            rank_buckets["not_in_top_100"] += 1
        elif expected_rank <= 1:
            rank_buckets["rank_1"] += 1
        elif expected_rank <= 5:
            rank_buckets["rank_2_5"] += 1
        elif expected_rank <= 10:
            rank_buckets["rank_6_10"] += 1
        else:
            rank_buckets["rank_11_100"] += 1

        if expected_rank is None or expected_rank > ANALYSIS_TOP_K:
            failures.append(
                {
                    "index": index,
                    "question": row["question"],
                    "expected_ids": expected_ids,
                    "expected_rank": expected_rank,
                    "results": results,
                }
            )

    print()
    print("Retrieval Failure Analysis")
    print("==========================")
    print(f"Questions analysed: {len(evaluable_questions)}")
    print(f"Failures at Recall@{ANALYSIS_TOP_K}: {len(failures)}")
    print()

    print("Expected-document rank distribution")
    print("------------------------------------")

    print(
        f"Rank 1:          "
        f"{rank_buckets['rank_1']}"
    )

    print(
        f"Rank 2-5:        "
        f"{rank_buckets['rank_2_5']}"
    )

    print(
        f"Rank 6-10:       "
        f"{rank_buckets['rank_6_10']}"
    )

    print(
        f"Rank 11-100:     "
        f"{rank_buckets['rank_11_100']}"
    )

    print(
        f"Not in top 100:  "
        f"{rank_buckets['not_in_top_100']}"
    )

    print()
    print("Failure details")
    print("---------------")

    for failure in failures:
        print()
        print(
            f"[Question {failure['index']}] "
            f"{failure['question']}"
        )

        print(
            f"Expected IDs: "
            f"{sorted(failure['expected_ids'])}"
        )

        if failure["expected_rank"] is None:
            print(
                "Expected document: "
                "NOT FOUND IN TOP 100"
            )
        else:
            print(
                f"Expected document rank: "
                f"{failure['expected_rank']}"
            )

        print("Top retrieved documents:")

        for rank, (score, external_id) in enumerate(
            failure["results"][:ANALYSIS_TOP_K],
            start=1,
        ):
            title = document_titles.get(
                external_id,
                "<unknown>",
            )

            print(
                f"  {rank:>2}. "
                f"{score:.4f}  "
                f"{external_id}  "
                f"{title}"
            )


if __name__ == "__main__":
    main()