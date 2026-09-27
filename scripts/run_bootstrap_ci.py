"""Adds bootstrap 95% CIs around the already-published test-set retrieval
metrics (reports/retrieval_test.json). Re-runs config E (the winning config,
local dense+BM25+rerank, no LLM calls) over the test set only to recover the
per-question hit/reciprocal-rank values the published aggregate doesn't store,
then verifies the recomputed aggregate matches the published one exactly
before writing the CI report -- this never replaces retrieval_test.json.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sebisage.config import EVAL_DIR, K_FUSED, PROCESSED_DIR, REPORTS_DIR
from sebisage.eval.bootstrap import bootstrap_ci
from sebisage.eval.retrieval_eval import aggregate, evaluate_question
from sebisage.retrieve.hybrid import retrieve
from sebisage.retrieve.rerank import rerank

N_ITER = 1000
SEED = 42


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def _chunk_meta(chunks: list[dict]) -> dict[str, dict]:
    return {c["id"]: {"source_file": c["source_file"], "page_start": c["page_start"], "page_end": c["page_end"]} for c in chunks}


def main() -> None:
    structured_chunks = _load_jsonl(PROCESSED_DIR / "chunks_structured.jsonl")
    meta_structured = _chunk_meta(structured_chunks)
    text_structured = {c["id"]: c["text"] for c in structured_chunks}

    test = _load_jsonl(EVAL_DIR / "questions_test.jsonl")

    results = []
    for q in test:
        fused = retrieve(q["question"], "structured", k=K_FUSED)
        candidates = [{"id": h["id"], "text": text_structured[h["id"]]} for h in fused if h["id"] in text_structured]
        ranked = [{"id": r["id"], "score": r["rerank_score"]} for r in rerank(q["question"], candidates, k=10)]
        results.append(evaluate_question(q, ranked, meta_structured, meta_structured))

    recomputed = aggregate(results)
    published = json.loads((REPORTS_DIR / "retrieval_test.json").read_text(encoding="utf-8"))
    for key in ("n_answerable", "recall_at_1", "recall_at_5", "mrr_at_10"):
        if round(recomputed[key], 4) != round(published[key], 4):
            raise SystemExit(
                f"Recomputed {key}={recomputed[key]} does not match published retrieval_test.json {key}={published[key]}. "
                "Stopping without writing a bootstrap report -- investigate before proceeding."
            )

    answerable = [r for r in results if r.answerable]
    hits_at_1 = [r.hit_at_1 for r in answerable]
    hits_at_5 = [r.hit_at_5 for r in answerable]
    rr = [r.reciprocal_rank for r in answerable]

    def metric_block(hits: list[bool | float]) -> dict:
        mean = sum(hits) / len(hits)
        lower, upper = bootstrap_ci(hits, n_iter=N_ITER, seed=SEED)
        return {"mean": round(mean, 4), "ci_95_lower": round(lower, 4), "ci_95_upper": round(upper, 4)}

    report = {
        "seed": SEED,
        "n_iter": N_ITER,
        "n_answerable_test": len(answerable),
        "note": "95% bootstrap CI (rough uncertainty estimate; small sample, n<25 means wide intervals).",
        "recall_at_1": metric_block(hits_at_1),
        "recall_at_5": metric_block(hits_at_5),
        "mrr_at_10": metric_block(rr),
    }

    (REPORTS_DIR / "retrieval_bootstrap_ci.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
