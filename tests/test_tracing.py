"""Tests for sebisage.tracing: must be a safe no-op with no Langfuse keys configured."""

from sebisage import tracing


def test_tracing_disabled_without_keys(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    assert tracing.tracing_enabled() is False

    trace_id, handler = tracing.new_trace()
    assert isinstance(trace_id, str) and trace_id
    assert handler is None

    assert tracing.trace_url(trace_id) is None
    tracing.flush()  # must not raise


def test_new_trace_returns_handler_when_keys_present(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    assert tracing.tracing_enabled() is True

    trace_id, handler = tracing.new_trace()
    assert isinstance(trace_id, str) and trace_id
    assert handler is not None
