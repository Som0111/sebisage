"""Tests for sebisage.eval.retrieval_eval (page-overlap hit criterion)."""

from sebisage.eval.retrieval_eval import aggregate, breakdown, evaluate_question, overlaps

GOLD = {
    "lodr_2015.pdf:30:1-2:0": {"source_file": "lodr_2015.pdf", "page_start": 29, "page_end": 29},
    "lodr_2015.pdf:17:1:1": {"source_file": "lodr_2015.pdf", "page_start": 16, "page_end": 16},
}

# Retrieved-chunk metadata: any chunker, so no reg_no field needed/used.
META_STRUCTURED = {
    "lodr_2015.pdf:30:1-2:0": {"source_file": "lodr_2015.pdf", "page_start": 29, "page_end": 29},
    "lodr_2015.pdf:30:5:0": {"source_file": "lodr_2015.pdf", "page_start": 29, "page_end": 30},
    "lodr_2015.pdf:17:1:1": {"source_file": "lodr_2015.pdf", "page_start": 16, "page_end": 16},
}
# A fixed-chunker chunk that happens to span the same page as the gold answer.
META_FIXED = {
    "lodr_2015.pdf:None:None:4": {"source_file": "lodr_2015.pdf", "page_start": 28, "page_end": 30},
    "lodr_2015.pdf:None:None:9": {"source_file": "lodr_2015.pdf", "page_start": 60, "page_end": 62},
}


def test_overlaps_same_file_overlapping_pages():
    assert overlaps("a.pdf", 5, 5, "a.pdf", 5, 5) is True
    assert overlaps("a.pdf", 4, 6, "a.pdf", 5, 5) is True
    assert overlaps("a.pdf", 1, 2, "a.pdf", 5, 5) is False
    assert overlaps("a.pdf", 5, 5, "b.pdf", 5, 5) is False


def test_evaluate_question_hit_via_page_overlap_not_reg_no():
    q = {"id": "q1", "type": "deadline", "difficulty": "easy", "gold_reg": "lodr_2015:30", "chunk_id": "lodr_2015.pdf:30:1-2:0"}
    ranked = [{"id": "lodr_2015.pdf:17:1:1", "score": 0.9}, {"id": "lodr_2015.pdf:30:5:0", "score": 0.8}]
    result = evaluate_question(q, ranked, META_STRUCTURED, GOLD)
    assert result.hit_at_1 is False
    assert result.hit_at_3 is True
    assert result.reciprocal_rank == 0.5


def test_evaluate_question_fixed_chunker_can_hit_despite_no_reg_no():
    q = {"id": "q1", "type": "deadline", "difficulty": "easy", "gold_reg": "lodr_2015:30", "chunk_id": "lodr_2015.pdf:30:1-2:0"}
    ranked = [{"id": "lodr_2015.pdf:None:None:4", "score": 0.5}, {"id": "lodr_2015.pdf:None:None:9", "score": 0.2}]
    result = evaluate_question(q, ranked, META_FIXED, GOLD)
    assert result.hit_at_1 is True
    assert result.reciprocal_rank == 1.0


def test_evaluate_question_unanswerable_records_top_score_no_hits():
    q = {"id": "q2", "type": "out_of_scope", "difficulty": "medium", "gold_reg": None, "chunk_id": None}
    ranked = [{"id": "lodr_2015.pdf:30:1-2:0", "score": 0.42}]
    result = evaluate_question(q, ranked, META_STRUCTURED, GOLD)
    assert result.answerable is False
    assert result.top_score == 0.42
    assert result.hit_at_1 is False


def test_aggregate_excludes_unanswerable_from_recall_but_tracks_their_scores():
    q1 = {"id": "q1", "type": "deadline", "difficulty": "easy", "gold_reg": "lodr_2015:30", "chunk_id": "lodr_2015.pdf:30:1-2:0"}
    q2 = {"id": "q2", "type": "out_of_scope", "difficulty": "medium", "gold_reg": None, "chunk_id": None}
    r1 = evaluate_question(q1, [{"id": "lodr_2015.pdf:30:1-2:0", "score": 1.0}], META_STRUCTURED, GOLD)
    r2 = evaluate_question(q2, [{"id": "lodr_2015.pdf:17:1:1", "score": 0.1}], META_STRUCTURED, GOLD)
    agg = aggregate([r1, r2])
    assert agg["n_answerable"] == 1
    assert agg["recall_at_1"] == 1.0
    assert agg["n_unanswerable"] == 1
    assert agg["unanswerable_top_scores"] == [0.1]


def test_breakdown_by_type():
    q1 = {"id": "q1", "type": "deadline", "difficulty": "easy", "gold_reg": "lodr_2015:30", "chunk_id": "lodr_2015.pdf:30:1-2:0"}
    q2 = {"id": "q2", "type": "definition", "difficulty": "easy", "gold_reg": "lodr_2015:17", "chunk_id": "lodr_2015.pdf:17:1:1"}
    r1 = evaluate_question(q1, [{"id": "lodr_2015.pdf:30:1-2:0", "score": 1.0}], META_STRUCTURED, GOLD)
    r2 = evaluate_question(q2, [{"id": "lodr_2015.pdf:17:1:1", "score": 1.0}], META_STRUCTURED, GOLD)
    result = breakdown([r1, r2], "type")
    assert set(result) == {"deadline", "definition"}
    assert result["deadline"]["recall_at_1"] == 1.0
