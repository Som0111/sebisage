# SebiSage Demo Script

## Duration

60-90 seconds.

## Pre-recording checklist

- [ ] API started locally: `uvicorn sebisage.api:app --app-dir src --port 8000`
- [ ] UI started locally: `streamlit run ui/app.py --server.port 7860`
- [ ] Browser open at http://localhost:7860
- [ ] Terminal hidden (no API keys visible on screen)
- [ ] `GEMINI_API_KEY` set in `.env` (generation needs a real key — see
  [Honest limitations](../README.md#honest-limitations); there is no demo/mocked
  generation mode, so a real key is required for a live recording)

## Recording sequence

### 1 - Introduction (5s)

Show the UI home screen: the disclaimer banner and the regulation coverage chips
(`LODR 2015 | PIT 2015 | SAST 2011 | IA 2013 | RA 2014`) should both be visible
without scrolling.

### 2 - Regulation question (20s)

Type (or click the matching example question in the sidebar): *"When must a listed
company disclose a material event?"* — a Regulation 30 / LODR 2015 disclosure-timeline
question.

Wait for the streamed answer to complete. Point out the citations panel on the right
- regulation name, clause number, page.

### 3 - Open a citation (10s)

Click a citation in the panel to expand the source text. Show that the answer text
matches the cited clause.

### 4 - Follow-up question (15s)

Ask a follow-up that refers back to the first answer, e.g. *"What is the penalty for
not disclosing it?"* Point out that the agent understood "it" from the prior turn
(the follow-up rewrite happens silently - there's nothing to click to prove it beyond
the answer itself staying on-topic).

### 5 - Route and grounding badge (5s)

Point to the metadata row under the answer: `route: regulation`, the grounded ✅
badge, and the retrieval/e2e latency figures next to it.

### 6 - Out-of-scope question (10s)

Ask an out-of-scope question, e.g. *"What is the current repo rate set by the Reserve
Bank of India?"* (this is one of the sidebar example questions). Show the polite
refusal and the scope statement (the five covered regulations).

## What NOT to show

- Terminal output with API keys.
- Internal file paths (e.g. `.cache/`, `storage/chroma/`).
- Any answer implying this is legal advice or a production/SLA-backed service.
- A "live demo" URL - this project is not currently deployed to a public URL (see
  [README status](../README.md#status)). Record locally only.
