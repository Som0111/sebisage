"""Tests for sebisage.generate.llm: disk cache and quota-error handling."""

from types import SimpleNamespace

import pytest

from sebisage.generate.llm import LLMClient, QuotaExceededError

MESSAGES = [{"role": "user", "content": "What is regulation 30?"}]


def _fake_response(text: str = "answer text") -> SimpleNamespace:
    return SimpleNamespace(content=text, usage_metadata={"input_tokens": 10, "output_tokens": 5})


def test_second_identical_call_hits_cache(tmp_path, monkeypatch):
    client = LLMClient(cache_dir=tmp_path)
    calls = []

    def fake_call(lc_messages):
        calls.append(lc_messages)
        return _fake_response()

    monkeypatch.setattr(client, "_call", fake_call)

    first = client.invoke(MESSAGES)
    second = client.invoke(MESSAGES)

    assert len(calls) == 1  # second call never hit _call
    assert first.cached is False
    assert second.cached is True
    assert first.text == second.text == "answer text"
    assert second.input_tokens == 10
    assert second.output_tokens == 5


def test_different_prompt_version_is_a_cache_miss(tmp_path, monkeypatch):
    client = LLMClient(cache_dir=tmp_path)
    calls = []
    monkeypatch.setattr(client, "_call", lambda lc_messages: calls.append(1) or _fake_response())

    client.invoke(MESSAGES, prompt_version="v1")
    client.invoke(MESSAGES, prompt_version="v2")

    assert len(calls) == 2


def test_quota_error_returns_error_object_never_crashes(tmp_path, monkeypatch):
    client = LLMClient(cache_dir=tmp_path)

    def always_quota(lc_messages):
        raise QuotaExceededError(retry_after=0.01)

    monkeypatch.setattr(client, "_call", always_quota)

    result = client.invoke(MESSAGES)

    assert result.error == "quota_exceeded"
    assert result.text == ""


def test_quota_error_recovers_on_retry(tmp_path, monkeypatch):
    client = LLMClient(cache_dir=tmp_path)
    attempts = {"n": 0}

    def flaky(lc_messages):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise QuotaExceededError(retry_after=0.01)
        return _fake_response("recovered")

    monkeypatch.setattr(client, "_call", flaky)

    result = client.invoke(MESSAGES)

    assert result.error is None
    assert result.text == "recovered"
    assert attempts["n"] == 2


def test_quota_error_with_delay_over_max_wait_gives_up_without_sleeping(tmp_path, monkeypatch):
    from sebisage import config

    monkeypatch.setattr(config, "MAX_WAIT_S", 5)
    monkeypatch.setattr("sebisage.generate.llm.MAX_WAIT_S", 5)

    client = LLMClient(cache_dir=tmp_path)

    def slow_quota(lc_messages):
        raise QuotaExceededError(retry_after=999)

    monkeypatch.setattr(client, "_call", slow_quota)

    result = client.invoke(MESSAGES)

    assert result.error == "quota_exceeded"


def test_no_exception_propagates_on_unexpected_quota_shape(tmp_path, monkeypatch):
    client = LLMClient(cache_dir=tmp_path)

    def always_quota(lc_messages):
        raise QuotaExceededError()  # no retry_after given -> falls back to a default delay

    monkeypatch.setattr(client, "_call", always_quota)
    monkeypatch.setattr("sebisage.generate.llm.time.sleep", lambda _seconds: None)

    try:
        result = client.invoke(MESSAGES)
    except QuotaExceededError:
        pytest.fail("QuotaExceededError should never propagate out of invoke()")

    assert result.error == "quota_exceeded"
