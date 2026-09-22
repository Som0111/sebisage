# SebiSage — Agentic RAG over SEBI Regulations
## Claude Code Execution Roadmap

---

## 0. What This Project Is

SebiSage answers questions about Indian securities regulations (SEBI) with **clause-level citations**.

A user asks: *"When must a listed company disclose a material event?"*
SebiSage answers with the rule **and** cites the exact source, e.g. *"Reg 30(6), SEBI LODR Regulations 2015"*.

Core pieces:
- **Structure-aware ingestion** — PDFs split by Regulation / sub-regulation, not by fixed character count.
- **Hybrid retrieval** — dense vectors (Chroma) + keyword search (BM25), fused with Reciprocal Rank Fusion, then a cross-encoder reranker.
- **Grounded generation** — LangChain chain that must cite retrieved chunks; a grounding check rejects uncited claims.
- **LangGraph agent** — routes each question to: regulation lookup (RAG), recent-circular web search (sebi.gov.in only), or a polite out-of-scope refusal. Handles follow-up questions with conversation memory.
- **FastAPI** with streaming responses, input guardrails, and per-query token/cost tracking.
- **Langfuse** tracing for every agent step.
- **Evaluation** — retrieval metrics (Recall@k, MRR) on a human-verified question set, plus answer scoring through **EvalForge** (sibling project).
- **Streamlit UI** — question box, streamed answer, citations panel with the source text.
- **Docker + GitHub Actions CI + Hugging Face Spaces** deployment.

**Disclaimer (must appear in README and UI):** SebiSage is an educational project, not legal or investment advice.

---

## 1. Rules for Claude Code (read before every session)

1. **Phase-driven, not date-driven.** Finish a phase fully before starting the next.
2. **Every subphase ≤ 20 minutes.** If one grows larger, split it and note the split in HUMAN_GUIDE.md.
3. **Loop per subphase:** implement → test → self-review → fix → re-test → tick checklist.
4. **Self-correct at most 2 times.** If still broken, STOP and write an escalation note in HUMAN_GUIDE.md.
5. **NEVER run `git commit` or `git push`.** The human commits. At each phase end, print the suggested commit message and stop.
6. **Never fabricate** human labels, metrics, test results, URLs or quotes from regulations. Every number in docs must come from a file in `reports/`.
7. **No AI attribution** in any file, commit message suggestion, or comment.
8. **Secrets only in `.env`.** Never print a key. `.env` is in `.gitignore`.
9. **Free tiers only.** Cache every LLM call on disk (see Phase 4.1) so reruns cost zero quota.
10. **Prefer simple.** No extra frameworks beyond those listed in Section 3.
11. **At the end of every phase:** update HUMAN_GUIDE.md (append only) and update `private/PROJECT_EXPLAINED.md` sections marked for that phase with **real** outcomes.
12. **Model names change.** Never hardcode a model name outside `config.py`. At Phase 0, check which Gemini models are currently available on the free tier and record the choice.

---

## 2. Human Sections — Quick Index

Every place the human must act is marked `🧑 HUMAN CHECKPOINT`. Claude Code stops at each one.

| # | Phase | What the human does |
|---|---|---|
| H1 | 0.2 | Create API keys (Gemini, Langfuse) and paste into `.env` |
| H2 | 0.3 | Download SEBI regulation PDFs into `data/raw/` |
| H3 | 3.1 | Verify / correct the evaluation question set |
| H4 | 4.4 | Spot-check 10 generated answers for correctness |
| H5 | 9.3 | Create Hugging Face Space and add secrets |
| H6 | End of every phase | Review, then run `git add . && git commit && git push` |

---

