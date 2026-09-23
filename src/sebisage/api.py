"""FastAPI app: /health, /ask, /ask/stream, /sources/{chunk_id}, /stats."""

import json
import os
import time
import uuid
from collections import Counter, defaultdict
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()  # GEMINI_API_KEY, SEBISAGE_API_KEY, LANGFUSE_* etc. - must run before any reads of them below

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from sebisage.agent.graph import compiled_graph
from sebisage.config import (
    API_KEY_HEADER,
    CHROMA_DIR,
    COST_PER_1K_INPUT,
    COST_PER_1K_OUTPUT,
    EMBEDDING_MODEL,
    GEMINI_MODEL,
    PROCESSED_DIR,
    RATE_LIMIT_PER_MIN,
    REPORTS_DIR,
    RERANKER_MODEL,
    SESSION_TTL_S,
)
from sebisage.generate.llm import get_cache_stats
from sebisage.guardrails import check_input

app = FastAPI(title="SebiSage API")

_sessions: dict[str, dict] = {}
_rate_limit_hits: dict[str, list[float]] = defaultdict(list)
_stats = {"queries": 0, "route_counts": Counter(), "latencies_ms": [], "total_input_tokens": 0, "total_output_tokens": 0}


@lru_cache(maxsize=1)
def _chunk_store() -> dict[str, dict]:
    store = {}
    path = PROCESSED_DIR / "chunks_structured.jsonl"
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                c = json.loads(line)
                store[c["id"]] = c
    return store


def _get_graph():
    return compiled_graph()


def require_api_key(x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER)) -> None:
    expected = os.environ.get("SEBISAGE_API_KEY")
    if not expected or x_api_key != expected:
        raise HTTPException(status_code=401, detail="missing or invalid API key")


def check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = _rate_limit_hits[ip]
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="rate limit exceeded, try again shortly")
    window.append(now)


def _get_session(session_id: str | None) -> tuple[str, list]:
    now = time.time()
    for sid in [sid for sid, s in _sessions.items() if now - s["last_access"] > SESSION_TTL_S]:
        del _sessions[sid]

    if session_id and session_id in _sessions:
        _sessions[session_id]["last_access"] = now
        return session_id, _sessions[session_id]["messages"]

    new_id = session_id or str(uuid.uuid4())
    _sessions[new_id] = {"messages": [], "last_access": now}
    return new_id, []


def _append_turn(session_id: str, question: str, answer: str | None) -> None:
    _sessions[session_id]["messages"].append(HumanMessage(content=question))
    _sessions[session_id]["messages"].append(AIMessage(content=answer or ""))


def _estimate_cost(usage: dict) -> float:
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    return round((input_tokens / 1000) * COST_PER_1K_INPUT + (output_tokens / 1000) * COST_PER_1K_OUTPUT, 6)


def _citations_with_metadata(citations: list[str]) -> list[dict]:
    store = _chunk_store()
    out = []
    for ref in citations:
        chunk = store.get(ref)
        if chunk:
            out.append({"source": ref, "regulation": chunk["regulation"], "reg_no": chunk["reg_no"], "page": chunk["page_start"]})
        else:
            out.append({"source": ref, "regulation": None, "reg_no": None, "page": None})
    return out


def _record_stats(route: str | None, latency_ms: float, usage: dict) -> None:
    _stats["queries"] += 1
    _stats["route_counts"][route or "unknown"] += 1
    _stats["latencies_ms"].append(latency_ms)
    _stats["total_input_tokens"] += usage.get("input_tokens", 0)
    _stats["total_output_tokens"] += usage.get("output_tokens", 0)


class AskRequest(BaseModel):
    question: str
    session_id: str | None = None


class Citation(BaseModel):
    source: str
    regulation: str | None = None
    reg_no: str | None = None
    page: int | None = None


class AskResponse(BaseModel):
    answer: str | None
    citations: list[Citation]
    route: str
    grounded: bool
    usage: dict
    estimated_cost_usd: float
    latency_ms: float
    trace_id: str
    session_id: str


