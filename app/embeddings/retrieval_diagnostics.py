import time

from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from sqlalchemy import func, select, text

from app.db.session import SessionLocal
from app.embeddings.evaluate import (
    CANDIDATE_K,
    EVAL_KS,
    load_corpus_document_ids,
    load_questions,
    reciprocal_rank,
)
from app.models import Chunk, Document
from app.embeddings.hybrid_evaluate import retrieve_lexical

def inspect_failure_queries():
    questions = load_questions()
    corpus_document_ids = load_corpus_document_ids()

    for row in questions:
        if row["question_id"] not in {
            "qst_0020",
            "qst_0021",
            "qst_0033",
        }:
            continue

        expected_ids = (
            set(row["expected_doc_ids"])
            & corpus_document_ids
        )

        print("\n" + "=" * 80)
        print(row["question_id"])
        print(row["question"])
        print(f"Expected: {expected_ids}")

        lexical_results = retrieve_lexical(
            row["question"],
            CANDIDATE_K,
        )

        lexical_ids = [
            document_id
            for _, document_id in lexical_results
        ]

        print("\nLexical retrieval:")
        for rank, (score, document_id) in enumerate(
            lexical_results[:10],
            start=1,
        ):
            marker = " <-- EXPECTED" if document_id in expected_ids else ""
            print(
                f"{rank:3}. {score:.4f}  "
                f"{document_id}{marker}"
            )

        for expected_id in expected_ids:
            if expected_id in lexical_ids:
                print(
                    f"\nExpected document lexical rank: "
                    f"{lexical_ids.index(expected_id) + 1}"
                )
            else:
                print(
                    "\nExpected document: "
                    "NOT FOUND IN LEXICAL TOP 100"
                )


def inspect_fts_matching(external_id: str, query: str) -> None:
    with SessionLocal() as session:
        result = session.execute(
            text("""
                SELECT
                    d.external_id,
                    d.title,
                    to_tsvector('simple', c.content) AS document_tokens,
                    plainto_tsquery('simple', :query) AS query_tokens,
                    ts_rank_cd(
                        to_tsvector('simple', c.content),
                        plainto_tsquery('simple', :query)
                    ) AS rank
                FROM documents d
                JOIN chunks c ON c.document_id = d.id
                WHERE d.external_id = :external_id
            """),
            {
                "external_id": external_id,
                "query": query,
            },
        ).mappings().one()

        print("\n" + "=" * 80)
        print(f"EXPECTED DOCUMENT: {result['external_id']}")
        print(f"QUERY: {query}")
        print(f"\nQUERY TOKENS:\n{result['query_tokens']}")
        print(f"\nDOCUMENT TOKENS:\n{result['document_tokens']}")
        print(f"\nRANK: {result['rank']}")


def inspect_document(external_id: str) -> None:
    with SessionLocal() as session:
        document = session.query(Document).filter(
            Document.external_id == external_id
        ).first()

        if document is None:
            print(f"Document not found: {external_id}")
            return

        print("\n" + "=" * 80)
        print(f"DOCUMENT: {document.external_id}")
        print(f"Title: {document.title}")
        print(f"URI: {document.source_uri}")
        print(f"Chunks: {len(document.chunks)}")

        for chunk in document.chunks:
            print("\n" + "-" * 80)
            print(f"Chunk index: {chunk.chunk_index}")
            print(f"Metadata: {chunk.chunk_metadata}")
            print("\nContent:")
            print(chunk.content)

def main():
    inspect_document(
        "dsid_d7f0edbaa28147da807b5b85ea495bd1"
    )


if __name__ == "__main__":
    main()