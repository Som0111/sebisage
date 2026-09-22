"""Chunk dataclass: id, text, regulation, reg_no, page, source_file."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    regulation: str
    reg_no: str | None
    sub_reg: str | None
    chapter: str | None
    page_start: int
    page_end: int
    source_file: str
    chunker: str


def make_id(source_file: str, reg_no: str | None, sub_reg: str | None, n: int) -> str:
    """Deterministic id: same input gives the same id on every run."""
    return f"{source_file}:{reg_no}:{sub_reg}:{n}"
