"""Streamlit app: chat, citations panel, example questions."""

import json
import os
import sys
import uuid
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
load_dotenv()

from sebisage.config import API_PORT, COVERED_REGULATIONS, EXAMPLE_QUESTIONS

API_BASE_URL = os.environ.get("SEBISAGE_API_URL", f"http://localhost:{API_PORT}")
API_KEY = os.environ.get("SEBISAGE_API_KEY", "")

st.set_page_config(page_title="SebiSage", layout="wide")


def _headers() -> dict:
    return {"X-API-Key": API_KEY, "Content-Type": "application/json"}


def stream_answer(question: str, session_id: str):
    """Generator of answer-text chunks from /ask/stream's SSE `token` events;
    stashes the `route`/`citations` side-channel events into session_state as
    they arrive (Streamlit's write_stream only wants the text stream itself)."""
    with httpx.stream(
        "POST",
        f"{API_BASE_URL}/ask/stream",
        json={"question": question, "session_id": session_id},
        headers=_headers(),
        timeout=120,
    ) as response:
        response.raise_for_status()
        current_event = None
        for line in response.iter_lines():
            if not line:
                continue
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                # Only drop the single space that's part of the SSE "data: " delimiter -
                # a full .strip() would also eat the trailing space each token event
                # intentionally carries (api.py sends "word "), mashing words together.
                data = line.split(":", 1)[1].removeprefix(" ")
                if current_event == "route":
                    st.session_state["_last_meta"] = json.loads(data)
                elif current_event == "token":
                    yield data
                elif current_event == "citations":
                    st.session_state["_last_meta"].update(json.loads(data))


def fetch_source(chunk_id: str) -> dict | None:
    try:
        resp = httpx.get(f"{API_BASE_URL}/sources/{chunk_id}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except httpx.HTTPError:
        pass
    return None


def render_citations_panel(citations: list[dict]):
    st.subheader("Citations")
    if not citations:
        st.caption("No citations for this answer.")
        return
    for c in citations:
        source = c.get("source", "")
        label = f"{c.get('regulation') or source} · Reg {c.get('reg_no')}" if c.get("regulation") else source
        if c.get("page"):
            label += f" · p.{c['page']}"
        with st.expander(label):
            chunk = fetch_source(source) if c.get("regulation") else None
            if chunk:
                st.text(chunk["text"])
            elif source.startswith("http"):
                st.markdown(f"[{source}]({source})")
            else:
                st.caption("Source text unavailable.")


def render_badges(meta: dict):
    route = meta.get("route", "unknown")
    grounded = meta.get("grounded")
    badge = "✅ grounded" if grounded else ("⚠️ ungrounded" if grounded is not None else "")
    st.caption(f"**route:** `{route}` &nbsp;&nbsp; {badge}")


def main():
    st.markdown(
        "> **Educational project — not legal or investment advice.** "
        "SebiSage answers questions about Indian SEBI securities regulations with clause-level citations."
    )
    st.markdown(" ".join(f"`{r}`" for r in COVERED_REGULATIONS))

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "_last_meta" not in st.session_state:
        st.session_state["_last_meta"] = {}

    with st.sidebar:
        st.header("Example questions")
        example_clicked = None
        for q in EXAMPLE_QUESTIONS:
            if st.button(q, use_container_width=True):
                example_clicked = q
        st.divider()
        if st.button("Clear conversation"):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()

    left, right = st.columns([2, 1])

    with left:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg["role"] == "assistant" and msg.get("meta"):
                    render_badges(msg["meta"])

        question = st.chat_input("Ask about LODR, PIT, SAST, IA or RA regulations...") or example_clicked

        if question:
            st.session_state.messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.write(question)

            with st.chat_message("assistant"):
                try:
                    st.session_state["_last_meta"] = {}
                    answer_text = st.write_stream(stream_answer(question, st.session_state.session_id))
                    meta = st.session_state.get("_last_meta", {})
                    render_badges(meta)
                    st.session_state.messages.append({"role": "assistant", "content": answer_text, "meta": meta})
                except httpx.TimeoutException:
                    msg = "The SebiSage API is taking a while to respond (it may be cold-starting). Please try again in a moment."
                    st.error(msg)
                    st.session_state.messages.append({"role": "assistant", "content": msg, "meta": {}})
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        msg = "Rate limit reached — please wait a minute before asking again."
                    elif e.response.status_code == 401:
                        msg = "The API rejected the request (missing or invalid API key). Check SEBISAGE_API_KEY."
                    elif e.response.status_code == 400:
                        msg = f"That question couldn't be processed: {e.response.text}"
                    else:
                        msg = f"The SebiSage API returned an error ({e.response.status_code})."
                    st.error(msg)
                    st.session_state.messages.append({"role": "assistant", "content": msg, "meta": {}})
                except httpx.ConnectError:
                    msg = f"Can't reach the SebiSage API at {API_BASE_URL} — is it running?"
                    st.error(msg)
                    st.session_state.messages.append({"role": "assistant", "content": msg, "meta": {}})

    with right:
        last_assistant = next((m for m in reversed(st.session_state.messages) if m["role"] == "assistant"), None)
        render_citations_panel((last_assistant or {}).get("meta", {}).get("citations", []))


if __name__ == "__main__":
    main()
