"""Langfuse setup; no-op if keys are missing."""

import os
import uuid

from langfuse import get_client
from langfuse.langchain import CallbackHandler


def tracing_enabled() -> bool:
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY")) and bool(os.environ.get("LANGFUSE_SECRET_KEY"))


def new_trace() -> tuple[str, CallbackHandler | None]:
    """(trace_id, handler). `trace_id` is always a usable id, even when tracing
    is disabled (for logging/correlation); `handler` is None when Langfuse keys
    aren't configured, so callers simply attach no callback and nothing is sent.
    """
    if not tracing_enabled():
        return str(uuid.uuid4()), None
    trace_id = get_client().create_trace_id()
    return trace_id, CallbackHandler(trace_context={"trace_id": trace_id})


def trace_url(trace_id: str) -> str | None:
    if not tracing_enabled():
        return None
    return get_client().get_trace_url(trace_id=trace_id)


def flush() -> None:
    """Force-send buffered spans. Call at the end of a short-lived request/script
    so traces show up promptly rather than waiting for the batch export timer."""
    if tracing_enabled():
        get_client().flush()
