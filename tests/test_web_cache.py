"""Tests for sebisage.retrieve.web_cache. All mocked -- no real network calls."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from sebisage.retrieve import web_cache


class _FakeResponse:
    def __init__(self, status_code: int, headers: dict, body: bytes):
        self.status_code = status_code
        self.headers = headers
        self._body = body

    def iter_bytes(self):
        chunk_size = 4096
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i : i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeClient:
    """Stands in for httpx.Client(); `responses` is consumed one per .stream() call
    (supports a redirect hop followed by the real response)."""

    def __init__(self, responses=None, raise_exc: Exception | None = None):
        self._responses = list(responses or [])
        self._raise_exc = raise_exc

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def stream(self, method, url, headers=None):
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._responses.pop(0)


@pytest.fixture(autouse=True)
def _isolated_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(web_cache, "WEB_CACHE_DIR", tmp_path)


def test_non_sebi_url_rejected_without_network_call(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("no network call should happen for a disallowed domain")

    monkeypatch.setattr(web_cache.httpx, "Client", boom)
    assert web_cache.fetch_sebi_content("https://evil.example.com/page") is None


def test_valid_sebi_html_fetch_extracts_text_and_writes_cache(monkeypatch):
    html = b"<html><body><script>ignored()</script><p>Regulation 30 disclosure rules.</p></body></html>"
    resp = _FakeResponse(200, {"content-type": "text/html; charset=utf-8"}, html)
    monkeypatch.setattr(web_cache.httpx, "Client", lambda **k: _FakeClient([resp]))

    text = web_cache.fetch_sebi_content("https://www.sebi.gov.in/legal/regulations/reg30")
    assert text == "Regulation 30 disclosure rules."

    cached_files = list(web_cache.WEB_CACHE_DIR.glob("*.json"))
    assert len(cached_files) == 1
    data = json.loads(cached_files[0].read_text(encoding="utf-8"))
    assert data["text"] == text


def test_valid_sebi_pdf_fetch_extracted_via_pymupdf(monkeypatch):
    resp = _FakeResponse(200, {"content-type": "application/pdf"}, b"%PDF-fake-bytes")
    monkeypatch.setattr(web_cache.httpx, "Client", lambda **k: _FakeClient([resp]))

    class _FakePage:
        def get_text(self):
            return "Regulation 30 text from PDF."

    class _FakeDoc:
        page_count = 1

        def __getitem__(self, idx):
            return _FakePage()

    import types

    fake_fitz = types.SimpleNamespace(open=lambda stream, filetype: _FakeDoc())
    monkeypatch.setitem(__import__("sys").modules, "fitz", fake_fitz)

    text = web_cache.fetch_sebi_content("https://sebi.gov.in/circular.pdf")
    assert text == "Regulation 30 text from PDF."


def test_timeout_returns_none(monkeypatch):
    monkeypatch.setattr(web_cache.httpx, "Client", lambda **k: _FakeClient(raise_exc=httpx.TimeoutException("timed out")))
    assert web_cache.fetch_sebi_content("https://sebi.gov.in/slow") is None


def test_oversized_download_is_truncated_not_crashed(monkeypatch):
    big_body = b"a" * (web_cache.WEB_FETCH_MAX_BYTES + 5000)
    resp = _FakeResponse(200, {"content-type": "text/html"}, big_body)
    monkeypatch.setattr(web_cache.httpx, "Client", lambda **k: _FakeClient([resp]))

    text = web_cache.fetch_sebi_content("https://sebi.gov.in/huge")
    assert text is not None
    assert len(text) <= web_cache.WEB_FETCH_MAX_CHARS


def test_extraction_failure_returns_none(monkeypatch):
    resp = _FakeResponse(200, {"content-type": "application/pdf"}, b"%PDF-broken")
    monkeypatch.setattr(web_cache.httpx, "Client", lambda **k: _FakeClient([resp]))

    import types

    def _raise_open(*a, **k):
        raise RuntimeError("corrupt pdf")

    fake_fitz = types.SimpleNamespace(open=_raise_open)
    monkeypatch.setitem(__import__("sys").modules, "fitz", fake_fitz)

    assert web_cache.fetch_sebi_content("https://sebi.gov.in/broken.pdf") is None


def test_cache_hit_makes_no_network_call(monkeypatch, tmp_path):
    url = "https://sebi.gov.in/cached-page"
    path = web_cache._cache_path(url)
    path.write_text(
        json.dumps({"url": url, "fetched_at": datetime.now(UTC).isoformat(), "text": "cached text"}),
        encoding="utf-8",
    )

    def boom(*a, **k):
        raise AssertionError("cache hit should not make a network call")

    monkeypatch.setattr(web_cache.httpx, "Client", boom)
    assert web_cache.fetch_sebi_content(url) == "cached text"


def test_cache_expired_refetches(monkeypatch):
    url = "https://sebi.gov.in/stale-page"
    path = web_cache._cache_path(url)
    stale_time = datetime.now(UTC) - timedelta(hours=web_cache.WEB_CACHE_TTL_HOURS + 1)
    path.write_text(
        json.dumps({"url": url, "fetched_at": stale_time.isoformat(), "text": "old text"}),
        encoding="utf-8",
    )

    resp = _FakeResponse(200, {"content-type": "text/html"}, b"<p>fresh text</p>")
    monkeypatch.setattr(web_cache.httpx, "Client", lambda **k: _FakeClient([resp]))

    assert web_cache.fetch_sebi_content(url) == "fresh text"


def test_redirect_to_non_sebi_domain_rejected(monkeypatch):
    redirect = _FakeResponse(302, {"location": "https://evil.example.com/steal"}, b"")
    monkeypatch.setattr(web_cache.httpx, "Client", lambda **k: _FakeClient([redirect]))
    assert web_cache.fetch_sebi_content("https://sebi.gov.in/redirector") is None


def test_answer_from_web_falls_back_to_snippets_when_fetch_returns_none():
    from sebisage.agent import nodes
    from sebisage.generate.llm import LLMResult

    class FakeLLMClient:
        def invoke(self, messages, prompt_version="v1"):
            return LLMResult(text="snippet-based answer", input_tokens=1, output_tokens=1, cached=False)

    results = [{"title": "t", "href": "https://sebi.gov.in/x", "body": "snippet"}]
    out = nodes.answer_from_web(
        {"standalone_question": "q", "web_results": results, "fetched_text": None, "fetched_url": None},
        llm_client=FakeLLMClient(),
    )
    assert out["source_type"] == "search_snippets"
    assert out["citations"] == ["https://sebi.gov.in/x"]
