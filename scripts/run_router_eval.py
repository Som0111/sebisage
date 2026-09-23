"""Phase 5.3: evaluates the router on all dev questions. Answerable questions
should route "regulation"; out-of-scope questions should route "out_of_scope".
Writes reports/router_dev.json with accuracy and a confusion matrix.
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

load_dotenv()

from sebisage.agent.nodes import router
from sebisage.config import EVAL_DIR, REPORTS_DIR


def main() -> None:
    dev = [json.loads(line) for line in (EVAL_DIR / "questions_dev.jsonl").open(encoding="utf-8")]

    rows = []
    confusion: Counter = Counter()
    for q in dev:
        expected = "out_of_scope" if q["gold_reg"] is None else "regulation"
        print(f"routing {q['id']} ({expected}): {q['question'][:60]}...")
        out = router({"standalone_question": q["question"]})
        predicted = out["route"]
        rows.append({"id": q["id"], "expected": expected, "predicted": predicted, "reason": out["route_reason"], "correct": predicted == expected})
        confusion[(expected, predicted)] += 1

    n = len(rows)
    n_correct = sum(1 for r in rows if r["correct"])
    report = {
        "n_dev": n,
        "accuracy": round(n_correct / n, 4) if n else 0.0,
        "confusion_matrix": {f"expected={e}|predicted={p}": c for (e, p), c in confusion.items()},
        "per_question": rows,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "router_dev.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"router accuracy: {report['accuracy']:.3f} ({n_correct}/{n})")


if __name__ == "__main__":
    main()
