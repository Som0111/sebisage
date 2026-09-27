# SebiSage — Interview Guide

All numbers below are sourced from `reports/retrieval_test.json`, `reports/e2e_test.json`,
`reports/EVAL_REPORT.md`, and `reports/retrieval_ablation_dev.json`. Where a metric has a
denominator smaller than the full test set, it's stated explicitly — retrieval metrics use
`n_answerable=21` (2 of the 23 test questions are out-of-scope and excluded), not `n_test=23`.

---

## Section 1 — 30-second explanation

SebiSage is a question-answering system over five Indian SEBI securities regulations that
answers with clause-level citations instead of free-floating prose. Regulatory text is a hard
retrieval problem because it mixes exact legal terminology ("material subsidiary") with
paraphrased plain-language questions, and a wrong or uncited answer is worse than no answer at
all. The system was built with dev/test evaluation splits and an ablation study rather than
tuned by feel: on the held-out test set it retrieves the correct clause in its top 5 results
90.5% of the time (n=21 answerable questions), routes questions correctly 100% of the time
(n=23), and every regulation-routed answer passed citation grounding (n=21).

## Section 2 — 90-second technical walkthrough

1. **PDF parsing** — `pymupdf` extracts text per page, stripping repeated headers/footers.
2. **Structure-aware chunking** — a regex parser detects regulation/sub-regulation/clause
   boundaries so every chunk carries a real `reg_no`, which is what makes clause-level citation
   possible at all.
3. **Dense + BM25 retrieval** — `bge-small-en-v1.5` embeddings and BM25 run in parallel over the
   same chunks.
4. **Reciprocal Rank Fusion** — merges the two ranked lists without hand-tuning a blend weight.
5. **Cross-encoder reranking** — `ms-marco-MiniLM-L-6-v2` rescores the fused top-20 candidates
   for the final top-5.
6. **LLM generation** — Gemini answers only from the retrieved context, citing `[n]` per
   sentence, and returns `INSUFFICIENT_CONTEXT` verbatim if the context doesn't support an
   answer.
7. **Grounding validator** — checks every citation is real and every claim traces to one, with
   one automatic retry before returning `grounded: false`.
8. **LangGraph routing** — a 3-tier cost-ordered router (keywords → retrieval confidence → LLM
   classifier) sends each question to regulation lookup, live web search, or refusal.
9. **FastAPI + Streamlit** — streaming API with guardrails and cost tracking, backing a chat UI
   with a citations panel.

## Section 3 — Three strongest engineering decisions

### 1. Structure-aware chunking

- **Problem it solves:** fixed-size chunking has no natural `regulation_no` to cite — clause-level
  citation is impossible without knowing which regulation/sub-regulation a chunk came from.
- **What was tried / alternatives:** a fixed-size word-window chunker (500 words, 50 overlap) was
  built as the ablation baseline (config A).
- **Chosen approach:** a regex-based parser detects regulation/sub-regulation/clause boundaries at
  line starts, validated by requiring the (number, letter-suffix) sequence to be strictly
  increasing — this is what rejects inline cross-references like "...under regulation 23..."
  without a stricter anchor.
- **Measured evidence:** dense-only retrieval with structured chunking (config B) hit Recall@5
  93.5% vs. 83.9% for fixed-size (config A) on the dev set (`reports/retrieval_ablation_dev.json`).
- **Honest trade-off:** one PIT regulation (regulation 14) is missed by the chunker due to a
  nested-bracket amendment pattern the regex doesn't handle — a known, accepted gap.

### 2. Hybrid retrieval + cross-encoder reranking

- **Problem it solves:** regulation text has exact-phrase/defined-term queries where lexical
  search wins, and paraphrased queries where dense embeddings win — neither retriever alone
  covers both.
- **What was tried / alternatives:** dense-only (B), BM25-only (C), and hybrid RRF without
  reranking (D) were all measured on dev before adding the reranker (E).
