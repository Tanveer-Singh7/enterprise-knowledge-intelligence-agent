from sentence_transformers import CrossEncoder


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L6-v2"


class Reranker:
    def __init__(self, model_name: str = MODEL_NAME) -> None:
        self.model = CrossEncoder(
            model_name,
            device="cpu",
        )

    def rerank(
        self,
        query: str,
        candidates: list[tuple[str, str]],
    ) -> list[tuple[float, str]]:
        """
        Rerank (document_id, document_text) candidates for a query.
        """
        pairs = [
            (query, document_text)
            for _, document_text in candidates
        ]

        scores = self.model.predict(
            pairs,
            show_progress_bar=False,
        )

        ranked = [
            (float(score), document_id)
            for (document_id, _), score in zip(candidates, scores)
        ]

        return sorted(
            ranked,
            key=lambda item: item[0],
            reverse=True,
        )