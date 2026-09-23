"""Recall@k, MRR, ablations.

Hit criterion: a retrieved chunk counts as correct if it comes from the same
source PDF and its page range overlaps the gold answer's page range — not a
reg_no string match. Two reasons: (1) the fixed-size baseline chunker never
sets reg_no (see ingest/chunk.py::fixed_chunks), so reg_no matching would
make it score zero by construction regardless of retrieval quality, which
isn't a fair ablation; (2) page overlap is stricter anyway — it requires
finding the specific sub-regulation/clause, not just any chunk from the
right regulation.
"""

from collections import defaultdict
from dataclasses import dataclass


def overlaps(
    source_file: str,
    page_start: int,
    page_end: int,
    gold_source_file: str,
    gold_page_start: int,
    gold_page_end: int,
) -> bool:
    return source_file == gold_source_file and page_start <= gold_page_end and page_end >= gold_page_start


@dataclass
class QuestionResult:
    id: str
    type: str
    difficulty: str
    answerable: bool
    hit_at_1: bool
    hit_at_3: bool
    hit_at_5: bool
    reciprocal_rank: float
    top_score: float | None


def evaluate_question(question: dict, ranked: list[dict], meta: dict[str, dict], gold: dict[str, dict]) -> QuestionResult:
    """`ranked`: ordered [{"id", "score"}, ...], best first.
    `meta`: retrieved chunk id -> {source_file, page_start, page_end} (any chunker).
    `gold`: structured chunk id -> same fields, used to resolve `question["chunk_id"]`.
    """
    top_score = ranked[0]["score"] if ranked else None
    chunk_id = question.get("chunk_id")
    if chunk_id is None or chunk_id not in gold:
        return QuestionResult(question["id"], question["type"], question["difficulty"], False, False, False, False, 0.0, top_score)

    g = gold[chunk_id]
    hits = [
        bool(meta.get(r["id"]))
        and overlaps(
            meta[r["id"]]["source_file"],
            meta[r["id"]]["page_start"],
            meta[r["id"]]["page_end"],
            g["source_file"],
            g["page_start"],
            g["page_end"],
        )
        for r in ranked
    ]

    rr = next((1.0 / (i + 1) for i, h in enumerate(hits[:10]) if h), 0.0)

    return QuestionResult(
        question["id"],
        question["type"],
        question["difficulty"],
        True,
        any(hits[:1]),
        any(hits[:3]),
        any(hits[:5]),
        rr,
        top_score,
    )


def aggregate(results: list[QuestionResult]) -> dict:
    answerable = [r for r in results if r.answerable]
    n = len(answerable)

    def rate(attr: str) -> float:
        return sum(getattr(r, attr) for r in answerable) / n if n else 0.0

    unanswerable_top_scores = [r.top_score for r in results if not r.answerable and r.top_score is not None]
    return {
        "n_answerable": n,
        "recall_at_1": rate("hit_at_1"),
        "recall_at_3": rate("hit_at_3"),
        "recall_at_5": rate("hit_at_5"),
        "mrr_at_10": sum(r.reciprocal_rank for r in answerable) / n if n else 0.0,
        "n_unanswerable": len(unanswerable_top_scores),
        "unanswerable_top_scores": unanswerable_top_scores,
    }


def breakdown(results: list[QuestionResult], attr: str) -> dict:
    groups: dict[str, list[QuestionResult]] = defaultdict(list)
    for r in results:
        if r.answerable:
            groups[getattr(r, attr)].append(r)
    return {key: aggregate(group) for key, group in groups.items()}
