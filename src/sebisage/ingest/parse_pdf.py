"""PDF to pages with page numbers, via pymupdf.

Cleans three kinds of PDF noise found in SEBI's consolidated regulation PDFs:
  - page-number lines, either bare ("12") or "Page 12 of 82"
  - any other line repeated on > 50% of pages (running headers/footers)
  - amendment footnote markers: inline "N[text]" citation markers (unwrapped,
    keeping the current legal text) and the small-print footnote glossary
    ("1 Inserted by SEBI (...) Regulations, ... w.e.f. ...") at the foot of a
    page, which is amendment history, not regulation text.
"""

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pymupdf

_PAGE_NUM_RE = re.compile(r"^\s*(?:page\s+)?\d+(?:\s+of\s+\d+)?\s*$", re.IGNORECASE)
_INLINE_MARKER_RE = re.compile(r"\d+\s*\[([^\[\]]*)\]")
_GLOSSARY_VERBS = r"Inserted|Substituted|Omitted|Deleted|Renumbered|Added"
_GLOSSARY_ENTRY_RE = re.compile(
    rf"(?:\A|\n)\s*\d+\s+(?:{_GLOSSARY_VERBS})\b.*?(?=\n\s*\d+\s+(?:{_GLOSSARY_VERBS})\b|\n\s*\n|\Z)",
    re.DOTALL,
)


@dataclass(frozen=True)
class Page:
    page_number: int  # 1-based
    text: str
    source_file: str


def _clean_inline_markers(text: str) -> str:
    def repl(m: re.Match) -> str:
        inner = m.group(1).strip()
        return "" if inner == "***" or inner == "" else m.group(1)

    return _INLINE_MARKER_RE.sub(repl, text)


def _strip_glossary(text: str) -> str:
    return _GLOSSARY_ENTRY_RE.sub("\n", text)


def _repeated_lines(pages_lines: list[list[str]]) -> set[str]:
    counts: Counter = Counter()
    n = len(pages_lines)
    for lines in pages_lines:
        for stripped in {ln.strip() for ln in lines if ln.strip()}:
            counts[stripped] += 1
    return {line for line, c in counts.items() if n and c / n > 0.5}


def parse(path: str | Path) -> list[Page]:
    """Extract cleaned per-page text from a PDF, in reading order."""
    path = Path(path)
    doc = pymupdf.open(path)
    source_file = path.name
    try:
        raw_pages_lines = [doc[i].get_text().split("\n") for i in range(doc.page_count)]
    finally:
        doc.close()

    repeated = _repeated_lines(raw_pages_lines)

    pages = []
    for i, lines in enumerate(raw_pages_lines):
        kept = [ln for ln in lines if ln.strip() not in repeated and not _PAGE_NUM_RE.match(ln)]
        text = "\n".join(kept)
        text = _strip_glossary(text)
        text = _clean_inline_markers(text)
        text = text.strip()
        if text:
            pages.append(Page(page_number=i + 1, text=text, source_file=source_file))
    return pages
