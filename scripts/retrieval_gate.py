"""CI retrieval-regression gate: rebuilds indexes from data/processed/, runs
the production retrieval pipeline (hybrid RRF + rerank, config E from the
Phase 3 ablation) on the dev set, and fails if MRR@10 drops more than
GATE_TOLERANCE below reports/retrieval_baseline.json. No LLM API key needed -
retrieval and reranking are both local models, so quota can't break this gate.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sebisage.config import (
    EVAL_DIR,
    GATE_TOLERANCE,
    K_FUSED,
    PROCESSED_DIR,
    REPORTS_DIR,
)
from sebisage.eval.retrieval_eval import aggregate, evaluate_question
from sebisage.index.dense import build_dense
from sebisage.index.sparse import build_bm25
from sebisage.ingest.schema import Chunk
from sebisage.retrieve.hybrid import retrieve
from sebisage.retrieve.rerank import rerank


def _load_chunks(chunker: str) -> list[Chunk]:
    path = PROCESSED_DIR / f"chunks_{chunker}.jsonl"
    return [Chunk(**json.loads(line)) for line in path.open(encoding="utf-8")]


def main() -> None:
    print("rebuilding structured index from data/processed/ ...")
    chunks = _load_chunks("structured")
    build_dense(chunks, "structured")
    build_bm25(chunks, "structured")

    meta = {c.id: {"source_file": c.source_file, "page_start": c.page_start, "page_end": c.page_end} for c in chunks}
    text_by_id = {c.id: c.text for c in chunks}

    dev = [json.loads(line) for line in (EVAL_DIR / "questions_dev.jsonl").open(encoding="utf-8")]
    results = []
    for q in dev:
        fused = retrieve(q["question"], "structured", k=K_FUSED)
        candidates = [{"id": h["id"], "text": text_by_id[h["id"]]} for h in fused if h["id"] in text_by_id]
        reranked = rerank(q["question"], candidates, k=10)
        ranked = [{"id": r["id"], "score": r["rerank_score"]} for r in reranked]
        results.append(evaluate_question(q, ranked, meta, meta))

    mrr = aggregate(results)["mrr_at_10"]

    baseline = json.loads((REPORTS_DIR / "retrieval_baseline.json").read_text(encoding="utf-8"))
    baseline_mrr = baseline["mrr_at_10"]
    floor = baseline_mrr - GATE_TOLERANCE

    print(f"baseline MRR@10: {baseline_mrr:.4f}  current MRR@10: {mrr:.4f}  floor (tolerance {GATE_TOLERANCE}): {floor:.4f}")
    if mrr < floor:
        print(f"FAIL: retrieval quality regressed beyond tolerance ({mrr:.4f} < {floor:.4f})")
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
