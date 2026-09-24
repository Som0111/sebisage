"""Runs the end-to-end evaluation and writes reports/e2e_test.json and reports/EVAL_REPORT.md.

Runs the full compiled agent graph (routing + generation + grounding) over
every TEST question for real, then combines that with Phase 3's already-real
retrieval-test numbers, Phase 5's dev router accuracy, and EvalForge scores.
"""

import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

load_dotenv()

from sebisage.agent.graph import compiled_graph
from sebisage.config import (
    COST_PER_1K_INPUT,
    COST_PER_1K_OUTPUT,
    EVAL_DIR,
    REPORTS_DIR,
)
from sebisage.generate.answer import retrieve_context
from sebisage.generate.answer_eval import evaluate_answers
from sebisage.generate.llm import get_cache_stats


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, round(p / 100 * (len(s) - 1)))]


def main() -> None:
    test = [json.loads(line) for line in (EVAL_DIR / "questions_test.jsonl").open(encoding="utf-8")]
    graph = compiled_graph()
    cache_before = get_cache_stats()

    rows = []
    for q in test:
        expected_route = "out_of_scope" if q["gold_reg"] is None else "regulation"
        print(f"running {q['id']} ({expected_route}): {q['question'][:60]}...")
        t0 = time.perf_counter()
        result = graph.invoke({"question": q["question"], "messages": []})
        latency_ms = (time.perf_counter() - t0) * 1000
        usage = result.get("usage_total") or {}
        rows.append(
            {
                "id": q["id"],
                "type": q["type"],
                "expected_route": expected_route,
                "route": result.get("route"),
                "grounded": result.get("grounded"),
                "grounding_flags": result.get("grounding_flags") or [],
                "answer": result.get("answer"),
                "citations": result.get("citations") or [],
                "usage": usage,
                "latency_ms": latency_ms,
            }
        )

    cache_after = get_cache_stats()
    calls_made = (cache_after["hits"] + cache_after["misses"]) - (cache_before["hits"] + cache_before["misses"])
    hits_made = cache_after["hits"] - cache_before["hits"]
    run_cache_hit_rate = round(hits_made / calls_made, 4) if calls_made else 0.0

    # --- router accuracy / refusal precision & recall on test ---
    n = len(rows)
    n_correct_route = sum(1 for r in rows if r["route"] == r["expected_route"])
    tp = sum(1 for r in rows if r["route"] == "out_of_scope" and r["expected_route"] == "out_of_scope")
    fp = sum(1 for r in rows if r["route"] == "out_of_scope" and r["expected_route"] != "out_of_scope")
    fn = sum(1 for r in rows if r["route"] != "out_of_scope" and r["expected_route"] == "out_of_scope")
    refusal_precision = round(tp / (tp + fp), 4) if (tp + fp) else None
    refusal_recall = round(tp / (tp + fn), 4) if (tp + fn) else None

    # --- grounding pass rate (regulation-routed answers only, matches Phase 4 dev methodology) ---
    regulation_rows = [r for r in rows if r["route"] == "regulation"]
    n_grounded = sum(1 for r in regulation_rows if r["grounded"])
    grounding_pass_rate = round(n_grounded / len(regulation_rows), 4) if regulation_rows else None

    # --- latency / tokens / cost ---
    latencies = [r["latency_ms"] for r in rows]
    input_tokens = [r["usage"].get("input_tokens", 0) for r in rows]
    output_tokens = [r["usage"].get("output_tokens", 0) for r in rows]
    costs = [(it / 1000) * COST_PER_1K_INPUT + (ot / 1000) * COST_PER_1K_OUTPUT for it, ot in zip(input_tokens, output_tokens, strict=True)]

    # --- EvalForge scores, for regulation-routed answered questions only ---
    eval_items = []
    for r, q in zip(rows, test, strict=True):
        if r["route"] != "regulation" or not r["answer"] or r["answer"].strip().startswith("INSUFFICIENT_CONTEXT"):
            continue
        context_chunks = retrieve_context(q["question"])
        context_text = "\n\n".join(c["text"] for c in context_chunks)
        eval_items.append({"id": r["id"], "input": f"{q['question']}\n\nContext:\n{context_text}", "output": r["answer"]})
    evalforge_report = evaluate_answers(eval_items)

    router_dev = json.loads((REPORTS_DIR / "router_dev.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "router_dev.json").exists() else {}
    retrieval_test = json.loads((REPORTS_DIR / "retrieval_test.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "retrieval_test.json").exists() else {}

    report = {
        "n_test": n,
        "retrieval_test": {k: retrieval_test.get(k) for k in ("recall_at_1", "recall_at_3", "recall_at_5", "mrr_at_10")},
        "router_accuracy_dev": router_dev.get("accuracy"),
        "router_accuracy_test": round(n_correct_route / n, 4) if n else None,
        "refusal_precision_test": refusal_precision,
        "refusal_recall_test": refusal_recall,
        "grounding_pass_rate_test": grounding_pass_rate,
        "n_regulation_routed": len(regulation_rows),
        "evalforge": evalforge_report,
        "latency_ms_p50": round(percentile(latencies, 50), 1),
        "latency_ms_p95": round(percentile(latencies, 95), 1),
        "mean_input_tokens": round(statistics.mean(input_tokens), 1) if input_tokens else 0,
        "mean_output_tokens": round(statistics.mean(output_tokens), 1) if output_tokens else 0,
        "mean_cost_usd_estimate": round(statistics.mean(costs), 6) if costs else 0,
        "cache_hit_rate_this_run": run_cache_hit_rate,
        "per_question": rows,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "e2e_test.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    _write_markdown_report(report)
    print(f"router_accuracy_test={report['router_accuracy_test']} grounding_pass_rate_test={grounding_pass_rate} evalforge_status={evalforge_report.get('status')}")


def _write_markdown_report(report: dict) -> None:
    lines = ["# SebiSage End-to-End Evaluation Report (test set)\n"]
    lines.append(f"n test questions: {report['n_test']}\n")

    lines.append("## Retrieval (Phase 3, test set)\n")
    for k, v in report["retrieval_test"].items():
        lines.append(f"- {k}: {v}")

    lines.append("\n## Routing\n")
    lines.append(f"- Router accuracy (dev, Phase 5): {report['router_accuracy_dev']}")
    lines.append(f"- Router accuracy (test): {report['router_accuracy_test']}")
    lines.append(f"- Refusal precision (test, n=2 out-of-scope): {report['refusal_precision_test']}")
    lines.append(f"- Refusal recall (test, n=2 out-of-scope): {report['refusal_recall_test']}")

    lines.append("\n## Grounding\n")
    lines.append(f"- Grounding pass rate (test, regulation-routed answers, n={report['n_regulation_routed']}): {report['grounding_pass_rate_test']}")

    lines.append("\n## EvalForge\n")
    ef = report["evalforge"]
    if ef.get("status") == "ok":
        lines.append(f"- n evaluated: {ef['n_items']} (n_failed reported by EvalForge: {ef['n_failed']})")
        for k, v in ef["mean_scores"].items():
            lines.append(f"- mean {k}: {v}")
        lines.append(f"- judged (of {ef['n_items']}): {ef['n_judged']}")
        lines.append(f"- {ef['judge_note']}")
    else:
        lines.append(f"- SKIPPED: {ef.get('reason')}")

    lines.append("\n## Cost, Latency, Cache\n")
    lines.append(f"- Latency p50 / p95: {report['latency_ms_p50']}ms / {report['latency_ms_p95']}ms")
    lines.append(f"- Mean tokens in/out: {report['mean_input_tokens']} / {report['mean_output_tokens']}")
    lines.append(f"- Mean estimated cost per query: ${report['mean_cost_usd_estimate']}")
    lines.append(f"- LLM disk-cache hit rate (this run): {report['cache_hit_rate_this_run']}")

    (REPORTS_DIR / "EVAL_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
