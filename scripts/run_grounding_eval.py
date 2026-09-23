"""Phase 4 exit gate: grounding pass rate on all dev questions. Writes
reports/grounding_dev.json. Answerable and unanswerable dev questions are
both run through the chain (an unanswerable one should get INSUFFICIENT_CONTEXT,
which check_grounding treats as trivially grounded).
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

load_dotenv()

from sebisage.config import EVAL_DIR, REPORTS_DIR
from sebisage.generate.answer import answer


def main() -> None:
    dev = [json.loads(line) for line in (EVAL_DIR / "questions_dev.jsonl").open(encoding="utf-8")]

    per_question = []
    flag_counts: Counter = Counter()
    n_errors = 0

    for q in dev:
        print(f"answering {q['id']}: {q['question'][:60]}...")
        result = answer(q["question"])
        if result.get("error"):
            n_errors += 1
            per_question.append({"id": q["id"], "type": q["type"], "error": result["error"]})
            continue
        for flag in result["grounding_flags"]:
            flag_counts[flag] += 1
        per_question.append(
            {
                "id": q["id"],
                "type": q["type"],
                "grounded": result["grounded"],
                "flags": result["grounding_flags"],
                "gave_insufficient_context": result["answer"].strip() == "INSUFFICIENT_CONTEXT",
                "is_out_of_scope_question": q["gold_reg"] is None,
            }
        )

    n_answered = len(per_question)
    n_grounded = sum(1 for p in per_question if p.get("grounded"))
    report = {
        "n_dev": len(dev),
        "n_answered": n_answered,
        "n_errors": n_errors,
        "grounded_pass_rate": round(n_grounded / n_answered, 4) if n_answered else 0.0,
        "flag_counts": dict(flag_counts),
        "per_question": per_question,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "grounding_dev.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"grounded pass rate: {report['grounded_pass_rate']:.3f} ({n_grounded}/{n_answered})")


if __name__ == "__main__":
    main()
