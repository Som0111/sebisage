"""Tests for sebisage.index.dense (Chroma + bge-small)."""

from sebisage.index import dense
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
    _chunk("c1", "30", "Every listed entity shall disclose material events or information to the stock exchange."),
    _chunk("c2", "17", "The board of directors shall have an optimum combination of executive and independent directors."),
    _chunk("c3", "5", "Definitions used throughout these regulations, including 'listed entity' and 'board'."),
    _chunk("c4", "9", "Records and documents shall be preserved for a minimum period of eight years."),
    _chunk("c5", "1", "These regulations may be called the Test Regulations and shall come into force at once."),
]


def test_build_and_query_returns_obviously_matching_chunk_first(tmp_path, monkeypatch):
    monkeypatch.setattr(dense, "CHROMA_DIR", tmp_path)
    dense.build_dense(FIXTURE, "structured")
    hits = dense.query_dense("When must a company disclose material events to the exchange?", "structured", k=3)
    assert hits[0]["id"] == "c1"


def test_metadata_excludes_text_field(tmp_path, monkeypatch):
    monkeypatch.setattr(dense, "CHROMA_DIR", tmp_path)
    dense.build_dense(FIXTURE, "structured")
    hits = dense.query_dense("board of directors composition", "structured", k=1)
    assert "text" not in hits[0]["metadata"]
    assert hits[0]["metadata"]["reg_no"] in {"30", "17", "5", "9", "1"}


def test_rebuild_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(dense, "CHROMA_DIR", tmp_path)
    dense.build_dense(FIXTURE, "structured")
    count_first = dense.load_collection("structured").count()
    dense.build_dense(FIXTURE, "structured")
    count_second = dense.load_collection("structured").count()
    assert count_first == count_second == len(FIXTURE)
