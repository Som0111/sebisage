"""Tests for sebisage.retrieve.rerank (cross-encoder reranker)."""

from sebisage.retrieve.rerank import rerank


def test_relevant_pair_outscores_irrelevant_pair():
    candidates = [
        {"id": "irrelevant", "text": "Bananas are a good source of potassium and grow in tropical climates."},
        {"id": "relevant", "text": "Every listed entity shall disclose material events to the stock exchange."},
    ]
    results = rerank("When must a company disclose a material event?", candidates, k=2)
    assert results[0]["id"] == "relevant"
    assert results[0]["rerank_score"] > results[1]["rerank_score"]


def test_empty_candidates_returns_empty():
    assert rerank("anything", [], k=5) == []


def test_respects_k():
    candidates = [{"id": str(i), "text": f"chunk number {i}"} for i in range(5)]
    results = rerank("chunk", candidates, k=2)
    assert len(results) == 2