- **Chosen approach:** dense + BM25 fused via Reciprocal Rank Fusion, then a cross-encoder
  reranks the fused top-20 candidates for the final top-5.
- **Measured evidence:** config E (hybrid + rerank) reached dev MRR@10 0.762, the best of the
  five configs, and was confirmed on test at MRR@10 0.747, Recall@5 90.5% (n=21 answerable,
  `reports/retrieval_test.json`).
- **Honest trade-off:** on this dev set, hybrid RRF **without** reranking (config D, MRR@10
  0.616) actually underperformed dense-only (config B, MRR@10 0.756) — see Section 4. Reranking
  is also expensive: dev p50 latency jumped from 125.3ms (D) to 4059.7ms (E), a ~32x increase.

### 3. Citation grounding validator

- **Problem it solves:** instructing an LLM to cite sources in a prompt doesn't guarantee it
  won't hallucinate a citation or a regulation number.
- **What was tried / alternatives:** a single generation pass with citation instructions only,
  no post-hoc check.
- **Chosen approach:** every `[n]` is checked against the real context, every sentence must carry
  a citation, and every regulation number mentioned must appear in a cited chunk; one automatic
  retry runs before the answer is returned with `grounded: false`.
- **Measured evidence:** 100% grounding pass rate on the 21 regulation-routed test answers
  (`reports/e2e_test.json::grounding_pass_rate_test`). Traced during development: some refusals
  were genuine retrieval misses (the correct chunk never reached the top 5), not lazy refusals —
  the validator does its job even when retrieval is the actual weak link.
- **Honest trade-off:** 100% grounding pass rate does not mean 100% correct — see Section 5, Q9.

## Section 4 — Important experimental findings (honest)

- **Structured dense (B) outperformed hybrid RRF without reranking (D) on dev MRR**
  (0.756 vs. 0.616). Hybrid RRF alone is not automatically better than a strong dense baseline —
  BM25's weaker rankings pulled the fused blend down.
- **Reranking (E) gave the best dev MRR (0.762) but at a real latency cost**: dev p50 latency
  went from ~125ms (config D) to ~4060ms (config E) — about 32x.
- **End-to-end p50 (~35,382ms) is far higher than retrieval p50 (~4,206ms) on the test set** —
  the gap is the LLM generation + routing + grounding pipeline, not retrieval.
- **The production config was chosen by dev MRR and evaluated once on the held-out test set.**
  Dev was not re-examined after test was run — no test-set peeking.
- **Hard-difficulty questions (n=3) show Recall@5 of only 33.3%** — a small sample, but an honest
  limitation worth naming rather than smoothing over.

## Section 5 — Likely interviewer questions

**1. Why BM25 if embeddings already exist?**
- Embeddings miss exact-phrase/defined-term matches (e.g. "material subsidiary") that lexical
  search catches reliably.
- BM25 alone (config C) scored worst of all five configs on dev (MRR@10 0.519) — it's a
  complement to dense, not a replacement.
- Regulatory text is full of stable, reusable terms that keyword search is naturally good at.

**2. Why RRF instead of weighted score fusion?**
- RRF needs no hand-tuned blend weight between dense and BM25 score scales, which aren't
  directly comparable.
- It's rank-based, so it's robust to one retriever's scores being on a wildly different scale.
- Simpler to reason about and reproduce than tuning a weight on a 34-question dev set.

**3. Why cross-encoder reranking?**
- It jointly attends over the (query, chunk) pair instead of comparing independent embeddings,
  which recovers ranking quality RRF alone can't.
- Measured dev MRR@10 gain from 0.616 (config D) to 0.762 (config E).
- Bounded cost — it only scores the already-fused top-20 candidates, not the whole corpus.

**4. Why not rerank the entire corpus?**
- Reranking is O(n) cross-encoder forward passes per query — reranking 1,900+ chunks per query
  would be far too slow for an interactive system.
