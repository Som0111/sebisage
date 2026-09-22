# SebiSage — Human Guide

Append-only log. Claude Code adds to this file at the end of every phase and at every human checkpoint. Never edit past entries, only append.

---

## Status

- **Phase 0.1 done.** Repo skeleton created per ROADMAP.md Section 4. Python 3.11.9 venv (`.venv/`) set up (Windows only had 3.14 installed; installed 3.11 via `py install 3.11` since the roadmap pins 3.11 for dependency compatibility with torch/chromadb/sentence-transformers). CPU-only torch installed first. `pip install -e ".[dev]"` succeeded, `import sebisage` works, `pytest` runs (0 tests, expected), `ruff check .` passes clean.
- **Phase 0.2 done.** `.env` created (H1 confirmed by human); all 6 keys verified present via `python-dotenv` without printing values. Gemini model chosen: `gemini-flash-lite-latest` (see Decisions).
- **Phase 0.3 done.** All 5 SEBI PDFs in `data/raw/`, verified readable with pymupdf, page counts and amendment dates logged above.
- **Phase 0 exit gate: all items complete.** Suggested commit below — human to run `git add . && git commit && git push` (H6).

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
