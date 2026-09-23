"""Phase 4.4: runs the answer chain on 10 dev questions (mix of types) for the
human spot-check checkpoint. Writes reports/answer_samples.md.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

load_dotenv()

from sebisage.config import EVAL_DIR, PROCESSED_DIR, REPORTS_DIR
from sebisage.generate.answer import answer

# Hand-picked for type coverage: 2 deadline, 3 obligation, 2 threshold,
# 1 out_of_scope, 1 definition, 1 penalty.
SAMPLE_IDS = ["q019", "q039", "q035", "q047", "q030", "q023", "q027", "q057", "q016", "q010"]


def main() -> None:
    dev = {r["id"]: r for r in (json.loads(line) for line in (EVAL_DIR / "questions_dev.jsonl").open(encoding="utf-8"))}
    chunk_text = {c["id"]: c["text"] for c in (json.loads(line) for line in (PROCESSED_DIR / "chunks_structured.jsonl").open(encoding="utf-8"))}

    lines = ["# Answer Samples — Phase 4.4 Human Spot-Check\n"]
    lines.append(
        "For each answer: mark ✅ correct, ⚠️ partially correct, or ❌ wrong directly below the "
        "answer, then tell Claude Code \"spot-check done\".\n"
    )

    for qid in SAMPLE_IDS:
        q = dev[qid]
        print(f"answering {qid}: {q['question']}")
        result = answer(q["question"])

        lines.append(f"\n---\n\n## {qid} ({q['type']}, {q['difficulty']}{', paraphrased' if q.get('paraphrased') else ''})\n")
        lines.append(f"**Question:** {q['question']}\n")
        lines.append(f"**Gold:** `{q['gold_reg']}` sub_reg `{q['gold_sub_reg']}`\n")

        if result.get("error"):
            lines.append(f"**ERROR:** {result['error']}\n")
            continue

        lines.append(f"**Answer:**\n\n{result['answer']}\n")
        lines.append(f"**Grounded:** {result['grounded']} (flags: {result['grounding_flags'] or 'none'})\n")
        lines.append(f"**Usage:** {result['usage']} | **Latency:** {result['latency_ms']:.0f}ms\n")

        if result["citations"]:
            lines.append("**Cited chunk text:**\n")
            for cid in result["citations"]:
                text = chunk_text.get(cid, "(not found)")
                lines.append(f"- `{cid}`: {text[:400]}{'...' if len(text) > 400 else ''}\n")
        else:
            lines.append("**Cited chunk text:** (none)\n")

        lines.append("\n**Human mark:** _(✅/⚠️/❌)_\n")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "answer_samples.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote reports/answer_samples.md ({len(SAMPLE_IDS)} questions)")


if __name__ == "__main__":
    main()