## 3. Tech Stack (fixed)

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | Same as other projects |
| Orchestration | LangChain + LangGraph | Top JD skills (82% / 49%) |
| LLM | Gemini (free tier) via `langchain-google-genai` | Free; already used in EvalForge |
| Embeddings | `BAAI/bge-small-en-v1.5` (local, sentence-transformers) | No API quota, strong on retrieval benchmarks, small |
| Vector DB | Chroma (persistent, local) | Free, no server, easy to ship in Docker |
| Keyword search | `rank_bm25` | Legal text is full of exact terms ("Reg 30", "KMP") that dense search misses |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` (local) | Free, CPU-friendly |
| PDF parsing | `pymupdf` | Fast, keeps page numbers |
| Web search tool | `ddgs` (DuckDuckGo) restricted to `site:sebi.gov.in` | No key needed |
| API | FastAPI + SSE streaming | 76% of JDs |
| Observability | Langfuse (free cloud) | Top-10 JD skill |
| UI | Streamlit | Fast, demo-friendly |
| Tests | pytest, ruff | Same as other projects |
| Deploy | Docker → Hugging Face Spaces (free CPU, 16 GB RAM) | Render free tier (512 MB) cannot hold torch + models |

---

## 4. Target Project Structure

```
sebisage/
├── src/sebisage/
│   ├── config.py            all paths, model names, thresholds, top-k values
│   ├── ingest/
│   │   ├── parse_pdf.py     PDF → pages with page numbers
│   │   ├── chunk.py         structure-aware + fixed-size chunkers
│   │   └── schema.py        Chunk dataclass (id, text, regulation, reg_no, page, source_file)
│   ├── index/
│   │   ├── dense.py         Chroma build/load
│   │   └── sparse.py        BM25 build/load (pickled)
│   ├── retrieve/
│   │   ├── hybrid.py        dense + BM25 + RRF fusion
│   │   └── rerank.py        cross-encoder reranker
│   ├── generate/
│   │   ├── llm.py           Gemini wrapper + disk cache + token counting
│   │   ├── prompts.py       versioned prompts
│   │   ├── answer.py        LangChain answer chain with citations
│   │   └── grounding.py     citation validator
│   ├── agent/
│   │   ├── state.py         LangGraph state
│   │   ├── nodes.py         router, rag, web_search, refuse, rewrite_followup
│   │   └── graph.py         graph wiring
│   ├── guardrails.py        input checks (length, injection patterns, PII)
│   ├── tracing.py           Langfuse setup (no-op if keys missing)
│   ├── api.py               FastAPI app
│   └── eval/
│       ├── retrieval_eval.py   Recall@k, MRR, ablations
│       └── answer_eval.py      calls EvalForge /evaluate
├── ui/app.py                Streamlit app
├── data/
│   ├── raw/                 SEBI PDFs (human-provided, gitignored)
│   ├── processed/           chunks.jsonl
│   └── eval/                questions_dev.jsonl, questions_test.jsonl
├── storage/                 chroma/ and bm25.pkl (gitignored, rebuilt by script)
├── reports/                 all metric JSONs and figures
├── scripts/                 build_index.py, run_eval.py
├── tests/
├── private/                 PROJECT_EXPLAINED.md (gitignored)
├── .github/workflows/ci.yml
├── Dockerfile
├── pyproject.toml
├── HUMAN_GUIDE.md
├── ROADMAP.md
└── README.md
```

---

## Phase 0 — Setup and Data Acquisition

**Goal:** Repo skeleton, keys configured, SEBI PDFs in place.

### 0.1 — Repo skeleton
- Create the directory tree above with empty modules and one-line docstrings.
- `pyproject.toml` dependencies: `langchain`, `langchain-core`, `langchain-community`, `langchain-google-genai`, `langgraph`, `chromadb`, `sentence-transformers`, `rank-bm25`, `pymupdf`, `ddgs`, `fastapi`, `uvicorn`, `sse-starlette`, `langfuse`, `streamlit`, `python-dotenv`, `httpx`. Dev: `pytest`, `ruff`.
- Install CPU-only torch first (`--index-url https://download.pytorch.org/whl/cpu`) to keep the image small.
- `.gitignore`: `.env`, `data/raw/`, `storage/`, `private/`, `__pycache__/`, `.venv/`, `.cache/`.
- `config.py`: every path, model name, and numeric setting as constants.
- Create `HUMAN_GUIDE.md` with sections: *Status*, *Human actions needed*, *Decisions*, *Escalations*, *Live URLs*.
- Copy the provided `PROJECT_EXPLAINED.md` into `private/`.
- **Verify:** `pip install -e ".[dev]"` succeeds; `python -c "import sebisage"` works; `pytest` runs (0 tests is fine).

