"""Tests for sebisage.ingest.chunk: structured and fixed chunkers."""

from sebisage.config import MAX_CHUNK_TOKENS, MIN_CHUNK_TOKENS
from sebisage.ingest.chunk import fixed_chunks, structured_chunks
from sebisage.ingest.parse_pdf import Page

SOURCE = "synthetic_2026.pdf"
REGULATION = "synthetic_2026"


def _pages(*texts: str) -> list[Page]:
    return [Page(page_number=i + 1, text=t, source_file=SOURCE) for i, t in enumerate(texts)]


def _synthetic_three_reg_pages() -> list[Page]:
    body = (
        "CHAPTER I\n"
        "PRELIMINARY\n"
        "Short title.\n"
        "1. (1) These regulations may be called the Test Regulations, 2026.\n"
        "(2) They shall come into force at once.\n"
        "Definitions.\n"
        "2. (1) In these regulations, unless the context otherwise requires-\n"
        "(a) 'Board' means the Board.\n"
        "(b) 'company' means a company.\n"
        "CHAPTER II\n"
        "OBLIGATIONS\n"
        "Disclosure of events.\n"
        "3. (1) Every listed entity shall disclose material events.\n"
        "(2) The disclosure shall be made without delay.\n"
    )
    return _pages(body)


def test_structured_chunker_detects_correct_reg_numbers():
    chunks = structured_chunks(_synthetic_three_reg_pages(), SOURCE, REGULATION)
    reg_nos = sorted({c.reg_no for c in chunks}, key=lambda r: int(r))
    assert reg_nos == ["1", "2", "3"]


def test_structured_chunker_assigns_chapter():
    chunks = structured_chunks(_synthetic_three_reg_pages(), SOURCE, REGULATION)
    reg1 = [c for c in chunks if c.reg_no == "1"]
    reg3 = [c for c in chunks if c.reg_no == "3"]
    assert all(c.chapter == "I" for c in reg1)
    assert all(c.chapter == "II" for c in reg3)


def test_long_subregulation_splits_on_clauses_and_keeps_header():
    filler = " ".join(["word"] * 20)
    clauses = "\n".join(f"({chr(97 + i)}) clause number {i} {filler}." for i in range(20))
    body = f"Big obligations.\n1. (1) Intro text.\n{clauses}\n"
    chunks = structured_chunks(_pages(body), SOURCE, REGULATION)
    assert len(chunks) > 1
    assert all(c.text.startswith("[Regulation 1]") for c in chunks[1:])
    assert sum(len(c.text.split()) for c in chunks) >= MAX_CHUNK_TOKENS


def test_short_subregulation_merges_with_next():
    body = "Title.\n1. (1) Short.\n(2) " + " ".join(["word"] * 60) + "\n"
    chunks = structured_chunks(_pages(body), SOURCE, REGULATION)
    reg1_chunks = [c for c in chunks if c.reg_no == "1"]
    assert len(reg1_chunks) == 1
    assert reg1_chunks[0].sub_reg == "1-2"
    assert len(reg1_chunks[0].text.split()) >= MIN_CHUNK_TOKENS


def test_chunk_ids_stable_across_runs():
    pages = _synthetic_three_reg_pages()
    ids_a = [c.id for c in structured_chunks(pages, SOURCE, REGULATION)]
    ids_b = [c.id for c in structured_chunks(pages, SOURCE, REGULATION)]
    assert ids_a == ids_b
    assert len(ids_a) == len(set(ids_a))


def test_cross_reference_is_not_mistaken_for_new_regulation():
    body = (
        "Title one.\n"
        "1. (1) This refers to sub-regulation (4) of regulation 23 elsewhere.\n"
        "Title two.\n"
        "2. (1) Second regulation text.\n"
    )
    chunks = structured_chunks(_pages(body), SOURCE, REGULATION)
    reg_nos = sorted({c.reg_no for c in chunks}, key=lambda r: int(r))
    assert reg_nos == ["1", "2"]


def test_fixed_chunker_same_schema_no_reg_no():
    pages = _synthetic_three_reg_pages()
    chunks = fixed_chunks(pages, SOURCE, REGULATION, size=20, overlap=5)
    assert chunks
    assert all(c.reg_no is None and c.chunker == "fixed" for c in chunks)


def test_fixed_chunker_ids_stable_and_unique():
    pages = _synthetic_three_reg_pages()
    ids_a = [c.id for c in fixed_chunks(pages, SOURCE, REGULATION, size=20, overlap=5)]
    ids_b = [c.id for c in fixed_chunks(pages, SOURCE, REGULATION, size=20, overlap=5)]
    assert ids_a == ids_b
    assert len(ids_a) == len(set(ids_a))
