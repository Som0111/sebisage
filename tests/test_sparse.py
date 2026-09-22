"""Tests for sebisage.index.sparse (BM25)."""

from sebisage.index import sparse
from sebisage.ingest.schema import Chunk

SOURCE = "synthetic.pdf"


def _chunk(id_, reg_no, text) -> Chunk:
    return Chunk(
        id=id_,
        text=text,
        regulation="synthetic",
        reg_no=reg_no,
        sub_reg="1",
        chapter=None,
        page_start=1,
        page_end=1,
        source_file=SOURCE,
        chunker="structured",
    )


FIXTURE = [
    _chunk("c1", "30", "Disclosure of events. Regulation 30 requires prompt disclosure of material events."),
    _chunk("c2", "17", "Board of directors composition under Regulation 17, including KMP appointments."),
    _chunk("c3", "5", "Definitions relevant to the listed entity and its obligations."),
    _chunk("c4", "9", "Preservation of documents for a minimum period as specified by the Board."),
    _chunk("c5", "1", "Short title and commencement of these regulations."),
]


def test_tokenizer_keeps_parenthesised_identifiers_intact():
    tokens = sparse.tokenize("Reg 30(6) applies to KMP disclosures.")
    assert "30(6)" in tokens
    assert "kmp" in tokens


def test_build_and_query_ranks_exact_term_match_first(tmp_path, monkeypatch):
    monkeypatch.setattr(sparse, "STORAGE_DIR", tmp_path)
    sparse.build_bm25(FIXTURE, "structured")
    results = sparse.query_bm25("Regulation 30", "structured", k=3)
    assert results[0][0] == "c1"


def test_rebuild_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(sparse, "STORAGE_DIR", tmp_path)
    sparse.build_bm25(FIXTURE, "structured")
    _, ids_first = sparse.load_bm25("structured")
    sparse.build_bm25(FIXTURE, "structured")
    _, ids_second = sparse.load_bm25("structured")
    assert ids_first == ids_second
    assert len(ids_second) == len(FIXTURE)
