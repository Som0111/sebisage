"""Cross-encoder reranker over fused candidates."""

from sentence_transformers import CrossEncoder

from sebisage.config import K_FINAL, RERANKER_MODEL

_model: CrossEncoder | None = None


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder(RERANKER_MODEL)
    return _model


def rerank(query: str, candidates: list[dict], k: int = K_FINAL) -> list[dict]:
    """Score (query, chunk_text) pairs with the cross-encoder, return top-k.

    `candidates` are dicts with at least `id` and `text`; the return value is
    the same dicts with a `rerank_score` field added, sorted descending.
    """
    if not candidates:
        return []
    model = _get_model()
    pairs = [(query, c["text"]) for c in candidates]
    scores = model.predict(pairs)
    scored = [{**c, "rerank_score": float(s)} for c, s in zip(candidates, scores, strict=True)]
    scored.sort(key=lambda c: c["rerank_score"], reverse=True)
    return scored[:k]
