"""Tests for sebisage.generate.answer_eval, httpx mocked throughout."""

import httpx

from sebisage.generate import answer_eval

ITEMS = [{"id": "q1", "input": "question + context", "output": "the answer [1]."}]


class _FakeResponse:
    def __init__(self, json_body: dict, status_code: int = 200):
        self._json_body = json_body
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json_body


def _ok_response(n: int = 1, judge=None, failed: int = 0) -> _FakeResponse:
    results = [
        {"scores": {"length": 1.0, "keyword_overlap": 0.6, "format": 1.0, "relevance": 0.78}, "judge": judge, "judge_prompt_version": "v2", "judge_model": "m"}
        for _ in range(n)
    ]
    return _FakeResponse({"results": results, "total": n, "failed": failed})


def test_no_config_returns_skipped(monkeypatch):
    monkeypatch.delenv("EVALFORGE_URL", raising=False)
    monkeypatch.delenv("EVALFORGE_API_KEY", raising=False)
    result = answer_eval.evaluate_answers(ITEMS)
    assert result["status"] == "skipped"


def test_successful_batch_aggregates_scores(monkeypatch):
    monkeypatch.setenv("EVALFORGE_URL", "https://evalforge.example")
    monkeypatch.setenv("EVALFORGE_API_KEY", "key")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _ok_response(n=1))

    result = answer_eval.evaluate_answers(ITEMS)

    assert result["status"] == "ok"
    assert result["n_items"] == 1
    assert result["mean_scores"]["relevance"] == 0.78
    assert result["n_judged"] == 0
    assert "caveated" in result["judge_note"]
    assert result["per_item"][0]["id"] == "q1"


def test_judge_present_is_counted(monkeypatch):
    monkeypatch.setenv("EVALFORGE_URL", "https://evalforge.example")
    monkeypatch.setenv("EVALFORGE_API_KEY", "key")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _ok_response(n=1, judge={"correctness": 4}))

    result = answer_eval.evaluate_answers(ITEMS)
    assert result["n_judged"] == 1


def test_retries_once_after_transient_failure_then_succeeds(monkeypatch):
    monkeypatch.setenv("EVALFORGE_URL", "https://evalforge.example")
    monkeypatch.setenv("EVALFORGE_API_KEY", "key")
    monkeypatch.setattr(answer_eval.time, "sleep", lambda _s: None)

    calls = {"n": 0}

    def flaky_post(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("connection refused")
        return _ok_response(n=1)

    monkeypatch.setattr(httpx, "post", flaky_post)

    result = answer_eval.evaluate_answers(ITEMS)
    assert result["status"] == "ok"
    assert calls["n"] == 2


def test_still_unreachable_after_retry_is_skipped_not_raised(monkeypatch):
    monkeypatch.setenv("EVALFORGE_URL", "https://evalforge.example")
    monkeypatch.setenv("EVALFORGE_API_KEY", "key")
    monkeypatch.setattr(answer_eval.time, "sleep", lambda _s: None)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("down")))

    result = answer_eval.evaluate_answers(ITEMS)
    assert result["status"] == "skipped"
    assert "unreachable" in result["reason"]


def test_batches_split_at_max_size(monkeypatch):
    monkeypatch.setenv("EVALFORGE_URL", "https://evalforge.example")
    monkeypatch.setenv("EVALFORGE_API_KEY", "key")
    many_items = [{"id": f"q{i}", "input": "x", "output": "y"} for i in range(75)]

    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append(len(json["items"]))
        return _ok_response(n=len(json["items"]))

    monkeypatch.setattr(httpx, "post", fake_post)

    result = answer_eval.evaluate_answers(many_items)
    assert calls == [50, 25]
    assert result["n_items"] == 75


def test_empty_items_is_skipped():
    result = answer_eval.evaluate_answers([])
    assert result["status"] == "skipped"
