"""Tests for sebisage.retrieve.hybrid (RRF fusion)."""

from sebisage.retrieve import hybrid


def test_rrf_math_hand_made_rankings():
    dense = ["a", "b", "c"]
    sparse = ["b", "a", "c"]
    scores = hybrid.rrf_fuse([dense, sparse], rrf_k=60)
    # a: rank1 in dense (1/61) + rank2 in sparse (1/62)
    assert scores["a"] == 1 / 61 + 1 / 62
    # b: rank2 in dense (1/62) + rank1 in sparse (1/61)
    assert scores["b"] == 1 / 62 + 1 / 61
    # c: rank3 in both (1/63 + 1/63)
    assert scores["c"] == 2 / 63


def test_doc_found_by_both_outranks_doc_found_by_one_at_equal_rank():
    # "shared" is rank 1 in both lists; "dense_only" is rank 1 in dense only.
    dense = ["shared", "dense_only"]
    sparse = ["shared", "sparse_only"]
    scores = hybrid.rrf_fuse([dense, sparse])
    ranked = sorted(scores, key=lambda d: scores[d], reverse=True)
    assert ranked[0] == "shared"
    assert scores["shared"] > scores["dense_only"]
    assert scores["shared"] > scores["sparse_only"]


def test_retrieve_fuses_and_tags_sources(monkeypatch):
    def fake_dense(query, chunker, k):
        return [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]

    def fake_sparse(query, chunker, k):
        return [("c2", 5.0), ("c4", 3.0)]

    monkeypatch.setattr(hybrid, "query_dense", fake_dense)
    monkeypatch.setattr(hybrid, "query_bm25", fake_sparse)

    results = hybrid.retrieve("some query", "structured", k=10)
    by_id = {r["id"]: r for r in results}

    assert by_id["c2"]["sources"] == ["dense", "sparse"]
    assert by_id["c1"]["sources"] == ["dense"]
    assert by_id["c4"]["sources"] == ["sparse"]
    # c2 found by both, ranked highly in both lists -> should score highest.
    assert results[0]["id"] == "c2"
