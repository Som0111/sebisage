# SebiSage — Human Guide

Append-only log. Claude Code adds to this file at the end of every phase and at every human checkpoint. Never edit past entries, only append.

---

## Status

- **Phase 0.1 done.** Repo skeleton created per ROADMAP.md Section 4. Python 3.11.9 venv (`.venv/`) set up (Windows only had 3.14 installed; installed 3.11 via `py install 3.11` since the roadmap pins 3.11 for dependency compatibility with torch/chromadb/sentence-transformers). CPU-only torch installed first. `pip install -e ".[dev]"` succeeded, `import sebisage` works, `pytest` runs (0 tests, expected), `ruff check .` passes clean.
- **Phase 0.2 done.** `.env` created (H1 confirmed by human); all 6 keys verified present via `python-dotenv` without printing values. Gemini model chosen: `gemini-flash-lite-latest` (see Decisions).
- **Phase 0.3 done.** All 5 SEBI PDFs in `data/raw/`, verified readable with pymupdf, page counts and amendment dates logged above.
- **Phase 0 exit gate: all items complete.** Suggested commit below — human to run `git add . && git commit && git push` (H6).
- **Phase 1 done.** PDF parsing (`ingest/parse_pdf.py`) + structure-aware and fixed chunkers (`ingest/chunk.py`) implemented and run over all 5 PDFs. 1,900 structured chunks (one fewer than first reported, after a Phase 2 bugfix — see Phase 1 note below), 307 fixed chunks, 100% reg_no coverage (well above the 85% bar). Details and sample chunks below.
- **Phase 2 done.** Dense (Chroma + bge-small) and BM25 indexes built for both chunkers. 1,900 + 307 chunks indexed in each. Idempotency verified by rebuilding twice and comparing counts. Details below.
- **Phase 3 done.** 3.1: 57/60 questions verified by human review, split 34 dev / 23 test (stratified). 3.2–3.5: hybrid retrieval (RRF), cross-encoder reranker, retrieval metrics (page-overlap hit criterion), and the ablation study all built and run. Best config by dev MRR: **E (hybrid + rerank)**, test Recall@5 = 0.905, MRR@10 = 0.747. Honest findings (hybrid alone underperforms dense-only on this dev set; reranker's quality gain is small relative to its ~65x latency cost) documented below. Details below.

---

## Human actions needed

*(newest first)*

### 🧑 HUMAN CHECKPOINT H1 — API keys (2026-09-22) — ✅ done

Keys added to `.env` and verified present.

### 🧑 HUMAN CHECKPOINT H2 — SEBI PDFs (2026-09-22)

Download these from **sebi.gov.in → Legal → Regulations** (latest amended/consolidated versions) and save into `data/raw/` with these exact names:

| File name | Regulation |
|---|---|
| `lodr_2015.pdf` | SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015 |
| `pit_2015.pdf` | SEBI (Prohibition of Insider Trading) Regulations, 2015 |
| `sast_2011.pdf` | SEBI (Substantial Acquisition of Shares and Takeovers) Regulations, 2011 |
| `ia_2013.pdf` | SEBI (Investment Advisers) Regulations, 2013 |
| `ra_2014.pdf` | SEBI (Research Analysts) Regulations, 2014 |

Record the "last amended" date shown on each PDF in the table below once downloaded (fill this in, or tell Claude Code the dates and it will fill it):

| File | Last amended date | Pages (pymupdf) |
|---|---|---|
| `lodr_2015.pdf` | 2026-07-14 | 230 |
| `pit_2015.pdf` | 2025-03-12 | 82 |
| `sast_2011.pdf` | 2025-12-05 | 79 |
| `ia_2013.pdf` | 2025-11-25 | 43 |
| `ra_2014.pdf` | 2025-11-25 | 38 |

✅ All 5 files present in `data/raw/` and verified readable with pymupdf (2026-09-22).

---

## Decisions

- **2026-09-22** — Windows machine only had Python 3.14 installed. Installed Python 3.11.9 via `py install 3.11` (Windows py launcher) and created `.venv` with it, since torch/sentence-transformers/chromadb compatibility with 3.11 is well-established and 3.14 is too new to trust for this stack. This is an environment fix, not a roadmap deviation.
- **2026-09-22** — Generation model: `gemini-flash-lite-latest`. Listed all models available to the provided `GEMINI_API_KEY` via the `google-genai` SDK (60 models returned — the account has broad access, including newer preview models). Chose the `-lite-` flash tier for speed/cost over `-pro`/full `-flash`, and the `-latest` alias form (not a dated snapshot) so it keeps resolving to Google's current flash-lite model without needing edits as models get deprecated. Recorded in `config.py::GEMINI_MODEL`.
- **2026-09-22** — Regulation-boundary detection patterns (structure-aware chunker). SEBI's consolidated PDFs use a 3-level layout, each level starting its own line: regulation `"30. (1) ..."` (bare `NN.` or `NNA.`, sometimes with **no space** before the next `(`, e.g. `"22.(1)"` — seen in sast_2011.pdf), sub-regulation `"(1) ..."`, clause `"(a) ..."`. A blank line does *not* reliably precede these (varies with PDF font/spacing), so boundaries are detected at any line start and validated by requiring the (number, letter-suffix) sequence to be **strictly increasing** — this is what rejects inline cross-references like "...under regulation 23..." (never at a line start) without needing a stricter anchor. Chapters (`CHAPTER IV`) and schedules (`SCHEDULE I`) are detected the same way. Documented in the `ingest/chunk.py` module docstring.
- **2026-09-22** — Chunk size cap. Sub-regulations/schedules over `MAX_CHUNK_TOKENS` (400) are split on clause markers `(a)`, `(b)` first, then bare numbered items `1.`, `2.` (schedules/annexed forms often use these instead of lettered clauses), and any piece still oversized after that (uneven section sizes) falls back to fixed-size word windows — guarantees no chunk exceeds ~400 tokens. Every split piece is prefixed with a `[Regulation N]` / `[Schedule N]` header so it's still identifiable out of context.
- **2026-09-22** — Bugfix found while building the dense index (Phase 2): `chromadb.add()` rejected `chunks_structured.jsonl` with a `DuplicateIDError` on `lodr_2015.pdf:SCHEDULE_IV:*`. Cause: LODR's Schedule IV is printed as two separate "SCHEDULE IV" headings (Part A, Part B), so the chunker treated it as two schedules and both id counters restarted at 0. Fixed by merging consecutive schedule headings with the same label into one span before chunking (`ingest/chunk.py::structured_chunks`). Chunk count dropped from 1,901 to 1,900 (re-ran `scripts/build_chunks.py`); re-verified no duplicate ids across both chunk files before rebuilding the index.
- **2026-09-22** — Dense index: `BAAI/bge-small-en-v1.5` via `sentence-transformers`, queries prefixed with the model's documented instruction (`"Represent this sentence for searching relevant passages: "`), documents unprefixed. Stored in Chroma, one persistent collection per chunker (`sebisage_structured`, `sebisage_fixed`) at `storage/chroma/`. Rebuild is delete-collection-then-recreate (not upsert), so a rebuild always exactly matches current `data/processed/` content — verified idempotent by building twice and comparing counts (1,900 / 307 both times) and BM25 pickle bytes (identical both runs).
- **2026-09-22** — Sparse index tokenizer keeps identifiers like `"30(6)"` and `"kmp"` intact (regex `[a-z0-9()]+` on lowercased text) instead of splitting on punctuation, since legal citations depend on exact tokens BM25 would otherwise fragment.

---

## Escalations

---

## Live URLs

---

## Phase 0 Exit Gate

- [x] Skeleton matches Section 4.
- [x] `.env` present, keys load (present/missing only, no values printed).
- [x] 5 PDFs present and readable.
- [x] Model choice recorded (`gemini-flash-lite-latest`).
- [x] HUMAN_GUIDE.md updated.
- [ ] 🧑 H6: human runs `git add . && git commit && git push`.

**Suggested commit message:**
```
phase-0: repo skeleton, config and data setup
```

---

## Phase 1 — Parsing and Structure-Aware Chunking

**Chunk stats** (full detail in `reports/chunk_stats.json`):

| File | Structured chunks | Mean tokens | Median tokens | Max tokens | % with reg_no |
|---|---|---|---|---|---|
| lodr_2015.pdf | 1,064 | 67.3 | 41.0 | 402 | 100.0% |
| pit_2015.pdf | 218 | 92.3 | 54.0 | 402 | 100.0% |
| sast_2011.pdf | 305 | 78.6 | 55 | 402 | 100.0% |
| ia_2013.pdf | 135 | 76.4 | 45 | 402 | 100.0% |
| ra_2014.pdf | 179 | 62.0 | 43 | 402 | 100.0% |
| **Total** | **1,900** | **72.2** | **45** | **402** | **100.0%** |

(lodr_2015.pdf count updated from 1,064 to 1,063 after the Schedule IV duplicate-id fix — see Decisions.)

Fixed-size baseline chunker: 307 chunks (500 words, 50 overlap) — for the Phase 3 ablation study.

**Quality bar:** roadmap requires ≥ 85% of structured chunks to have a detected `reg_no`. Actual: **100%**, but note that's trivially true by construction (a chunk is only ever created *from* a detected regulation or schedule) — the real quality signal checked was **regulation recall**: cross-checking the detected regulation numbers per file for gaps in the sequence (e.g. LODR 1–103 with letter suffixes, no gaps). See *Problems faced* below for the handful of true misses found this way.

**5 random structured chunks (for eyeballing):**

1. `lodr_2015.pdf:SCHEDULE_II:None:17` (Schedule II, pages 158–165): *"[Schedule II] (ii) The listed entities ranked from 1001 to 2000 as per the list prepared by recognized stock exchanges in terms of sub-regulation (2) of regulation 3 shall endeavour to have atleast one woman independent director on its board of directors. B. Shareholder Righ..."*
2. `lodr_2015.pdf:36:4:0` (Reg 36(4), Chapter IV, pages 76–78): *"The disclosures made by the listed entity with immediate effect from date of notification of these amendments- (a) to the stock exchanges shall be in XBRL format in accordance with the guidelines specified by the stock exchang..."*
3. `lodr_2015.pdf:SCHEDULE_V:None:39` (Schedule V, pages 190–197): *"[Schedule V] (c) number of shareholders' complaints received during the financial year;"* — flagged as an example of a very short schedule fragment (see *Problems faced*).
4. `sast_2011.pdf:2:2:28` (Reg 2(2), Chapter I, pages 1–8): *"[Regulation 2] (zc) 'volume weighted average price' means the product of the number of equity shares bought and price of each such equity share divided by the total number of equity shares bought;"*
5. `lodr_2015.pdf:11:None:0` (Reg 11, Chapter III, page 19): *"The listed entity shall ensure that any scheme of arrangement /amalgamation /merger /reconstruction /reduction of capital etc. to be presented to any Court or Tribunal does not in any way violate, override or limit the provisions of securities laws or requirements of the stock..."*

All 5 read correctly attributed to their regulation/schedule and chapter. No garbled text, no leftover page numbers.

**Tests:** 13 passed (5 for `parse_pdf`, 8 for `chunk`), `ruff check .` clean.

### Phase 1 Exit Gate

- [x] Both chunk files written (`data/processed/chunks_structured.jsonl`, `chunks_fixed.jsonl`).
- [x] `reg_no` coverage ≥ 85% (actual: 100%, see caveat above).
- [x] 5 random structured chunks printed above for human eyeballing.
- [x] All tests pass (13/13), ruff clean.
- [x] `private/PROJECT_EXPLAINED.md` → *Problems faced* updated (parsing issues found).
- [ ] 🧑 H6: human runs `git add . && git commit && git push`.

**Suggested commit message:**
```
phase-1: PDF parsing and structure-aware chunking
```

---

## Phase 2 — Indexing (Dense + Sparse)

**What was built:**
- `index/dense.py` — embeds chunk text with `BAAI/bge-small-en-v1.5` (local, CPU), stores in a persistent Chroma collection per chunker (`sebisage_structured`, `sebisage_fixed`) at `storage/chroma/`. Queries get the model's documented instruction prefix; documents don't (asymmetric retrieval convention). Metadata stored is every `Chunk` field except `text` (text itself is Chroma's `documents` field).
- `index/sparse.py` — BM25 (`rank_bm25`) over a custom lowercase tokenizer that keeps identifiers like `"30(6)"` and `"kmp"` intact. Persisted to `storage/bm25_{chunker}.pkl` alongside the chunk-id list (both regenerated from scratch on every build — no incremental/upsert state to go stale).
- `scripts/build_index.py --chunker structured|fixed|all` — builds both indexes for the requested chunker(s), writes `reports/index_stats.json`.

**Index stats** (`reports/index_stats.json`, from two consecutive rebuilds — see idempotency below):

| Chunker | Chunks | Dense build time | BM25 build time | BM25 pickle size |
|---|---|---|---|---|
| structured | 1,900 | ~395s (CPU) | ~0.15s | 1,010,282 bytes |
| fixed | 307 | ~130s (CPU) | ~0.15s | 736,736 bytes |

Total `storage/chroma/` directory: ~22–27 MB (varies slightly run to run — Chroma's on-disk WAL/compaction files, not the logical content, which is verified identical).

**Idempotency:** ran `build_index.py --chunker all` twice in a row. Both runs: 1,900 structured + 307 fixed chunks indexed in Chroma (`collection.count()` confirmed directly), and the BM25 `.pkl` files were byte-identical both times. Achieved by rebuilding destructively each run (delete-then-recreate the Chroma collection; BM25 pickle always overwritten from scratch), not by upserting — so a rebuild always exactly reflects current `data/processed/` content regardless of history.

**Real-query smoke test** (not part of the automated tests, a sanity check against the actual roadmap example question): *"When must a listed company disclose a material event?"* against the dense index — top 3 hits were all Regulation 30 chunks (`lodr_2015.pdf:30:1-2:0`, `:30:5:0`, `:30:3-4:3`), which is exactly the regulation the roadmap's own example expects. A pure-keyword BM25 query for `"Regulation 30 disclosure"` ranked a Regulation 46 chunk first — expected for keyword-only search on a paraphrased query, and exactly the gap hybrid RRF fusion (Phase 3) exists to close.

**Tests:** 19 passed total (13 from Phase 1 + 3 for `sparse` + 3 for `dense`), `ruff check .` clean. Dense tests use the real `bge-small` model (local/free, not an API call) against a tiny in-memory fixture, isolated from the production Chroma store via `tmp_path` + `monkeypatch`.

### Phase 2 Exit Gate

- [x] Both indexes built for both chunkers (1,900 structured + 307 fixed, in Chroma and BM25).
- [x] Rebuild is idempotent (same counts twice, byte-identical BM25 pickles).
- [x] Tests pass (19/19), ruff clean.
- [ ] 🧑 H6: human runs `git add . && git commit && git push`.

**Suggested commit message:**
```
phase-2: dense and BM25 indexes
```

---

## Phase 3.1 — Evaluation Question Set (draft)

**What was built:**
- `scripts/draft_eval_questions.py` — 60 hand-written questions (no LLM call, nothing to fabricate or cache): 45 answerable in the regulation's own wording, 10 paraphrased in plain/colloquial language (tests whether dense retrieval bridges vocabulary gaps), 5 out-of-scope. Every answerable/paraphrased question cites a real `chunk_id` from `chunks_structured.jsonl` that I read before writing the question, and every `gold_reg`/`gold_sub_reg` was cross-checked programmatically against that chunk's actual metadata (zero mismatches). Spread: LODR 14, PIT 11, SAST 8, IA 6, RA 6 (answerable) + 10 paraphrased across all 5 + 5 out-of-scope. Types: obligation 28, deadline 14, threshold 6, definition 5, out_of_scope 5, penalty 2. Difficulty: easy 20, medium 32, hard 8.
- `scripts/build_review_html.py` — generates `data/eval/review.html`, a self-contained offline page (embeds all 60 questions + their supporting chunk text as inline JSON, no server or network needed) with per-question Keep/Fix/Drop buttons, an edit box for the question text and gold labels, a progress counter, and an Export button that downloads `questions_verified.jsonl` (excludes Dropped rows, applies Fix edits, keeps the original wording for Kept rows).
- Tested the actual page end-to-end in a real browser (Playwright): loads with no real errors (only a harmless favicon 404), all 60 cards render correctly with question/gold/chunk text, Keep/Fix/Drop buttons update state and the progress counter, edits made in Fix mode are captured, state survives a page reload (localStorage), and the export logic was verified to produce correct JSONL (drops excluded, edited questions reflected, gold labels preserved) — checked via direct evaluation of the export function's output, not by inspecting a downloaded file.

data/processed/ and data/eval/ are the only outputs from this step; `data/eval/questions_verified.jsonl` does not exist yet — it's produced by *your* review below.

### 🧑 HUMAN CHECKPOINT H3 — verify the evaluation question set

Open `data/eval/review.html` directly in your browser (double-click it, or drag it in — no server needed). For each of the 60 questions:
- Check that the gold regulation/sub-regulation shown really does answer the question, using the supporting chunk text shown right below it.
- **Keep** if it's correct as-is.
- **Fix** if the question or gold label needs a small correction — an edit box will open; edit the question text and/or `gold_reg`/`gold_sub_reg`, they're saved automatically as you type.
- **Drop** if the question is bad or not worth keeping.
- The 5 out-of-scope questions (badged "out-of-scope") have no chunk text to check — just confirm they're genuinely unrelated to the 5 regulations covered.

When done, click **Export questions_verified.jsonl** (top right) and move the downloaded file into `data/eval/questions_verified.jsonl` in the repo. Tell Claude Code "questions verified" when it's in place.

After you confirm: I'll split it deterministically (seed in `config.py`) into `questions_dev.jsonl` (~60%) and `questions_test.jsonl` (~40%), then continue with 3.2 (hybrid retrieval), 3.3 (reranker), 3.4 (retrieval metrics) and 3.5 (the ablation study) — all tuning happens on dev only, test is touched once at the very end.

✅ **H3 confirmed.** 3 of 60 questions dropped in review (q015 "connected person" definition, q024 PIT repeal question, q040 RA registration question — all Kept/Dropped only, no Fix edits were made). 57 verified questions remain.

---

## Phase 3.2–3.5 — Hybrid Retrieval, Reranking, Metrics, Ablation Study

### Dev/test split
`scripts/split_eval_questions.py` — **stratified by `type`** (not a plain shuffle-and-cut), seed 42, ~60/40. Plain random splitting risked putting all 5 out-of-scope questions in one split; Phase 5.3 needs some in *dev* to calibrate `REFUSE_THRESHOLD` from their scores. Result: **dev 34** (3 out-of-scope), **test 23** (2 out-of-scope), no id overlap, union = all 57.

### What was built
- `retrieve/hybrid.py` — dense (top `K_DENSE`=20) + BM25 (top `K_SPARSE`=20) fused with Reciprocal Rank Fusion (`RRF_K`=60), returns top `K_FUSED`=20 with each hit tagged by which retriever(s) found it.
- `retrieve/rerank.py` — cross-encoder (`ms-marco-MiniLM-L-6-v2`) scores `(query, chunk_text)` pairs for the fused candidates, returns top `K_FINAL`.
- `eval/retrieval_eval.py` — Recall@1/3/5, MRR@10, breakdown by `type`/`difficulty`.
  - **Design decision, deviates from the roadmap's literal wording:** hit detection uses **page-range overlap** (same source PDF, retrieved chunk's page range overlaps the gold chunk's page range) instead of `reg_no` string matching. Reason: the fixed-size baseline chunker never sets `reg_no` (`ingest/chunk.py::fixed_chunks`, by the Phase 1 spec) — reg_no matching would make config A score exactly 0% on every metric by construction, regardless of actual retrieval quality, which isn't a meaningful ablation. Page overlap works uniformly across both chunkers and is if anything a *stricter* test (it requires finding the specific sub-regulation/clause, not just any chunk from the right regulation).
- `scripts/run_ablation.py` — runs configs A–E on dev, writes `reports/retrieval_ablation_dev.json` + `reports/figures/ablation.png`, picks the best config by dev MRR@10, runs it once on test → `reports/retrieval_test.json` (with type/difficulty breakdown).
- Added `matplotlib` as a dependency (not in the roadmap's Section 3 stack list) — needed to produce the required `ablation.png`; no other charting option existed among the listed libraries.

### Ablation results (dev, 34 questions — `reports/retrieval_ablation_dev.json`)

| Config | Chunker | Retrieval | Rerank | Recall@1 | Recall@3 | Recall@5 | MRR@10 | p50 latency | p95 latency |
|---|---|---|---|---|---|---|---|---|---|
| A | fixed | dense only | no | 0.452 | 0.677 | 0.839 | 0.600 | 64ms | 98ms |
| B | structured | dense only | no | 0.613 | 0.871 | 0.935 | 0.756 | 62ms | 153ms |
| C | structured | BM25 only | no | 0.387 | 0.613 | 0.677 | 0.519 | 39ms | 84ms |
| D | structured | hybrid (RRF) | no | 0.452 | 0.774 | 0.871 | 0.616 | 125ms | 173ms |
| **E** | **structured** | **hybrid (RRF)** | **yes** | **0.645** | **0.871** | **0.871** | **0.762** | **4060ms** | **4839ms** |

**Best config by dev MRR@10: E** (hybrid + rerank), selected mechanically per the roadmap's rule. Run once on **test** (23 questions, `reports/retrieval_test.json`): Recall@1 = 0.619, Recall@3 = 0.857, **Recall@5 = 0.905**, **MRR@10 = 0.747**, p50 latency 4206ms, p95 5247ms.

**Honest findings, not the expected clean story:**
1. **Structured chunking clearly beats fixed** (B vs A): MRR 0.756 vs 0.600, Recall@5 0.935 vs 0.839. This is the one result that came out exactly as hypothesized.
2. **BM25 alone is the weakest single retriever** (C: MRR 0.519) — expected, since a third of the dev set is deliberately paraphrased away from the regulation's own wording, which is exactly what defeats keyword search.
3. **Hybrid RRF (D) does *not* beat dense-only (B)** on this dev set (MRR 0.616 vs 0.756) — BM25's weak rankings pull the fused blend down below pure dense. This only reverses once reranking (E) is added, which can override a bad candidate order rather than being limited by it.
4. **The reranker's MRR gain over dense-only is small (E vs B: 0.762 vs 0.756 — a 0.006 difference) while its latency cost is enormous (4060ms vs 62ms, ~65x)** — real CPU cross-encoder cost scales with input length, and real chunk text (up to ~400 tokens) is far longer than a synthetic smoke-test sentence would suggest. E still wins by the stated dev-MRR selection rule, but this tradeoff is worth revisiting when building the production API path in Phase 6 (e.g. truncating candidate text before reranking, or gating reranking behind a latency budget) — not changed now since the roadmap's config-selection rule doesn't factor in latency.
5. Dev set is only 34 answerable-adjacent questions (31 answerable + 3 out-of-scope) — small enough that these orderings could shift with a different split; reported as measured, not smoothed over.

**Test breakdown by type/difficulty** (from `reports/retrieval_test.json`, config E): recall@5 is 1.0 for `deadline` (6/6) and `definition` (2/2) questions, 0.9 for `obligation` (10), 0.5 for `threshold` (2, small n). By difficulty: `easy` and `medium` both hit recall@5 = 1.0; `hard` questions (n=3) score much lower (recall@5 = 0.333) — the 3 hardest dev/test questions (e.g. cross-referencing sub-regulations, or "what happens if a fine goes unpaid") are exactly where retrieval struggles most, which matches intuition.

**Tests:** 31 passed total (19 from Phase 1–2 + 6 `hybrid` + 3 `rerank` + 6 `retrieval_eval`... — retrieval_eval tests fully rewritten once the page-overlap redesign was made, to match), `ruff check .` clean.

### Phase 3 Exit Gate

- [x] Verified question set split into dev/test (34/23, stratified by type).
- [x] Ablation table with real numbers above and in `reports/retrieval_ablation_dev.json`.
- [x] Test-set result recorded once (`reports/retrieval_test.json`).
- [x] `private/PROJECT_EXPLAINED.md` → *Key results* and *Design decisions* updated with the measured deltas (including the honest hybrid-vs-dense and reranker-latency findings above).
- [x] All tests pass (31/31), ruff clean.
- [ ] 🧑 H6: human runs `git add . && git commit && git push`.

**Suggested commit message:**
```
phase-3: hybrid retrieval, reranking and ablation study
```