### 0.2 — 🧑 HUMAN CHECKPOINT H1: API keys
Write to HUMAN_GUIDE.md and stop:
> Create `.env` in the repo root with:
> ```
> GEMINI_API_KEY=...        # aistudio.google.com → Get API key (same key as EvalForge is fine)
> LANGFUSE_PUBLIC_KEY=...   # cloud.langfuse.com → new project → Settings → API keys
> LANGFUSE_SECRET_KEY=...
> LANGFUSE_HOST=https://cloud.langfuse.com
> EVALFORGE_URL=https://evalforge-cfyw.onrender.com
> EVALFORGE_API_KEY=...     # from EvalForge Render dashboard
> ```
> Tell Claude Code "keys added" when done.

After the human confirms: list the Gemini models available to this key, pick a fast free-tier text model for generation, record it in `config.py` and in HUMAN_GUIDE.md *Decisions*.

### 0.3 — 🧑 HUMAN CHECKPOINT H2: SEBI PDFs
Write to HUMAN_GUIDE.md and stop:
> Download these from **sebi.gov.in → Legal → Regulations** (latest amended/consolidated versions) and save into `data/raw/` with these exact names:
> | File name | Regulation |
> |---|---|
> | `lodr_2015.pdf` | SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015 |
> | `pit_2015.pdf` | SEBI (Prohibition of Insider Trading) Regulations, 2015 |
> | `sast_2011.pdf` | SEBI (Substantial Acquisition of Shares and Takeovers) Regulations, 2011 |
> | `ia_2013.pdf` | SEBI (Investment Advisers) Regulations, 2013 |
> | `ra_2014.pdf` | SEBI (Research Analysts) Regulations, 2014 |
>
> Record the "last amended" date shown on each PDF in the table in this file. Tell Claude Code "PDFs added".

After the human confirms: verify all 5 files open with pymupdf and log page counts to HUMAN_GUIDE.md.

### Phase 0 Exit Gate
- [ ] Skeleton matches Section 4.
- [ ] `.env` present, keys load (print only "present/missing", never values).
- [ ] 5 PDFs present and readable.
- [ ] Model choice recorded.
- [ ] HUMAN_GUIDE.md updated.
- [ ] 🧑 H6: Suggested commit: `phase-0: repo skeleton, config and data setup`

---

## Phase 1 — Parsing and Structure-Aware Chunking

**Goal:** Turn PDFs into clean chunks that each know which Regulation they belong to. This is the single most important quality decision in the project.

### 1.1 — PDF parsing
- `parse_pdf.py`: `parse(path) -> list[Page]` with `page_number`, `text`, `source_file`.
- Strip repeated headers/footers (lines that appear on > 50% of pages), page numbers, and footnote markers.
- Tests: page count matches pymupdf; a known header string is removed; no empty pages returned.

### 1.2 — Chunk schema
- `schema.py`: `Chunk(id, text, regulation, reg_no, sub_reg, chapter, page_start, page_end, source_file, chunker)`.
- `id` is deterministic: `{source_file}:{reg_no}:{sub_reg}:{n}` — same input gives same ids every run.

### 1.3 — Structure-aware chunker
- Detect regulation boundaries with regex on lines such as `30. (1)`, `Regulation 30`, `CHAPTER IV`, `SCHEDULE`. Document the patterns in a comment and in HUMAN_GUIDE.md.
- One chunk = one sub-regulation. If a sub-regulation exceeds `MAX_CHUNK_TOKENS` (config, e.g. 400), split on clause markers `(a)`, `(b)`, keeping the regulation header prefixed to every piece.
- Very short sub-regulations (< 40 tokens) merge with the next one under the same regulation.
- Schedules and definitions (Reg 2) get their own chunks.
- Tests: synthetic 3-regulation text yields correct `reg_no` values; long clause splits keep header; ids are stable across two runs.

### 1.4 — Baseline fixed-size chunker
- `fixed_chunks(pages, size=500, overlap=50)` — needed later for the ablation study. Same schema, `reg_no = None`, `chunker = "fixed"`.

### 1.5 — Run and inspect
- `scripts/build_chunks.py` writes `data/processed/chunks_structured.jsonl` and `chunks_fixed.jsonl`.
- Write `reports/chunk_stats.json`: count per file, mean/median/max tokens, % of chunks with a detected `reg_no`.
- **Quality bar:** ≥ 85% of structured chunks have a `reg_no`. If lower, inspect failures and improve regex (max 2 attempts, then escalate).