- Reranking the fused top-20 gets most of the quality gain at a fixed, bounded cost.
- The retrieval-quality ceiling is set by whether the fused set even contains the right chunk;
  reranking only reorders what's already there.

**5. Why structure-aware chunking instead of fixed-size?**
- Fixed-size chunks have no natural `reg_no` — clause-level citation is impossible without one.
- Dev Recall@5 improved from 83.9% (fixed, config A) to 93.5% (structured, config B) even before
  adding hybrid retrieval or reranking.
- Legal text has natural clause boundaries; splitting mid-clause loses semantic units the
  retriever depends on.

**6. How was the refusal threshold chosen?**
- The top cross-encoder rerank score was computed for every dev question, answerable and
  out-of-scope.
- Out-of-scope scores topped out at 3.01; answerable scores were mostly well above that.
- `REFUSE_THRESHOLD=3.5` was set comfortably above every observed out-of-scope score, so the
  fast path can't let an out-of-scope question through unchecked.

**7. How do you prevent hallucinations?**
- The prompt requires citations on every factual sentence and an exact `INSUFFICIENT_CONTEXT`
  reply when context doesn't support an answer.
- A post-hoc grounding validator checks every citation is real and every mentioned regulation
  number appears in a cited chunk.
- One automatic retry runs before an answer is ever returned as ungrounded.

**8. How do you evaluate grounding?**
- `check_grounding()` flags three failure modes: invalid citation, uncited sentence, and
  hallucinated regulation reference.
- Grounding pass rate is measured on all regulation-routed test answers (n=21), not just a
  hand-picked sample.
- `INSUFFICIENT_CONTEXT` responses count as trivially grounded (no citation to hallucinate), so
  the number is read alongside refusal rate, not in isolation.

**9. Why is 100% grounding pass rate not sufficient evidence of correctness?**
- Grounding validates that citations exist and are internally consistent; it does not validate
  that the retrieved chunk is actually the best possible answer to the question.
- A confidently-cited but retrieval-mismatched answer can still pass grounding.
- EvalForge's relevance score (~0.817 mean, embedding-based) covers this gap partially, but is a
  secondary signal, not a full correctness check.

**10. What does Recall@5 mean in this project specifically?**
- The fraction of answerable test questions (n=21) where the correct chunk's page range appears
  somewhere in the top 5 retrieved results.
- Hit detection uses page-range overlap, not `reg_no` string matching, so it applies uniformly
  across the fixed and structured chunkers in the ablation.
- On test: 90.5%.

**11. Why is the test set small?**
- 57 hand-verified questions total (60 drafted, 3 dropped in human review), split 34 dev / 23
  test — building and manually verifying each question against real regulation text is slow.
- Small-n metrics are reported as measured, not smoothed with confidence intervals that would
  overstate precision.
- It's an explicit, stated limitation rather than a hidden one.

**12. What is the latency bottleneck?**
- Retrieval-only p50 on test is ~4,206ms, dominated by cross-encoder reranking over the fused
  candidate set.
- End-to-end p50 on test is ~35,382ms, dominated by LLM generation (plus routing and grounding).
- These are two different numbers measuring two different stages — the ~31 second gap is
  generation, not retrieval.

**13. What happens if SEBI amends a regulation?**
- The indexed PDFs are dated snapshots (last-amended dates recorded in `HUMAN_GUIDE.md`); the
  system doesn't detect or ingest amendments automatically.
- Re-running `scripts/build_chunks.py` + `scripts/build_index.py` against updated PDFs rebuilds
  the index from scratch, destructively, so it always exactly reflects whatever PDF is given.
- Indexing SEBI's master circulars with version dates is on the roadmap, not yet built.

**14. Why LangGraph instead of a normal chain?**
- Different question types need genuinely different handling — regulation lookup, live web
  search, and refusal — which a single fixed chain can't route between.
- The router is 3-tier and cost-ordered (free keyword rules → retrieval-confidence fast path →
  LLM classifier), keeping routing cost near zero on the common path — a plain chain has no
  place to put that logic.
