"""Calls EvalForge /evaluate/batch for answer scoring.

EvalForge's real response shape (confirmed against the live service):
  {"results": [{"scores": {"length":.., "keyword_overlap":.., "format":..,
                            "relevance":..}, "judge": {...}|null,
                "judge_prompt_version": str, "judge_model": str}, ...],
   "total": int, "failed": int}
`judge` can be null (and `failed` > 0) even when `scores` are populated -
EvalForge's judge step can fail independently of the cheap rule-based/
embedding scores, so those are reported as the primary signal and judge
scores only ever as a secondary, caveated one (EvalForge's own judge had
low inter-annotator kappa - see its own docs).
"""

import os
import time

import httpx

BATCH_SIZE = 50  # EvalForge's own hard cap (BatchRequest.items: maxItems=50)
_COLD_START_RETRY_WAIT_S = 60

JUDGE_CAVEAT = (
    "EvalForge's LLM-judge scores are a secondary, caveated signal only - "
    "EvalForge's own inter-annotator kappa for its judge was low. Rule-based "
    "(length, keyword_overlap, format) and embedding (relevance) scores are "
    "the primary signal here."
)


def _config() -> tuple[str, str] | None:
    url = os.environ.get("EVALFORGE_URL")
    key = os.environ.get("EVALFORGE_API_KEY")
    return (url, key) if url and key else None


def evaluate_batch(items: list[dict], timeout: float = 60.0) -> dict | None:
    """`items`: [{"input": str, "output": str}, ...], max BATCH_SIZE.
    One retry after a fixed wait (covers a sleeping free-tier cold start);
    returns None (never raises) if still unreachable."""
    config = _config()
    if config is None:
        return None
    url, key = config

    for attempt in range(2):
        try:
            resp = httpx.post(f"{url}/evaluate/batch", json={"items": items}, headers={"X-API-Key": key}, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError):
            if attempt == 0:
                time.sleep(_COLD_START_RETRY_WAIT_S)
                continue
            return None
    return None


def evaluate_answers(items: list[dict]) -> dict:
    """`items`: [{"id", "input", "output"}, ...] (input = question + retrieved
    context, output = generated answer), any length - batched internally.
    Returns {"status": "ok"|"skipped", ...} - never raises."""
    if not items:
        return {"status": "skipped", "reason": "no items to evaluate"}

    per_item = []
    total_failed = 0
    for i in range(0, len(items), BATCH_SIZE):
        chunk = items[i : i + BATCH_SIZE]
        response = evaluate_batch([{"input": c["input"], "output": c["output"]} for c in chunk])
        if response is None:
            return {"status": "skipped", "reason": "EvalForge unreachable after retry (cold start or quota)"}
        total_failed += response.get("failed", 0)
        for item, result in zip(chunk, response["results"], strict=True):
            per_item.append({"id": item["id"], **result})

    score_keys: set[str] = set()
    for r in per_item:
        score_keys.update(r.get("scores", {}).keys())
    mean_scores = {}
    for key in score_keys:
        values = [r["scores"][key] for r in per_item if key in r.get("scores", {})]
        mean_scores[key] = round(sum(values) / len(values), 4) if values else None

    n_judged = sum(1 for r in per_item if r.get("judge") is not None)

    return {
        "status": "ok",
        "n_items": len(per_item),
        "n_failed": total_failed,
        "mean_scores": mean_scores,
        "n_judged": n_judged,
        "judge_note": JUDGE_CAVEAT,
        "per_item": per_item,
    }
