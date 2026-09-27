"""Tests for sebisage.retrieve.rerank (cross-encoder reranker)."""

from sebisage.retrieve import rerank as rerank_module
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


def test_model_initialised_once_across_calls(monkeypatch):
    calls = []

    class FakeModel:
        def predict(self, pairs, **kwargs):
            return [0.0 for _ in pairs]

    def fake_cross_encoder(model_name):
        calls.append(model_name)
        return FakeModel()

    monkeypatch.setattr(rerank_module, "_model", None)
    monkeypatch.setattr(rerank_module, "CrossEncoder", fake_cross_encoder)

    rerank("first query", [{"id": "a", "text": "x"}])
    rerank("second query", [{"id": "b", "text": "y"}])

    assert len(calls) == 1
