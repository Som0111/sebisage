"""Structure-aware and fixed-size chunkers.

Structure-aware chunker: SEBI's consolidated regulation PDFs use a
consistent three-level layout, each level starting its own blank-line
paragraph:
  - regulation:     "30. (1) Every listed entity shall..."  -> bare "NN." or "NNA."
  - sub-regulation:  "(1) ...", "(2) ..."                    -> "(N)"
  - clause:          "(a) ...", "(b) ..."                    -> "(a)"
A chapter heading ("CHAPTER IV") and a schedule heading ("SCHEDULE I") each
start their own paragraph too. Regulation/sub-regulation numbers are
validated to be strictly increasing (by (number, letter-suffix)) so that
inline cross-references like "...under regulation 23..." (which appear
mid-sentence, not at a paragraph start) can never be mistaken for a new
regulation.
"""

import re
from bisect import bisect_right

from sebisage.config import (
    FIXED_CHUNK_OVERLAP,
    FIXED_CHUNK_SIZE,
    MAX_CHUNK_TOKENS,
    MIN_CHUNK_TOKENS,
)
from sebisage.ingest.parse_pdf import Page, _clean_inline_markers
from sebisage.ingest.schema import Chunk, make_id

_CHAPTER_RE = re.compile(r"(?:\A|\n)[ \t]*CHAPTER[ \t]*-?[ \t]*([IVXLCDM]+)\b")
_SCHEDULE_RE = re.compile(r"(?:\A|\n)[ \t]*SCHEDULE[ \t]+([IVXLCDM]+|[0-9]+)\b")
# Regulation/sub-regulation/clause markers each start their own line, but PDF
# text extraction is inconsistent about whether a blank line precedes them
# (varies with font/spacing), so anchor on a plain line start and rely on
# strict-increase ordering (see _monotonic_matches) to reject cross-reference
# mentions like "...under regulation 23..." that never fall at a line start.
# A trailing lookahead (not a consumed space) because some PDFs glue the next
# marker directly on, e.g. "22.(1)" with no space (seen in sast_2011.pdf).
_REG_RE = re.compile(r"(?:\A|\n)[ \t]*(\d{1,3})([A-Z]?)\.(?=[\s(])")
_SUBREG_RE = re.compile(r"(?:\A|\n)[ \t]*\((\d{1,2})\)(?=[\s(]|$)")
_CLAUSE_RE = re.compile(r"(?:\A|\n)[ \t]*\(([a-z]{1,3})\)(?=[\s(]|$)")


def count_tokens(text: str) -> int:
    """Cheap token proxy: whitespace word count (no tokenizer dependency)."""
    return len(text.split())


_PAGE_SEP = "\x00PB\x00"


def _build_full_text(pages: list[Page]) -> tuple[str, list[tuple[int, int]]]:
    """Join page texts; return (full_text, [(start_offset, page_number), ...]).

    Cleans inline amendment-bracket markers again across the joined text
    (parse_pdf already does this per page), since a bracket that wraps an
    entire inserted regulation can span a page break and be left unclosed
    on either side when cleaned per page alone.
    """
    joined = _PAGE_SEP.join(page.text for page in pages)
    cleaned = _clean_inline_markers(joined)
    cleaned_texts = cleaned.split(_PAGE_SEP)

    parts = []
    offsets = []
    pos = 0
    for page, text in zip(pages, cleaned_texts):
        offsets.append((pos, page.page_number))
        parts.append(text)
        pos += len(text) + 2  # for the "\n\n" separator below
        parts.append("\n\n")
    return "".join(parts), offsets


def _page_at(offsets: list[tuple[int, int]], pos: int) -> int:
    starts = [o[0] for o in offsets]
    idx = max(0, bisect_right(starts, pos) - 1)
    return offsets[idx][1]


def _monotonic_matches(pattern: re.Pattern, text: str, end: int | None = None) -> list[tuple[int, int, int, str]]:
    """Find paragraph-start matches whose (number, suffix) is strictly increasing.

    Returns a list of (start, content_start, number, suffix) tuples, where
    `start` is the match start (including the blank-line/BOF anchor) and
    `content_start` is where the sub-text after the marker begins.
    """
    search_text = text if end is None else text[:end]
    accepted = []
    last_key: tuple[int, str] = (-1, "")
    for m in pattern.finditer(search_text):
        num = int(m.group(1))
        suffix = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
        key = (num, suffix)
        if key > last_key:
            accepted.append((m.start(), m.end(), num, suffix))
            last_key = key
    return accepted


def _chapter_at(chapters: list[tuple[int, str]], pos: int) -> str | None:
    current = None
    for cpos, roman in chapters:
        if cpos <= pos:
            current = roman
        else:
            break
    return current


_NUMBERED_ITEM_RE = re.compile(r"(?:\A|\n)[ \t]*(\d{1,3})\.(?=[\s(])")


def _marker_pieces(text: str) -> list[str] | None:
    """Split on clause markers "(a)", else bare numbered items "1.", else None."""
    for pattern in (_CLAUSE_RE, _NUMBERED_ITEM_RE):
        matches = list(pattern.finditer(text))
        if len(matches) < 2:
            continue
        starts = [m.start() for m in matches] + [len(text)]
        pieces = []
        if matches[0].start() > 0:
            pieces.append(text[: matches[0].start()].strip())
        for i in range(len(matches)):
            piece = text[starts[i] : starts[i + 1]].strip()
            if piece:
                pieces.append(piece)
        return pieces
    return None


def _word_windows(text: str, size: int) -> list[str]:
    words = text.split()
    return [" ".join(words[i : i + size]) for i in range(0, len(words), size)] if words else []


