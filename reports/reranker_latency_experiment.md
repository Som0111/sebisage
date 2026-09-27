# Reranker + LLM Pipeline Latency Audit

All retrieval numbers below are from the **dev set** (n=31 answerable, 3 out-of-scope)
unless marked "test" or "published" — the held-out test set was not re-run for this audit.

## 1. Full latency picture (Step 2)

| Stage | p50 latency | Source |
|---|---|---|
| Retrieval only (config E, test) | 4205.6ms | `reports/retrieval_test.json::latency_p50_ms` |
| End-to-end (test) | 35381.5ms | `reports/EVAL_REPORT.md` |
| Gap (LLM pipeline: routing classifier + generation + grounding) | 31175.9ms | derived (35381.5 − 4205.6) |

Retrieval is ~11.9% of end-to-end p50. Optimising only the reranker addresses a small
minority of total latency; the LLM pipeline (mostly generation) is the dominant cost.

## 2. Per-node timing breakdown (Step 3)

Added a `timings: dict[str, float]` field to `AgentState` (merged across nodes via a
custom reducer in `state.py`, since a plain TypedDict field would have each node's
return overwrite the previous node's timing) and instrumented `rewrite_followup`,
`router`, `rag`, `answer_from_web`, and `grounding_check` via a `@_timed(name)`
decorator in `nodes.py`. `timings` is now included in the `/ask` API response.

Ran 5 **real** queries (real Gemini calls, real retrieval — a `GEMINI_API_KEY` was
available in `.env`) directly through `compiled_graph()`, all on the `regulation` route:

| Question | Total (ms) | rewrite_followup | router (incl. retrieval) | rag | grounding_check |
|---|---|---|---|---|---|
| "When must a listed company disclose a material event?" | 25780.1 | 0.0 | 25753.7 | 10.5 | 0.0 |
| "What is a 'connected person' under the PIT Regulations?" | 10908.0 | 0.0 | 7696.2 | 3199.3 | 0.0 |
| "At what shareholding threshold must an acquirer make an open offer?" | 7076.9 | 0.0 | 3909.8 | 3157.2 | 0.0 |
| "For how long must an investment adviser preserve its records?" | 3871.1 | 0.0 | 3849.2 | 14.4 | 0.0 |
| "What must a research analyst maintain records of?" | 4517.2 | 0.0 | 1220.7 | 3290.3 | 0.0 |

Notes on reading this table:
- **The first query's router time (25.75s) is a cold-start artifact, not reranker cost**:
  it's when the embedding, BM25, and cross-encoder models first load into the process
  (visible as "Loading weights..." in the run log). Excluding that one outlier, the
  remaining 4 router times average ~4169ms, which matches `retrieval_test.json`'s
  published retrieval p50 (4205.6ms) almost exactly — a good sanity check that the
  instrumentation is measuring the right thing. **This cold-start cost is real and
  currently invisible in the recorded eval metrics** (which reuse one warm process
  across the whole run) but would hit the very first request after a real server
  restart — worth knowing for deployment, not something this audit fixes.
- **rag was near-instant (10.5ms, 14.4ms) for 2 of the 5 queries** — LLM disk-cache
  hits, not a code path skip. `.cache/llm/` already had 95 entries from prior eval
  runs, and these two questions happen to be exact matches (they're the project's own
  `EXAMPLE_QUESTIONS`). This is real evidence for finding #3 below, not a synthetic one.
- `rewrite_followup` and `grounding_check` were 0.0ms on every query, as expected
  (no conversation history; grounding_check is a pass-through — see Step 3 findings).

## 3. LLM pipeline findings (Step 4)

1. **`rewrite_followup` LLM call when there's no history**: **Already correct, no
   change needed.** The code returns early (`if not history: return {...}`) before
   constructing any prompt or calling the LLM. Confirmed both by reading `nodes.py`
   and by the real timing probe above (0.0ms on every query, since none had prior
   `messages`).

2. **Router LLM classifier frequency**: **No change made.** Per `HUMAN_GUIDE.md`
   Phase 5, 23/34 (68%) of dev questions already resolve via the free
   retrieval-confidence fast path (`REFUSE_THRESHOLD=3.5`); only 11/34 (32%) need the
   LLM classifier, and router accuracy is already 100% on both dev and test.
   Lowering the threshold further could skip the classifier on more borderline
   queries, but since accuracy is already 100% there's no accuracy upside to
   measure, only downside risk on future/unseen queries near the boundary — and the
   task constraint explicitly says not to change this without measuring impact on
   dev, which would require a fresh router-accuracy sweep. Recommending this as
   **future work**, not implementing it now.

3. **Disk cache hit rate**: **No change needed — confirmed working as intended.**
   The 0.0 hit rate in `reports/e2e_test.json` is expected for that specific run
   (23 test questions asked through the full chain for the first time, per
   `HUMAN_GUIDE.md` Phase 7). The real timing probe above shows the cache does help
   in practice once warm: 2 of 5 real queries hit the cache and answered in ~10-15ms
   instead of ~3.2s.

4. **Grounding retry rate**: **Cannot be determined from `reports/grounding_dev.json`
   as currently structured — documented as a gap, no code change made.** That file
   records only the *final* `grounding_flags`/`grounded` value per question (after a
   retry, if one happened), not whether a retry actually fired. `flag_counts: {}` and
   `grounded_pass_rate: 1.0` tell us every dev answer ended up grounded, but not
   whether that took one attempt or two for any given question. Measuring this
   properly would need `generate/answer.py::answer()` to report whether it retried,
   which isn't in scope for this audit (a documentation/instrumentation gap to flag,
   not a bug, and not implemented here to avoid scope creep beyond what's asked).

## 4. Reranker baseline (Step 5a, from `reports/retrieval_test.json` and `config.py` — not re-run)

| Setting | Value |
|---|---|
| Reranker model | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| K_FUSED (candidates fed to reranker) | 20 |
| K_FINAL (chunks returned after reranking) | 5 |
| Retrieval p50 (test) | 4205.6ms |
| Recall@5 (test) | 90.5% |
| MRR@10 (test) | 0.747 |

## 5. K_FUSED experiment (Step 5b, dev set only, n=31 answerable)

Re-ran the same dense+BM25+RRF+rerank pipeline as `scripts/run_ablation.py`'s config E,
varying only `K_FUSED`, over `data/eval/questions_dev.jsonl` (unchanged, same 34
questions used everywhere else — no new random split or seed needed, since retrieval
itself is deterministic given fixed inputs). K_FUSED=20's recomputed numbers
(Recall@5=87.1%, MRR@10=0.762) match `retrieval_ablation_dev.json`'s published config
E exactly, confirming the re-implementation is faithful to the original.

| K_FUSED | Recall@5 (dev) | MRR@10 (dev) | p50 (ms) | p95 (ms) |
|---|---|---|---|---|
| 10 | 93.5% | 0.7535 | 1618.7 | 2112.9 |
| 15 | 90.3% | 0.7677 | 3660.1 | 6358.7 |
| 20 (current) | 87.1% | 0.7619 | 4860.4 | 8379.7 |

(These latencies predate the batch-size fix in Section 6 below — all three ran through
the pre-fix `rerank()`, so they're apples-to-apples with each other and with the
published baseline, but not with a post-fix production run.)

## 6. Batch size finding (Step 5c)

The cross-encoder was called via `model.predict(pairs)` with no explicit `batch_size` —
confirmed by reading `rerank.py` before this audit. Measured median wall-clock time
over 5 runs on a fixed set of 20 real (query, chunk-text) pairs on CPU:

| `batch_size` | Median (5 runs) |
|---|---|
| unset (previous default) | 6063.9ms |
| 8 | **2936.0ms** |
| 16 | 5361.8ms |

`batch_size=8` is ~2x faster than the unset default for this candidate-set size (20),
and clearly faster than 16. Since this only changes how the same model batches the same
inputs internally — not the model, the inputs, or the scores — it carries no retrieval
quality trade-off. **Implemented**: `RERANKER_BATCH_SIZE = 8` added to `config.py`,
`rerank.py::rerank()` now calls `model.predict(pairs, batch_size=RERANKER_BATCH_SIZE)`.
Existing `tests/test_rerank.py` tests (relevance ordering, top-k) still pass unchanged.

## 7. Model init check (Step 5d)

**Confirmed correct, no change needed.** `_get_model()` uses a module-level `global
_model` singleton: `if _model is None: _model = CrossEncoder(RERANKER_MODEL)`, so the
model loads once per process and every `rerank()` call reuses it. Added
`tests/test_rerank.py::test_model_initialised_once_across_calls` to cover this with a
fake `CrossEncoder` constructor and assert it's called exactly once across two
`rerank()` calls.

## 8. Recommendation

**Implemented (safe, no quality trade-off):** `batch_size=8` on the cross-encoder call
— ~2x reranker speedup, same model and same inputs, so retrieval quality is unaffected.

**Not implemented — flagged for a deliberate follow-up, not decided here:**
`K_FUSED` reduction (e.g. to 15, which had both the best dev MRR@10 in the table above
*and* far lower latency than the current K_FUSED=20). On dev, smaller K_FUSED did not
cost any quality — Recall@5 was actually *higher* at K_FUSED=10 (93.5% vs 20's 87.1%)
and MRR@10 was highest at K_FUSED=15 (0.768 vs 20's 0.762). This clears the bar this
task set for recommending a change (same-or-better quality, lower latency). It is
**not implemented in this session** because this project's own established protocol
(`ROADMAP.md`, `HUMAN_GUIDE.md` Phase 3) is: tune on dev, then confirm the chosen
config **once** on the held-out test set before treating it as production — and this
task's constraint explicitly says not to touch the test set here. Changing
`config.py::K_FUSED` without that one-time test confirmation would break the project's
own dev/test discipline. **Recommended next step**: a human/maintainer decision to
spend that one test-set run on K_FUSED=15 (or 10) before changing the default.

## 9. If no change is recommended for K_FUSED right now

The current config (K_FUSED=20) is retained for production, not because the dev data
argues for it — it doesn't — but because changing a config that was originally
selected via "tune on dev, confirm once on test" requires re-doing the "confirm once
on test" step, which is out of scope for this audit by explicit instruction. This is a
process constraint, not a quality judgment: the dev evidence itself favors a smaller
K_FUSED.
