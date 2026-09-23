"""Dense + BM25 + Reciprocal Rank Fusion."""

from sebisage.config import K_DENSE, K_FUSED, K_SPARSE, RRF_K
from sebisage.index.dense import query_dense
from sebisage.index.sparse import query_bm25


def rrf_fuse(rankings: list[list[str]], rrf_k: int = RRF_K) -> dict[str, float]:
    """Reciprocal Rank Fusion over ranked id lists (best result first, rank 1)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for i, doc_id in enumerate(ranking):
            rank = i + 1
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank)
    return scores


def retrieve(query: str, chunker: str, k: int = K_FUSED) -> list[dict]:
    """Fuse dense + BM25 rankings with RRF. Returns top-k with score and source(s)."""
    dense_ids = [h["id"] for h in query_dense(query, chunker, K_DENSE)]
    sparse_ids = [doc_id for doc_id, _ in query_bm25(query, chunker, K_SPARSE)]

    scores = rrf_fuse([dense_ids, sparse_ids])
    dense_set, sparse_set = set(dense_ids), set(sparse_ids)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
    results = []
    for doc_id, score in ranked:
        sources = [s for s, ids in (("dense", dense_set), ("sparse", sparse_set)) if doc_id in ids]
        results.append({"id": doc_id, "score": score, "sources": sources})
    return results