def _split_long_text(text: str, label: str) -> list[str]:
    """Split text exceeding MAX_CHUNK_TOKENS, keeping a "[label]" header on every piece.

    Tries clause markers "(a)" first (the common case for sub-regulations),
    then bare numbered items "1." (schedules and annexed forms often use
    this instead), and falls back to fixed-size word windows so nothing
    stays huge (some schedules have neither and are just long prose). Any
    marker-delimited piece that is itself still oversized (uneven section
    sizes) is further cut into word windows.
    """
    if count_tokens(text) <= MAX_CHUNK_TOKENS:
        return [text]
    header = f"[{label}]"
    raw_pieces = _marker_pieces(text) or _word_windows(text, MAX_CHUNK_TOKENS)
    out = []
    for piece in raw_pieces:
        if count_tokens(piece) > MAX_CHUNK_TOKENS:
            out.extend(_word_windows(piece, MAX_CHUNK_TOKENS))
        else:
            out.append(piece)
    return [f"{header} {p}" for p in out if p]


def _merge_short_pieces(pieces: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Merge (sub_reg_label, text) pieces below MIN_CHUNK_TOKENS into the next one."""
    merged: list[tuple[str, str]] = []
    pending_label: str | None = None
    pending_text = ""
    for label, text in pieces:
        if pending_text:
            text = f"{pending_text}\n\n{text}"
            label = f"{pending_label}-{label}" if pending_label != label else label
        if count_tokens(text) < MIN_CHUNK_TOKENS:
            pending_label, pending_text = label, text
            continue
        merged.append((label, text))
        pending_label, pending_text = None, ""
    if pending_text:
        if merged:
            prev_label, prev_text = merged[-1]
            merged[-1] = (f"{prev_label}-{pending_label}", f"{prev_text}\n\n{pending_text}")
        else:
            merged.append((pending_label, pending_text))
    return merged


def structured_chunks(pages: list[Page], source_file: str, regulation: str) -> list[Chunk]:
    full_text, offsets = _build_full_text(pages)

    chapters = [(m.start(), m.group(1)) for m in _CHAPTER_RE.finditer(full_text)]
    schedule_headers = [(m.start(), m.end(), m.group(1)) for m in _SCHEDULE_RE.finditer(full_text)]
    schedule_start = schedule_headers[0][0] if schedule_headers else len(full_text)

    reg_matches = _monotonic_matches(_REG_RE, full_text, end=schedule_start)

    chunks: list[Chunk] = []

    for i, (start, content_start, num, suffix) in enumerate(reg_matches):
        reg_no = f"{num}{suffix}"
        end = reg_matches[i + 1][0] if i + 1 < len(reg_matches) else schedule_start
        reg_text = full_text[content_start:end].strip()
        chapter = _chapter_at(chapters, start)
        page_start = _page_at(offsets, content_start)
        page_end = _page_at(offsets, max(content_start, end - 1))

        subreg_matches = _monotonic_matches(_SUBREG_RE, reg_text)
        if not subreg_matches:
            pieces = [(None, reg_text)]
        else:
            pieces = []
            for j, (sstart, scontent, snum, _ssuffix) in enumerate(subreg_matches):
                send = subreg_matches[j + 1][0] if j + 1 < len(subreg_matches) else len(reg_text)
                pieces.append((str(snum), reg_text[scontent:send].strip()))

        merged = _merge_short_pieces(pieces) if len(pieces) > 1 else pieces
        merged = [(label, text) for label, text in merged if text]

        for sub_reg, text in merged:
            for n, split_text in enumerate(_split_long_text(text, f"Regulation {reg_no}")):
                chunks.append(
                    Chunk(
                        id=make_id(source_file, reg_no, sub_reg, n),
                        text=split_text,
                        regulation=regulation,
                        reg_no=reg_no,
                        sub_reg=sub_reg,
                        chapter=chapter,
                        page_start=page_start,
                        page_end=page_end,
                        source_file=source_file,
                        chunker="structured",
                    )
                )

    for i, (hstart, hend, label) in enumerate(schedule_headers):
        end = schedule_headers[i + 1][0] if i + 1 < len(schedule_headers) else len(full_text)
        text = full_text[hstart:end].strip()
        if not text:
            continue
        page_start = _page_at(offsets, hstart)
        page_end = _page_at(offsets, max(hstart, end - 1))
        reg_no = f"SCHEDULE_{label}"
        for n, split_text in enumerate(_split_long_text(text, f"Schedule {label}")):
            chunks.append(
                Chunk(
                    id=make_id(source_file, reg_no, None, n),
                    text=split_text,
                    regulation=regulation,
                    reg_no=reg_no,
                    sub_reg=None,
                    chapter=None,
                    page_start=page_start,
                    page_end=page_end,
                    source_file=source_file,
                    chunker="structured",
                )
            )

    return chunks


def fixed_chunks(
    pages: list[Page],
    source_file: str,
    regulation: str,
    size: int = FIXED_CHUNK_SIZE,
    overlap: int = FIXED_CHUNK_OVERLAP,
) -> list[Chunk]:
    full_text, offsets = _build_full_text(pages)
    spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", full_text)]
    if not spans:
        return []

    step = max(1, size - overlap)
    chunks = []
    n = 0
    i = 0
    while i < len(spans):
        window = spans[i : i + size]
        if not window:
            break
        start, end = window[0][0], window[-1][1]
        text = full_text[start:end]
        chunks.append(
            Chunk(
                id=make_id(source_file, None, None, n),
                text=text,
                regulation=regulation,
                reg_no=None,
                sub_reg=None,
                chapter=None,
                page_start=_page_at(offsets, start),
                page_end=_page_at(offsets, max(start, end - 1)),
                source_file=source_file,
                chunker="fixed",
            )
        )
        n += 1
        i += step
    return chunks