- Follow-up question rewriting needs conversation state across turns, which a stateless chain
  doesn't naturally carry.

**15. What would you improve next?**
- Query decomposition for questions spanning two regulations.
- Parent-child retrieval (retrieve at sub-regulation granularity, pass the whole regulation as
  context).
- A second human annotator on the eval set, to measure inter-annotator agreement.
- LoRA fine-tuning the embedding model on regulation Q&A pairs, measuring the retrieval gain.

## Section 6 — Resume bullets

### Conservative variant

- Built a RAG system over 5 SEBI securities regulations that answers with clause-level citations,
  covering PDF parsing, structure-aware chunking, hybrid retrieval, and citation-grounded
  generation.
- Measured retrieval and end-to-end quality on a held-out test set: 90.5% Recall@5 (n=21
  answerable questions), 100% router accuracy (n=23), and 100% grounding pass rate on
  regulation-routed answers (n=21).
- Deployed the system locally via Docker with a FastAPI backend, Streamlit UI, and a CI pipeline
  that gates merges on a retrieval-regression check.

### Technical variant

- Designed and evaluated a 5-configuration retrieval ablation (fixed vs. structured chunking;
  dense-only, BM25-only, hybrid RRF, and hybrid RRF + cross-encoder reranking), selecting the
  production config by dev-set MRR@10 (0.762) and confirming it once on a held-out test set
  (MRR@10 0.747, Recall@5 90.5%, n=21 answerable questions).
- Built a citation-grounding validator that checks every LLM-generated citation against retrieved
  context and flags hallucinated regulation references, reaching a 100% pass rate on
  regulation-routed test answers (n=21) with one automatic retry on failure.
- Implemented a LangGraph agent with a 3-tier cost-ordered router (keyword rules → retrieval
  confidence → LLM classifier), reaching 100% routing accuracy on 23 test questions while
  resolving most queries without an LLM classifier call.

### ML/IR-heavy variant

- Ran a controlled retrieval ablation across chunking strategy and retriever fusion (structure-
  aware vs. fixed-size chunking; dense embeddings, BM25, Reciprocal Rank Fusion, and cross-encoder
  reranking), finding that RRF alone underperformed a strong dense baseline on dev MRR@10 (0.616
  vs. 0.756) and that reranking was the component that closed the gap (0.762).
- Selected the production retrieval config by dev MRR@10 and evaluated it once on a held-out test
  set (Recall@1/3/5 = 61.9%/85.7%/90.5%, MRR@10 = 0.747, n=21 answerable questions) with no
  test-set peeking during tuning.
- Quantified the retrieval/generation latency split end-to-end (retrieval p50 ~4.2s dominated by
  cross-encoder reranking vs. end-to-end p50 ~35.4s dominated by LLM generation) to characterize
  the system's actual latency budget rather than reporting a single blended number.

---

## Verification notes

Every metric above traces to a `reports/` file:
- `retrieval_test.json`: n_answerable=21, n_unanswerable=2, recall_at_1/3/5, mrr_at_10,
  latency_p50_ms=4205.6, latency_p95_ms=5247.0, breakdown_by_difficulty.hard
  (n_answerable=3, recall_at_5=0.333).
- `retrieval_ablation_dev.json`: mrr_at_10 and latency_p50_ms for configs A–E.
- `e2e_test.json`: n_test=23, n_regulation_routed=21 (so n_unanswerable_in_test = 23 − 21 = 2,
  matching refusal n=2 out-of-scope), router_accuracy_test=1.0, grounding_pass_rate_test=1.0,
  mean_cost_usd_estimate=0.00032, evalforge.n_items=17/n_failed=17/n_judged=0,
  evalforge.mean_scores (relevance=0.8172, etc.).
- `EVAL_REPORT.md`: latency p50/p95 = 35381.5ms/79836.1ms (end-to-end).

No metric in this guide could not be verified from a report file.
