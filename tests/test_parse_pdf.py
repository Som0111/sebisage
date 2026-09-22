"""Tests for sebisage.ingest.parse_pdf, using a small synthetic PDF fixture."""

import pymupdf
import pytest

from sebisage.ingest.parse_pdf import parse


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    bodies = [
        "SEBI TEST REGULATIONS, 2026\n\n1\n\nShort title.\n\n1. (1) This is regulation one.",
        "SEBI TEST REGULATIONS, 2026\n\n2\n\nDefinitions.\n\n2. (1) This is regulation two.",
        (
            "SEBI TEST REGULATIONS, 2026\n\n3\n\n3. (1) This is regulation three.\n\n"
            "1 Inserted by SEBI Amendment Regulations, 2020, w.e.f. 1.1.2020."
        ),
    ]
    for body in bodies:
        page = doc.new_page()
        page.insert_text((72, 72), body, fontsize=11)
    doc.save(path)
    doc.close()
    return path


def test_page_count_matches_pymupdf(sample_pdf):
    pages = parse(sample_pdf)
    doc = pymupdf.open(sample_pdf)
    assert len(pages) == doc.page_count
    doc.close()


def test_repeated_header_removed(sample_pdf):
    pages = parse(sample_pdf)
    for page in pages:
        assert "SEBI TEST REGULATIONS, 2026" not in page.text


def test_no_empty_pages_returned(sample_pdf):
    pages = parse(sample_pdf)
    assert all(p.text.strip() for p in pages)


def test_page_number_lines_stripped(sample_pdf):
    pages = parse(sample_pdf)
    for page in pages:
        lines = [ln.strip() for ln in page.text.split("\n") if ln.strip()]
        assert not any(ln.isdigit() for ln in lines)


def test_footnote_glossary_stripped(sample_pdf):
    pages = parse(sample_pdf)
    full = "\n".join(p.text for p in pages)
    assert "Inserted by" not in full
