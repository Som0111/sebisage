"""Builds data/eval/review.html from questions_draft.jsonl + chunk text, for
the Phase 3.1 human review checkpoint (Keep / Fix / Drop -> questions_verified.jsonl).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sebisage.config import EVAL_DIR, PROCESSED_DIR

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SebiSage — Eval Question Review</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, -apple-system, sans-serif; max-width: 900px; margin: 0 auto;
         padding: 16px; background: #f7f7f8; color: #111; }
  header { position: sticky; top: 0; background: #f7f7f8; padding: 12px 0; border-bottom: 1px solid #ddd;
           display: flex; justify-content: space-between; align-items: center; z-index: 10; }
  h1 { font-size: 18px; margin: 0; }
  #progress { font-size: 14px; color: #444; }
  button.export { background: #1a7f37; color: white; border: none; padding: 8px 16px; border-radius: 6px;
                  cursor: pointer; font-size: 14px; }
  button.export:hover { background: #146c2e; }
  .card { background: white; border: 1px solid #ddd; border-radius: 8px; padding: 14px; margin: 14px 0; }
  .card.status-keep { border-left: 5px solid #1a7f37; }
  .card.status-fix { border-left: 5px solid #b08800; }
  .card.status-drop { border-left: 5px solid #b31d28; opacity: 0.55; }
  .badges { font-size: 11px; color: #555; margin-bottom: 6px; }
  .badges span { background: #eee; border-radius: 4px; padding: 2px 6px; margin-right: 4px; }
  .question { font-size: 15px; font-weight: 600; margin: 6px 0; }
  .meta { font-size: 12px; color: #555; margin-bottom: 8px; }
  .chunk { background: #f0f0f2; border-radius: 6px; padding: 8px 10px; font-size: 13px;
           white-space: pre-wrap; max-height: 160px; overflow-y: auto; margin-bottom: 8px; }
  .edit-box { display: none; margin: 8px 0; }
  .edit-box.open { display: block; }
  .edit-box textarea, .edit-box input { width: 100%; box-sizing: border-box; font-family: inherit;
                                          font-size: 13px; padding: 6px; margin-bottom: 6px; }
  .actions button { margin-right: 6px; padding: 4px 12px; border-radius: 5px; border: 1px solid #ccc;
                     background: white; cursor: pointer; font-size: 13px; }
  .actions button.active-keep { background: #1a7f37; color: white; border-color: #1a7f37; }
  .actions button.active-fix { background: #b08800; color: white; border-color: #b08800; }
  .actions button.active-drop { background: #b31d28; color: white; border-color: #b31d28; }
  @media (prefers-color-scheme: dark) {
    body { background: #15161a; color: #eee; }
    header { background: #15161a; border-color: #333; }
    .card { background: #1e1f24; border-color: #333; }
    .chunk { background: #26272d; }
    .actions button { background: #2a2b31; color: #eee; border-color: #444; }
    .badges span { background: #2a2b31; }
  }
</style>
</head>
<body>
<header>
  <h1>SebiSage — Eval Question Review</h1>
  <div>
    <span id="progress"></span>
    <button class="export" onclick="exportVerified()">Export questions_verified.jsonl</button>
  </div>
</header>
<div id="cards"></div>

<script>
const DATA = __DATA_JSON__;
const STORAGE_KEY = "sebisage_review_v1";

function loadState() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch (e) { return {}; }
}
function saveState(state) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) {}
}

let state = loadState();

function getRow(id) {
  return state[id] || { status: null, question: null, gold_reg: null, gold_sub_reg: null };
}

function setStatus(id, status) {
  const row = getRow(id);
  row.status = row.status === status ? null : status;
  state[id] = row;
  saveState(state);
  render();
}

function saveEdit(id) {
  const row = getRow(id);
  row.question = document.getElementById("edit-q-" + id).value;
  row.gold_reg = document.getElementById("edit-reg-" + id).value || null;
  row.gold_sub_reg = document.getElementById("edit-sub-" + id).value || null;
  state[id] = row;
  saveState(state);
}

function updateProgress() {
  const reviewed = DATA.filter(d => getRow(d.id).status).length;
  document.getElementById("progress").textContent = reviewed + " / " + DATA.length + " reviewed";
}

function render() {
  const container = document.getElementById("cards");
  container.innerHTML = "";
  for (const d of DATA) {
    const row = getRow(d.id);
    const card = document.createElement("div");
    card.className = "card" + (row.status ? " status-" + row.status : "");

    const badges = document.createElement("div");
    badges.className = "badges";
    badges.innerHTML = `<span>${d.id}</span><span>${d.type}</span><span>${d.difficulty}</span>` +
      (d.paraphrased ? `<span>paraphrased</span>` : "") +
      (d.gold_reg === null ? `<span>out-of-scope</span>` : "");
    card.appendChild(badges);

    const q = document.createElement("div");
    q.className = "question";
    q.textContent = row.question || d.question;
    card.appendChild(q);

    const meta = document.createElement("div");
    meta.className = "meta";
    const gr = row.gold_reg !== null ? row.gold_reg : d.gold_reg;
    const gs = row.gold_sub_reg !== null ? row.gold_sub_reg : d.gold_sub_reg;
    meta.textContent = "gold_reg: " + (gr || "null") + "   gold_sub_reg: " + (gs || "null") +
      "   chunk_id: " + (d.chunk_id || "null");
    card.appendChild(meta);

    if (d.chunk_text) {
      const chunk = document.createElement("div");
      chunk.className = "chunk";
      chunk.textContent = d.chunk_text;
      card.appendChild(chunk);
    }

    const editBox = document.createElement("div");
    editBox.className = "edit-box" + (row.status === "fix" ? " open" : "");
    editBox.innerHTML = `
      <textarea id="edit-q-${d.id}" rows="2" placeholder="Edited question">${row.question || d.question}</textarea>
      <input id="edit-reg-${d.id}" placeholder="gold_reg (e.g. lodr_2015:30)" value="${gr || ""}">
      <input id="edit-sub-${d.id}" placeholder="gold_sub_reg (e.g. 1-2)" value="${gs || ""}">
    `;
    card.appendChild(editBox);

    const actions = document.createElement("div");
    actions.className = "actions";
    const keepBtn = document.createElement("button");
    keepBtn.textContent = "Keep";
    keepBtn.className = row.status === "keep" ? "active-keep" : "";
    keepBtn.onclick = () => setStatus(d.id, "keep");
    const fixBtn = document.createElement("button");
    fixBtn.textContent = "Fix";
    fixBtn.className = row.status === "fix" ? "active-fix" : "";
    fixBtn.onclick = () => { saveEdit(d.id); setStatus(d.id, "fix"); };
    const dropBtn = document.createElement("button");
    dropBtn.textContent = "Drop";
    dropBtn.className = row.status === "drop" ? "active-drop" : "";
    dropBtn.onclick = () => setStatus(d.id, "drop");
    actions.append(keepBtn, fixBtn, dropBtn);
    card.appendChild(actions);

    editBox.querySelectorAll("textarea, input").forEach(el => {
      el.addEventListener("change", () => saveEdit(d.id));
    });

    container.appendChild(card);
  }
  updateProgress();
}

function exportVerified() {
  const lines = [];
  for (const d of DATA) {
    const row = getRow(d.id);
    if (row.status === "drop") continue;
    lines.push(JSON.stringify({
      id: d.id,
      question: row.question || d.question,
      gold_reg: row.gold_reg !== null ? (row.gold_reg || null) : d.gold_reg,
      gold_sub_reg: row.gold_sub_reg !== null ? (row.gold_sub_reg || null) : d.gold_sub_reg,
      difficulty: d.difficulty,
      type: d.type,
      paraphrased: d.paraphrased,
      chunk_id: d.chunk_id
    }));
  }
  const blob = new Blob([lines.join("\\n") + "\\n"], { type: "application/x-ndjson" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "questions_verified.jsonl";
  a.click();
}

render();
</script>
</body>
</html>
"""


def main() -> None:
    chunks_by_id = {}
    with (PROCESSED_DIR / "chunks_structured.jsonl").open(encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            chunks_by_id[c["id"]] = c["text"]

    rows = []
    with (EVAL_DIR / "questions_draft.jsonl").open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            d["chunk_text"] = chunks_by_id.get(d["chunk_id"]) if d["chunk_id"] else None
            rows.append(d)

    html = TEMPLATE.replace("__DATA_JSON__", json.dumps(rows, ensure_ascii=False))
    out_path = EVAL_DIR / "review.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} with {len(rows)} questions")


if __name__ == "__main__":
    main()
