"""Citation validator."""

import re
from dataclasses import dataclass, field

_CITATION_RE = re.compile(r"\[(\d+)\]")
_REG_MENTION_RE = re.compile(r"\b(?:regulation|reg\.?)\s+(\d{1,3}[A-Z]?)\b", re.IGNORECASE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_SOURCE_LINE_RE = re.compile(r"\n\s*Source:", re.IGNORECASE)


@dataclass
class GroundingResult:
    grounded: bool
    flags: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _sentences(answer_text: str) -> list[str]:
    body = _SOURCE_LINE_RE.split(answer_text, maxsplit=1)[0]
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(body.strip()) if s.strip()]


def check_grounding(answer_text: str, context_chunks: list[dict]) -> GroundingResult:
    """`context_chunks`: ordered list of {"id", "text"} matching the [n] numbering (1-indexed)
    used when the prompt's context was built (see generate/answer.py::_format_context)."""
    if answer_text.strip().startswith("INSUFFICIENT_CONTEXT"):
        return GroundingResult(grounded=True, flags=[])

    n_chunks = len(context_chunks)
    flags = []

    cited_numbers = {int(n) for n in _CITATION_RE.findall(answer_text)}
    invalid_numbers = {n for n in cited_numbers if n < 1 or n > n_chunks}
    if invalid_numbers:
        flags.append("invalid_citation")

    uncited_sentences = [s for s in _sentences(answer_text) if not _CITATION_RE.search(s)]
    if uncited_sentences:
        flags.append("uncited_sentence")

    valid_numbers = cited_numbers - invalid_numbers
    cited_text = " ".join(context_chunks[n - 1]["text"] for n in valid_numbers)
    mentioned_regs = {m.group(1) for m in _REG_MENTION_RE.finditer(answer_text)}
    hallucinated_regs = {r for r in mentioned_regs if not re.search(rf"\b{re.escape(r)}\b", cited_text)}
    if hallucinated_regs:
        flags.append("hallucinated_reference")

    return GroundingResult(
        grounded=len(flags) == 0,
        flags=flags,
        details={
            "invalid_citation_numbers": sorted(invalid_numbers),
            "uncited_sentences": uncited_sentences,
            "hallucinated_regs": sorted(hallucinated_regs),
        },
    )