### Phase 1 Exit Gate
- [ ] Both chunk files written.
- [ ] `reg_no` coverage ≥ 85% (real number in HUMAN_GUIDE.md).
- [ ] 5 random structured chunks printed into HUMAN_GUIDE.md for human eyeballing.
- [ ] All tests pass, ruff clean.
- [ ] Update `PROJECT_EXPLAINED.md` → *Problems faced* (any parsing issues found).
- [ ] 🧑 H6: Suggested commit: `phase-1: PDF parsing and structure-aware chunking`

---

## Phase 2 — Indexing (Dense + Sparse)

**Goal:** Two searchable indexes over the same chunks.

### 2.1 — Dense index
- `dense.py`: embed with bge-small (use the model's recommended query instruction prefix for queries, not documents). Store in persistent Chroma at `storage/chroma/`, one collection per chunker (`structured`, `fixed`).
- Metadata stored: every Chunk field except `text`.
- Tests (tiny 5-chunk fixture): build then query returns the obviously matching chunk first.

### 2.2 — Sparse index
- `sparse.py`: BM25 over lowercased, tokenised text; keep tokens like `30(6)` and `KMP` intact (custom tokenizer, tested).
- Persist to `storage/bm25_{chunker}.pkl` with the chunk id list.
- Tests: exact-term query "Regulation 30" ranks the Reg 30 fixture first.

### 2.3 — Build script
- `scripts/build_index.py --chunker structured|fixed|all` — idempotent, rebuilds from `data/processed/`.
- Log build time and index sizes to `reports/index_stats.json`.

### Phase 2 Exit Gate
- [ ] Both indexes built for both chunkers.
- [ ] Rebuild is idempotent (same counts twice).
- [ ] Tests pass, ruff clean.
- [ ] 🧑 H6: Suggested commit: `phase-2: dense and BM25 indexes`

---

## Phase 3 — Retrieval, Evaluation Set and Ablation

**Goal:** Measured, defensible retrieval. This phase produces the headline resume numbers.

### 3.1 — Evaluation question set (draft) → 🧑 HUMAN CHECKPOINT H3
- Claude Code drafts **60 questions** into `data/eval/questions_draft.jsonl`:
  - 45 answerable: each with `question`, `gold_reg` (e.g. `"lodr_2015:30"`), `gold_sub_reg` if applicable, `difficulty` (easy/medium/hard), `type` (definition / obligation / deadline / threshold / penalty).
  - 10 paraphrased questions that avoid the regulation's own wording (tests dense retrieval).
  - 5 unanswerable / out-of-scope (e.g. "What is the GST rate on mutual fund fees?") with `gold_reg: null`.
- Questions must be written from reading the chunk text, and each draft must include the supporting chunk id so the human can check quickly.
- Build `data/eval/review.html`: one card per question showing question, gold regulation, and the supporting chunk text, with **Keep / Fix / Drop** buttons and an edit box; exports `questions_verified.jsonl`.
- Write to HUMAN_GUIDE.md and stop:
  > Open `data/eval/review.html` in your browser. For each question, check the gold regulation really answers it. Keep, fix, or drop. Export when done and tell Claude Code "questions verified".
- After export: split deterministically (seed in config) into `questions_dev.jsonl` (≈ 60%) and `questions_test.jsonl` (≈ 40%). **All tuning uses dev only. Test is touched once, at the end of 3.5.** (Lesson from EvalForge: tuning on the only labelled set overfits.)

### 3.2 — Hybrid retrieval
- `hybrid.py`: `retrieve(query, k)`:
  1. dense top `K_DENSE` (config, e.g. 20)
  2. BM25 top `K_SPARSE` (e.g. 20)
  3. **Reciprocal Rank Fusion**: `score = Σ 1/(RRF_K + rank)` with `RRF_K = 60`
  4. return top `K_FUSED` chunk ids with scores and which retriever(s) found each.
- Tests: RRF math on hand-made rankings; a doc found by both retrievers outranks one found by only one at equal ranks.

### 3.3 — Reranker
- `rerank.py`: cross-encoder scores `(query, chunk_text)` pairs for the fused candidates, returns top `K_FINAL` (e.g. 5).
- Model loaded once, cached.
- Tests: obviously relevant pair outscores irrelevant pair.

### 3.4 — Retrieval metrics
- `retrieval_eval.py`: for each answerable question, a hit = any retrieved chunk whose `reg_no` matches `gold_reg`.
  - **Recall@1, Recall@3, Recall@5, MRR@10.**
  - Unanswerable questions: record the top reranker score (used later to set the refusal threshold).
- Breakdown by `type` and `difficulty`.

### 3.5 — Ablation study (the key result)
Run on **dev**, report all rows:

| Config | Chunker | Retrieval | Rerank |
|---|---|---|---|
| A | fixed | dense only | no |
| B | structured | dense only | no |
| C | structured | BM25 only | no |
| D | structured | hybrid (RRF) | no |
| E | structured | hybrid (RRF) | yes |

- Write `reports/retrieval_ablation_dev.json` and a bar chart `reports/figures/ablation.png`.
- Pick the best config **by dev MRR**. Then run that single config **once** on test → `reports/retrieval_test.json`.
- Record latency per query (p50, p95) for each config.
- If structured chunking does NOT beat fixed, report it honestly. Do not tweak the test set.

### Phase 3 Exit Gate
- [ ] Verified question set split into dev/test.
- [ ] Ablation table with real numbers in HUMAN_GUIDE.md.
- [ ] Test-set result recorded once.
- [ ] Update `PROJECT_EXPLAINED.md` → *Key results* and *Design decisions* (why hybrid, why rerank — with the measured deltas).
- [ ] Tests pass, ruff clean.
- [ ] 🧑 H6: Suggested commit: `phase-3: hybrid retrieval, reranking and ablation study`

---

## Phase 4 — Grounded Generation with Citations

**Goal:** Answers that only say what the retrieved text supports, and prove it with citations.

### 4.1 — LLM wrapper with disk cache
- `llm.py`: LangChain `ChatGoogleGenerativeAI` wrapper.
- **Disk cache** keyed by hash of (model, prompt version, messages). Reruns cost zero quota and make evals reproducible. Cache dir in config, gitignored.
- Track input/output tokens per call; expose `last_usage`.
- On quota errors (HTTP 429): wait the server-suggested delay up to `MAX_WAIT_S`, then give up gracefully (return an error object, never crash).
- Tests: mocked LLM — second identical call hits cache; 429 path returns error object.

### 4.2 — Answer prompt and chain
- `prompts.py`: `ANSWER_PROMPT_V1`. Rules inside the prompt:
  - Use ONLY the numbered context chunks.
  - Every factual sentence ends with a citation like `[2]`.
  - If context does not contain the answer, reply exactly `INSUFFICIENT_CONTEXT`.
  - Plain language, ≤ 150 words, then a one-line "Source:" list.
- `answer.py`: LCEL chain `retrieve → format context → prompt → llm → parse`. Output: `answer`, `citations` (list of chunk ids), `usage`, `latency_ms`.

### 4.3 — Grounding validator
- `grounding.py`:
  - Every `[n]` must reference a real context chunk → else flag `invalid_citation`.
  - Every sentence (except the Source line) must carry ≥ 1 citation → else flag `uncited_sentence`.
  - Regulation numbers mentioned in the answer text must appear in the cited chunks → else flag `hallucinated_reference`.
- If any flag fires: one automatic retry with a stricter reminder; if it fails again, return the answer with `grounded: false` and the flags.
- Tests on hand-written answers covering each flag.

### 4.4 — 🧑 HUMAN CHECKPOINT H4: answer spot-check
- Run the chain on 10 dev questions (mix of types) → `reports/answer_samples.md` showing question, answer, citations, and cited chunk text.
- Write to HUMAN_GUIDE.md and stop:
  > Read `reports/answer_samples.md`. For each answer mark ✅ correct, ⚠️ partially correct, ❌ wrong, directly in the file. Tell Claude Code "spot-check done".
- Record the tally in HUMAN_GUIDE.md. If ≥ 3 are ❌, escalate before continuing.

### Phase 4 Exit Gate
- [ ] Chain returns grounded answers with citations.
- [ ] Grounding validator tested for all 3 flags.
- [ ] Human spot-check tally recorded.
- [ ] Grounding pass rate on all dev questions in `reports/grounding_dev.json`.
- [ ] 🧑 H6: Suggested commit: `phase-4: grounded answer chain with citation validation`

---

## Phase 5 — LangGraph Agent

**Goal:** Move from a fixed chain to an agent that decides what to do.

### 5.1 — State and graph design
- `state.py`: `messages`, `question`, `standalone_question`, `route`, `retrieved`, `answer`, `citations`, `grounded`, `usage_total`, `trace_id`.
- Graph:
  ```
  START → rewrite_followup → router ─┬─ "regulation" → rag → grounding_check → END
                                     ├─ "recent"     → web_search → answer_from_web → END
                                     └─ "out_of_scope" → refuse → END
  ```
- Draw the graph with LangGraph's built-in Mermaid export → `reports/figures/agent_graph.md`.

### 5.2 — Follow-up rewriting (memory)
- `rewrite_followup`: if there is prior conversation, rewrite the latest message into a standalone question ("What about for insiders?" → "What are the disclosure obligations for insiders under PIT Regulations?").
- Keep last `MEMORY_TURNS` (config, e.g. 4) turns only.
- Tests with mocked LLM: no history → unchanged; with history → rewritten.

### 5.3 — Router
- Two-stage, cheap first:
  1. **Rules:** keywords like "latest", "recent circular", "2026", "new rule" → `recent`.
  2. **Retrieval confidence:** if top reranker score < `REFUSE_THRESHOLD` (set from Phase 3 unanswerable scores on dev) → LLM classifier decides between `regulation` and `out_of_scope`.
  3. Otherwise → `regulation`.
- Router decision and reason stored in state for tracing.
- Evaluate router on dev set (answerable should route `regulation`, unanswerable `out_of_scope`) → `reports/router_dev.json` with accuracy and confusion matrix.

### 5.4 — Tool nodes
- `rag`: the Phase 4 chain.
- `web_search`: DuckDuckGo query restricted to `site:sebi.gov.in`, top 5 results (title, url, snippet). Answer only from snippets, cite URLs, add a line: "Based on search snippets; verify on sebi.gov.in." Handle rate-limit/no-result gracefully.
- `refuse`: polite message stating scope (the 5 regulations covered) and suggesting a rephrase.

### Phase 5 Exit Gate
- [ ] Graph runs end-to-end for all 3 routes (mocked tests + 3 real smoke calls).
- [ ] Router accuracy on dev recorded.
- [ ] Mermaid graph committed.
- [ ] Update `PROJECT_EXPLAINED.md` → *Why an agent instead of a chain*.
- [ ] 🧑 H6: Suggested commit: `phase-5: LangGraph agent with routing and follow-up memory`

---

## Phase 6 — API, Streaming, Guardrails, Cost Tracking

### 6.1 — Guardrails
- `guardrails.py` (input side):
  - Max length (config).
  - Prompt-injection patterns ("ignore previous instructions", "system prompt", etc.) → reject with 400 and a reason.
  - PII: PAN (`[A-Z]{5}[0-9]{4}[A-Z]`), Aadhaar (12 digits), phone numbers → masked before sending to the LLM.
- Tests for each rule.

### 6.2 — FastAPI endpoints
- `GET /health` → status, index sizes, model names, index build date.
- `POST /ask` → `{question, session_id?}` → full JSON answer (answer, citations with regulation + page, route, grounded, usage, latency_ms, trace_id).
- `POST /ask/stream` → Server-Sent Events: `route` event, token events, final `citations` event.
- `GET /sources/{chunk_id}` → chunk text and metadata (the UI uses this).
- In-memory session store for conversation history (TTL in config).
- `X-API-Key` header required on `/ask*` (same pattern as EvalForge); `/health` open.
- Simple per-IP rate limit (config, e.g. 10/min).

### 6.3 — Cost and token tracking
- Every response includes tokens in/out and an estimated cost using per-token prices from `config.py` (clearly labelled as estimate).
- `GET /stats` → totals since start: queries, route counts, cache hit rate, mean latency, total tokens.

### Phase 6 Exit Gate
- [ ] All endpoints tested with FastAPI TestClient (LLM mocked).
- [ ] Streaming verified with a real local call.
- [ ] 🧑 H6: Suggested commit: `phase-6: FastAPI with streaming, guardrails and cost tracking`

---

## Phase 7 — Observability and End-to-End Evaluation

### 7.1 — Langfuse tracing
- `tracing.py`: LangChain callback handler for Langfuse; every agent node becomes a span with inputs, outputs, tokens, latency.
- No keys → tracing silently disabled (tests must pass without keys).
- `trace_id` returned in API responses.
- Take 2 screenshots of a real trace (one `regulation`, one `out_of_scope`) → ask human to save them to `docs/` (🧑 small action, note in HUMAN_GUIDE.md).

### 7.2 — Answer evaluation via EvalForge
- `answer_eval.py`: for each **test** question, send `(input = question + retrieved context, output = answer)` to EvalForge `/evaluate/batch` in chunks of ≤ 50.
- Report EvalForge rule-based and embedding scores; report its judge scores only as a secondary, clearly caveated signal (EvalForge's own judge kappa was low — say so).
- If EvalForge is asleep or quota-limited, retry after its cold start; if still failing, record `skipped` rather than crashing.

### 7.3 — End-to-end report
- `scripts/run_eval.py` → `reports/e2e_test.json` and `reports/EVAL_REPORT.md` with:
  - Retrieval (from Phase 3 test)
  - Router accuracy
  - Grounding pass rate
  - Refusal precision/recall on unanswerable questions
  - EvalForge scores
  - Latency p50/p95, mean tokens and estimated cost per query, cache hit rate

### Phase 7 Exit Gate
- [ ] Langfuse traces visible (human confirms).
- [ ] `EVAL_REPORT.md` generated from real runs only.
- [ ] Update `PROJECT_EXPLAINED.md` → *Key results* with final numbers.
- [ ] 🧑 H6: Suggested commit: `phase-7: Langfuse tracing and end-to-end evaluation`

---

## Phase 8 — Streamlit UI

### 8.1 — Layout
- Left: chat (question box, streamed answer, conversation history).
- Right: **Citations panel** — each citation shows regulation name, reg number, page, and an expandable box with the exact source text (from `/sources/{id}`).
- Top: disclaimer banner (educational, not legal advice) and "Covers: LODR, PIT, SAST, IA, RA" chip list.
- Badges per answer: route taken, grounded ✅/⚠️, latency, tokens.
- Sidebar: 6 example questions (clickable), "Clear conversation" button.

### 8.2 — Wiring
- UI calls the FastAPI service (URL from env); if running in one container, API on 8000 and UI on 7860.
- Handles API errors with friendly messages (cold start, rate limit, refusal).

### Phase 8 Exit Gate
- [ ] Runs locally with `streamlit run ui/app.py`.
- [ ] Screenshot saved to `docs/ui.png` (🧑 human takes it).
- [ ] 🧑 H6: Suggested commit: `phase-8: Streamlit UI with citations panel`

---

## Phase 9 — Docker, CI, Deployment

### 9.1 — Dockerfile
- `python:3.11-slim`, CPU torch, non-root user.
- Bake in at build time: bge-small, cross-encoder, Chroma + BM25 indexes (built from `data/processed/`, which IS committed — chunks are derived public text).
- Start script runs uvicorn (8000) and Streamlit (7860) together.
- **Verify:** `docker build` and `docker run -p 7860:7860` work locally; `/health` 200.

### 9.2 — GitHub Actions CI
- Jobs:
  1. **lint** — ruff
  2. **test** — pytest (all LLM calls mocked, no keys)
  3. **retrieval-gate** — rebuild indexes from `data/processed/`, run retrieval eval on **dev**, fail if MRR drops more than `GATE_TOLERANCE` below the recorded baseline in `reports/retrieval_baseline.json`. No API key needed (retrieval is local) — so this gate never fails because of LLM quota. (Lesson from EvalForge.)
- Cache pip and HF model downloads.

### 9.3 — 🧑 HUMAN CHECKPOINT H5: Hugging Face Space
Write to HUMAN_GUIDE.md and stop:
> 1. huggingface.co → New Space → name `sebisage`, SDK **Docker**, hardware **CPU basic (free)**, public.
> 2. Space → Settings → Variables and secrets → add `GEMINI_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `SEBISAGE_API_KEY` (any long random string).
> 3. Push the repo to the Space (Space page → "Clone repository" shows the git remote to add).
> 4. Paste the live Space URL into HUMAN_GUIDE.md *Live URLs*.

After the human confirms: hit `/health` and one real question; record results.

### Phase 9 Exit Gate
- [ ] Docker runs locally.
- [ ] All 3 CI jobs green on GitHub (human confirms).
- [ ] Live URL works end-to-end.
- [ ] 🧑 H6: Suggested commit: `phase-9: Docker, CI retrieval gate and Hugging Face deployment`

---

## Phase 10 — README, Resume Bullets, Interview File

### 10.1 — README.md
1. One-paragraph pitch + disclaimer.
2. Demo GIF placeholder (`docs/demo.gif` — 🧑 human records it) and live link.
3. Architecture diagram (Mermaid).
4. **Results** — ablation table and final test metrics, copied from `reports/`.
5. Design decisions (structure-aware chunking, hybrid + RRF, reranker, grounding validator, router, local embeddings, disk cache).
6. Quickstart (build index, run API, run UI, run eval).
7. API reference table.
8. Honest limitations (see 10.3).
9. Roadmap / future work.

### 10.2 — Resume bullets (LaTeX, same style as Contrail / CI Brain)
Fill with real numbers only. Template:
```latex
\resumeSubheading
{SebiSage - Agentic RAG over SEBI Regulations}{2026}
{Python, LangChain, LangGraph, ChromaDB, FastAPI, Streamlit, Langfuse, Docker, GitHub Actions}{\href{https://github.com/Som0111/sebisage}{\faGithub\ GitHub}}

\resumeItemListStart
\resumeItem{Built a \textbf{hybrid retrieval pipeline} (dense + BM25 fused via RRF, cross-encoder reranking) over \textbf{[N] regulation chunks}, lifting \textbf{Recall@5 from [A]\% to [B]\%} versus dense-only fixed-size chunking.}
\resumeItem{Designed a \textbf{LangGraph agent} routing queries between regulation lookup, live SEBI-site search, and refusal, reaching \textbf{[X]\% routing accuracy} and \textbf{[Y]\% refusal recall} on out-of-scope questions.}
\resumeItem{Engineered a \textbf{citation-grounding validator} rejecting uncited or hallucinated clause references, with \textbf{[Z]\%} of answers fully grounded on a held-out test set.}
\resumeItem{Deployed a \textbf{streaming FastAPI + Streamlit} app with guardrails, per-query cost tracking, \textbf{Langfuse tracing}, and a CI retrieval-regression gate.}
\resumeItemListEnd
```
Paste into HUMAN_GUIDE.md.

### 10.3 — Finalise `private/PROJECT_EXPLAINED.md`
Fill every section still marked `[FILL]` using real results and the problems actually hit during the build (read HUMAN_GUIDE.md escalations and decisions).

### Phase 10 Exit Gate
- [ ] README numbers match `reports/` exactly.
- [ ] Resume bullets contain no placeholders.
- [ ] `PROJECT_EXPLAINED.md` has no `[FILL]` left.
- [ ] All tests pass, ruff clean.
- [ ] 🧑 H6: Suggested commit: `phase-10: README, resume bullets and project explanation`

---

## Appendix A — Honest Limitations to Record (update with reality)
- Only 5 regulations; circulars and master circulars not indexed (web search covers them weakly).
- Regulations are amended often; index reflects the PDF dates recorded in Phase 0.3.
- Evaluation questions labelled by one person.
- Web search answers rely on snippets, not full documents.
- Free-tier LLM quota limits evaluation size.
- Not legal advice.

## Appendix B — Future Improvements (for interviews)
- Index SEBI master circulars with version dates; answer "as of date X".
- Parent-child retrieval (retrieve sub-regulation, pass whole regulation).
- Query decomposition for multi-regulation questions.
- Fine-tune bge-small on regulation Q&A pairs (LoRA) and measure the retrieval gain.
- Move to AWS (ECS/Fargate) or GCP Cloud Run.
- Second annotator + inter-annotator agreement on the eval set.

*End of ROADMAP.md*
