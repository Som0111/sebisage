"""Phase 3.5 ablation study: configs A-E on dev, best config once on test.

| Config | Chunker    | Retrieval    | Rerank |
|--------|------------|--------------|--------|
| A      | fixed      | dense only   | no     |
| B      | structured | dense only   | no     |
| C      | structured | BM25 only    | no     |
| D      | structured | hybrid (RRF) | no     |
| E      | structured | hybrid (RRF) | yes    |

Writes reports/retrieval_ablation_dev.json, reports/figures/ablation.png,
and reports/retrieval_test.json (best-by-dev-MRR config, run once on test).
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sebisage.config import EVAL_DIR, FIGURES_DIR, K_FUSED, PROCESSED_DIR, REPORTS_DIR
from sebisage.eval.retrieval_eval import (
    QuestionResult,
    aggregate,
    breakdown,
    evaluate_question,
)
from sebisage.index.dense import query_dense
from sebisage.index.sparse import query_bm25
from sebisage.retrieve.hybrid import retrieve
from sebisage.retrieve.rerank import rerank


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def _chunk_meta(chunks: list[dict]) -> dict[str, dict]:
    return {c["id"]: {"source_file": c["source_file"], "page_start": c["page_start"], "page_end": c["page_end"]} for c in chunks}


structured_chunks = _load_jsonl(PROCESSED_DIR / "chunks_structured.jsonl")
fixed_chunks = _load_jsonl(PROCESSED_DIR / "chunks_fixed.jsonl")
META_STRUCTURED = _chunk_meta(structured_chunks)
META_FIXED = _chunk_meta(fixed_chunks)
GOLD = META_STRUCTURED  # question["chunk_id"] always references a structured chunk
TEXT_STRUCTURED = {c["id"]: c["text"] for c in structured_chunks}


def config_a(query: str) -> list[dict]:  # fixed, dense only
    return [{"id": h["id"], "score": -h["distance"]} for h in query_dense(query, "fixed", 10)]


def config_b(query: str) -> list[dict]:  # structured, dense only
    return [{"id": h["id"], "score": -h["distance"]} for h in query_dense(query, "structured", 10)]


def config_c(query: str) -> list[dict]:  # structured, BM25 only
    return [{"id": cid, "score": s} for cid, s in query_bm25(query, "structured", 10)]


def config_d(query: str) -> list[dict]:  # structured, hybrid RRF
    return [{"id": h["id"], "score": h["score"]} for h in retrieve(query, "structured", k=10)]


def config_e(query: str) -> list[dict]:  # structured, hybrid RRF + rerank
    fused = retrieve(query, "structured", k=K_FUSED)
    candidates = [{"id": h["id"], "text": TEXT_STRUCTURED[h["id"]]} for h in fused if h["id"] in TEXT_STRUCTURED]
    return [{"id": r["id"], "score": r["rerank_score"]} for r in rerank(query, candidates, k=10)]


CONFIGS = {
    "A": (config_a, META_FIXED),
    "B": (config_b, META_STRUCTURED),
    "C": (config_c, META_STRUCTURED),
    "D": (config_d, META_STRUCTURED),
    "E": (config_e, META_STRUCTURED),
}


def run_config(fn, meta: dict[str, dict], questions: list[dict]) -> tuple[list[QuestionResult], list[float]]:
    results, latencies_ms = [], []
    for q in questions:
        t0 = time.perf_counter()
        ranked = fn(q["question"])
        latencies_ms.append((time.perf_counter() - t0) * 1000)
        results.append(evaluate_question(q, ranked, meta, GOLD))
    return results, latencies_ms


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, round(p / 100 * (len(s) - 1)))
    return s[idx]


def main() -> None:
    dev = _load_jsonl(EVAL_DIR / "questions_dev.jsonl")
    test = _load_jsonl(EVAL_DIR / "questions_test.jsonl")

    ablation = {}
    for name, (fn, meta) in CONFIGS.items():
        results, latencies = run_config(fn, meta, dev)
        metrics = aggregate(results)
        metrics["latency_p50_ms"] = round(percentile(latencies, 50), 1)
        metrics["latency_p95_ms"] = round(percentile(latencies, 95), 1)
        ablation[name] = metrics
        print(f"{name}: recall@5={metrics['recall_at_5']:.3f} mrr@10={metrics['mrr_at_10']:.3f}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "retrieval_ablation_dev.json").write_text(json.dumps(ablation, indent=2), encoding="utf-8")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    names = list(CONFIGS)
    recall5 = [ablation[n]["recall_at_5"] for n in names]
    mrr = [ablation[n]["mrr_at_10"] for n in names]
    x = range(len(names))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar([i - width / 2 for i in x], recall5, width, label="Recall@5")
    ax.bar([i + width / 2 for i in x], mrr, width, label="MRR@10")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Config")
    ax.set_title("Retrieval ablation (dev set)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "ablation.png", dpi=120)
    plt.close(fig)

    best_name = max(ablation, key=lambda n: ablation[n]["mrr_at_10"])
    best_fn, best_meta = CONFIGS[best_name]
    print(f"best config by dev MRR@10: {best_name}")

    test_results, test_latencies = run_config(best_fn, best_meta, test)
    test_metrics = aggregate(test_results)
    test_metrics["latency_p50_ms"] = round(percentile(test_latencies, 50), 1)
    test_metrics["latency_p95_ms"] = round(percentile(test_latencies, 95), 1)
    test_metrics["config"] = best_name
    test_metrics["breakdown_by_type"] = breakdown(test_results, "type")
    test_metrics["breakdown_by_difficulty"] = breakdown(test_results, "difficulty")
    (REPORTS_DIR / "retrieval_test.json").write_text(json.dumps(test_metrics, indent=2), encoding="utf-8")
    print(f"test: recall@5={test_metrics['recall_at_5']:.3f} mrr@10={test_metrics['mrr_at_10']:.3f}")


if __name__ == "__main__":
    main()
