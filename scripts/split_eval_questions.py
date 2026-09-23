"""Splits questions_verified.jsonl into questions_dev.jsonl (~60%) and
questions_test.jsonl (~40%), deterministically (seeded).

Stratified by `type` (not a plain shuffle-and-cut) so that small categories
-- especially the 5 out-of-scope questions -- land in both splits instead of
risking all of them falling into test. Dev needs some: Phase 5.3 sets
REFUSE_THRESHOLD from unanswerable-question scores measured on dev.
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sebisage.config import EVAL_DEV_FRACTION, EVAL_DIR, EVAL_SPLIT_SEED


def main() -> None:
    rows = [json.loads(line) for line in (EVAL_DIR / "questions_verified.jsonl").open(encoding="utf-8")]

    by_type = defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r)

    rng = random.Random(EVAL_SPLIT_SEED)
    dev, test = [], []
    for qtype in sorted(by_type):
        group = by_type[qtype]
        rng.shuffle(group)
        n_dev = round(len(group) * EVAL_DEV_FRACTION)
        dev.extend(group[:n_dev])
        test.extend(group[n_dev:])

    rng.shuffle(dev)
    rng.shuffle(test)

    for name, split in [("questions_dev.jsonl", dev), ("questions_test.jsonl", test)]:
        with (EVAL_DIR / name).open("w", encoding="utf-8") as f:
            for r in split:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"dev: {len(dev)}, test: {len(test)}, total: {len(rows)}")


if __name__ == "__main__":
    main()