def _run_ask(payload: AskRequest, request: Request) -> tuple[dict, str, str, float]:
    """Shared /ask and /ask/stream logic. Returns (result, trace_id, session_id, latency_ms)."""
    check_rate_limit(request)
    guard = check_input(payload.question)
    if not guard.allowed:
        raise HTTPException(status_code=400, detail=guard.reason)

    session_id, history = _get_session(payload.session_id)
    trace_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    result = _get_graph().invoke({"question": guard.text, "messages": history})
    latency_ms = (time.perf_counter() - t0) * 1000

    _append_turn(session_id, guard.text, result.get("answer"))
    _record_stats(result.get("route"), latency_ms, result.get("usage_total") or {})

    return result, trace_id, session_id, latency_ms


@app.get("/health")
def health() -> dict:
    index_stats_path = REPORTS_DIR / "index_stats.json"
    index_stats = json.loads(index_stats_path.read_text(encoding="utf-8")) if index_stats_path.exists() else {}
    build_mtime = None
    if CHROMA_DIR.exists():
        files = [f.stat().st_mtime for f in CHROMA_DIR.rglob("*") if f.is_file()]
        if files:
            build_mtime = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(max(files)))
    return {
        "status": "ok",
        "generation_model": GEMINI_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "reranker_model": RERANKER_MODEL,
        "index_stats": index_stats,
        "index_build_date": build_mtime,
    }


@app.post("/ask", response_model=AskResponse, dependencies=[Depends(require_api_key)])
def ask(payload: AskRequest, request: Request) -> AskResponse:
    result, trace_id, session_id, latency_ms = _run_ask(payload, request)
    usage = result.get("usage_total") or {}
    return AskResponse(
        answer=result.get("answer"),
        citations=[Citation(**c) for c in _citations_with_metadata(result.get("citations") or [])],
        route=result.get("route", "unknown"),
        grounded=result.get("grounded", False),
        usage=usage,
        estimated_cost_usd=_estimate_cost(usage),
        latency_ms=latency_ms,
        trace_id=trace_id,
        session_id=session_id,
    )


@app.post("/ask/stream", dependencies=[Depends(require_api_key)])
def ask_stream(payload: AskRequest, request: Request) -> EventSourceResponse:
    """Runs the full grounded chain first (grounding must see the complete text
    before it can decide whether a retry is needed - see generate/answer.py),
    then streams the already-validated final answer back to the client in
    word chunks. This is not raw token-level provider streaming: it can't be,
    without either streaming an answer that might get silently replaced by a
    grounding retry, or losing the grounding check entirely."""
    result, trace_id, session_id, _latency_ms = _run_ask(payload, request)
    citations = _citations_with_metadata(result.get("citations") or [])
    answer_text = result.get("answer") or ""

    def event_generator():
        yield {"event": "route", "data": json.dumps({"route": result.get("route"), "trace_id": trace_id})}
        for word in answer_text.split(" "):
            if word:
                yield {"event": "token", "data": word + " "}
        yield {"event": "citations", "data": json.dumps({"citations": citations, "grounded": result.get("grounded", False), "session_id": session_id})}

    return EventSourceResponse(event_generator())


@app.get("/sources/{chunk_id}")
def get_source(chunk_id: str) -> dict:
    chunk = _chunk_store().get(chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="chunk not found")
    return chunk


@app.get("/stats")
def stats() -> dict:
    cache = get_cache_stats()
    n = _stats["queries"]
    return {
        "queries": n,
        "route_counts": dict(_stats["route_counts"]),
        "cache_hit_rate": cache["hit_rate"],
        "mean_latency_ms": round(sum(_stats["latencies_ms"]) / n, 1) if n else 0.0,
        "total_input_tokens": _stats["total_input_tokens"],
        "total_output_tokens": _stats["total_output_tokens"],
    }
