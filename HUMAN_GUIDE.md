# SebiSage — Human Guide

Append-only log. Claude Code adds to this file at the end of every phase and at every human checkpoint. Never edit past entries, only append.

---

## Status

- **Phase 0.1 done.** Repo skeleton created per ROADMAP.md Section 4. Python 3.11.9 venv (`.venv/`) set up (Windows only had 3.14 installed; installed 3.11 via `py install 3.11` since the roadmap pins 3.11 for dependency compatibility with torch/chromadb/sentence-transformers). CPU-only torch installed first. `pip install -e ".[dev]"` succeeded, `import sebisage` works, `pytest` runs (0 tests, expected), `ruff check .` passes clean.
- **Phase 0.2 done.** `.env` created (H1 confirmed by human); all 6 keys verified present via `python-dotenv` without printing values. Gemini model chosen: `gemini-flash-lite-latest` (see Decisions).
- **Phase 0.3 done.** All 5 SEBI PDFs in `data/raw/`, verified readable with pymupdf, page counts and amendment dates logged above.
- **Phase 0 exit gate: all items complete.** Suggested commit below — human to run `git add . && git commit && git push` (H6).
- **Phase 1 done.** PDF parsing (`ingest/parse_pdf.py`) + structure-aware and fixed chunkers (`ingest/chunk.py`) implemented and run over all 5 PDFs. 1,901 structured chunks, 307 fixed chunks, 100% reg_no coverage (well above the 85% bar). Details and sample chunks below.

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
| **Total** | **1,901** | **72.2** | **45** | **402** | **100.0%** |

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
