import time

from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.embeddings.evaluate import (
    CANDIDATE_K,
    EVAL_KS,
    load_corpus_document_ids,
    load_questions,
    reciprocal_rank,
)
from app.models import Chunk, Document


MODEL_NAME = "BAAI/bge-small-en-v1.5"
RRF_K = 60


def retrieve_lexical(
    query: str,
    candidate_k: int,
) -> list[tuple[float, str]]:
    """
    Retrieve documents using PostgreSQL full-text search.

    The simple configuration is used deliberately so that
    enterprise terms, identifiers, and technical vocabulary
    are not aggressively stemmed.
    """
    db = SessionLocal()

    try:
        document_vector = func.to_tsvector(
            "simple",
            Chunk.content,
        )

        query_vector = func.websearch_to_tsquery(
            "simple",
            query,
        )

        rank = func.ts_rank_cd(
            document_vector,
            query_vector,
        )

        statement = (
            select(
                Document.external_id,
                rank.label("rank"),
            )
            .join(
                Document,
                Chunk.document_id == Document.id,
            )
            .where(
                Chunk.content.is_not(None),
                document_vector.op("@@")(query_vector),
            )
            .order_by(rank.desc())
            .limit(candidate_k)
        )

        rows = db.execute(statement).all()

    finally:
        db.close()

    best_document_scores: dict[str, float] = {}

    for external_id, score in rows:
        score = float(score)

        current_score = best_document_scores.get(external_id)

        if current_score is None or score > current_score:
            best_document_scores[external_id] = score

    return sorted(
        (
            (score, external_id)
            for external_id, score in best_document_scores.items()
        ),
        reverse=True,
        key=lambda item: item[0],
    )


def reciprocal_rank_fusion(
    dense_results: list[tuple[float, str]],
    lexical_results: list[tuple[float, str]],
) -> list[str]:
    """
    Fuse dense and lexical document rankings using RRF.

    Original retrieval scores are intentionally not combined because
    cosine similarity and PostgreSQL text-ranking scores are not
    directly comparable.
    """
    fused_scores: dict[str, float] = {}

    for rank, (_, document_id) in enumerate(
        dense_results,
        start=1,
    ):
        fused_scores[document_id] = (
            fused_scores.get(document_id, 0.0)
            + 1.0 / (RRF_K + rank)
        )

    for rank, (_, document_id) in enumerate(
        lexical_results,
        start=1,
    ):
        fused_scores[document_id] = (
            fused_scores.get(document_id, 0.0)
            + 1.0 / (RRF_K + rank)
        )

    return [
        document_id
        for document_id, _ in sorted(
            fused_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def retrieve_dense(
    query_embedding,
    candidate_k: int,
) -> list[tuple[float, str]]:
    """
    Dense retrieval copied from the validated baseline.
    """
    db = SessionLocal()

    try:
        distance = Chunk.embedding.cosine_distance(
            query_embedding
        )

        statement = (
            select(
                Document.external_id,
                distance.label("distance"),
            )
            .join(
                Document,
                Chunk.document_id == Document.id,
            )
            .where(Chunk.embedding.is_not(None))
            .order_by(distance)
            .limit(candidate_k)
        )

        rows = db.execute(statement).all()

    finally:
        db.close()

    best_document_scores: dict[str, float] = {}

    for external_id, cosine_distance in rows:
        score = 1.0 - float(cosine_distance)

        current_score = best_document_scores.get(external_id)

        if current_score is None or score > current_score:
            best_document_scores[external_id] = score

    return sorted(
        (
            (score, external_id)
            for external_id, score in best_document_scores.items()
        ),
        reverse=True,
        key=lambda item: item[0],
    )


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



def main():
    print("Loading benchmark questions...")
    questions = load_questions()

    print(f"Confluence questions: {len(questions)}")

    print("Loading corpus document IDs...")
    corpus_document_ids = load_corpus_document_ids()

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
    model = SentenceTransformer(
        MODEL_NAME,
        device="cpu",
    )

    recall_counts = {k: 0 for k in EVAL_KS}
    mrr = 0.0

    start = time.perf_counter()

    for row in evaluable_questions:
        expected_ids = (
            set(row["expected_doc_ids"])
            & corpus_document_ids
        )

        query = row["question"]

        query_embedding = model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        dense_results = retrieve_dense(
            query_embedding,
            CANDIDATE_K,
        )

        lexical_results = retrieve_lexical(
            query,
            CANDIDATE_K,
        )

        retrieved_ids = reciprocal_rank_fusion(
            dense_results,
            lexical_results,
        )

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

    elapsed = time.perf_counter() - start
    total = len(evaluable_questions)

    print()
    print("Hybrid retrieval — dense + PostgreSQL lexical + RRF")
    print("---------------------------------------------------")
    print(f"Dense model:       {MODEL_NAME}")
    print(f"Questions:         {total}")
    print(f"Excluded:          {excluded_questions}")
    print(f"Candidate chunks:  {CANDIDATE_K}")
    print(f"RRF constant:      {RRF_K}")
    print(f"Recall@1:          {recall_counts[1] / total:.4f}")
    print(f"Recall@5:          {recall_counts[5] / total:.4f}")
    print(f"Recall@10:         {recall_counts[10] / total:.4f}")
    print(f"MRR:               {mrr / total:.4f}")
    print(f"Eval time:         {elapsed:.2f}s")


if __name__ == "__main__":
    main()