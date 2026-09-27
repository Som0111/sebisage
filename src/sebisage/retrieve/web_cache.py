"""Fetches and caches official content from sebi.gov.in for the "recent" web
route, instead of answering from search snippets alone.

Same disk-cache principle as generate/llm.py (hash key -> JSON file on disk),
but keyed by URL with a TTL instead of by (model, prompt, messages).
"""

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from sebisage.config import (
    SEBI_ALLOWED_DOMAINS,
    WEB_CACHE_DIR,
    WEB_CACHE_TTL_HOURS,
    WEB_FETCH_MAX_BYTES,
    WEB_FETCH_MAX_CHARS,
    WEB_FETCH_PDF_MAX_PAGES,
    WEB_FETCH_TIMEOUT_S,
    WEB_FETCH_USER_AGENT,
)

logger = logging.getLogger(__name__)

_MAX_REDIRECTS = 5
_REDIRECT_STATUS_CODES = (301, 302, 303, 307, 308)


def _is_allowed_domain(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in SEBI_ALLOWED_DOMAINS


def _cache_path(url: str) -> Path:
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return Path(WEB_CACHE_DIR) / f"{key}.json"


def _read_cache(url: str) -> str | None:
    path = _cache_path(url)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(data["fetched_at"])
    except (OSError, ValueError, KeyError):
        return None
    if datetime.now(UTC) - fetched_at > timedelta(hours=WEB_CACHE_TTL_HOURS):
        return None
    return data["text"]


def _write_cache(url: str, text: str) -> None:
    try:
        path = _cache_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"url": url, "fetched_at": datetime.now(UTC).isoformat(), "text": text}),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("failed to write web cache for %s: %s", url, exc)


def _read_capped(response: httpx.Response) -> bytes:
    total = 0
    chunks = []
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > WEB_FETCH_MAX_BYTES:
            keep = WEB_FETCH_MAX_BYTES - (total - len(chunk))
            if keep > 0:
                chunks.append(chunk[:keep])
            break
        chunks.append(chunk)
    return b"".join(chunks)


def _strip_html(html_text: str) -> str:
    from html.parser import HTMLParser

    class _TextExtractor(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.parts: list[str] = []
            self._skip = False

        def handle_starttag(self, tag: str, attrs) -> None:
            if tag in ("script", "style"):
                self._skip = True

        def handle_endtag(self, tag: str) -> None:
            if tag in ("script", "style"):
                self._skip = False

        def handle_data(self, data: str) -> None:
            if not self._skip:
                self.parts.append(data)

    parser = _TextExtractor()
    parser.feed(html_text)
    return " ".join(" ".join(parser.parts).split())


def _extract_text(content: bytes, content_type: str, url: str) -> str | None:
    if content_type == "application/pdf":
        try:
            import fitz

            doc = fitz.open(stream=content, filetype="pdf")
            pages = [doc[i].get_text() for i in range(min(doc.page_count, WEB_FETCH_PDF_MAX_PAGES))]
            text = "\n".join(pages)
        except Exception as exc:  # noqa: BLE001 - pymupdf raises various error types on malformed input
            logger.warning("PDF extraction failed for %s: %s", url, exc)
            return None
    elif content_type in ("text/html", "application/xhtml+xml"):
        text = _strip_html(content.decode("utf-8", errors="replace"))
    else:
        logger.warning("unsupported content-type %r for %s", content_type, url)
        return None

    text = text.strip()
    return text[:WEB_FETCH_MAX_CHARS] if text else None


def _fetch_and_extract(url: str) -> str | None:
    current_url = url
    headers = {"User-Agent": WEB_FETCH_USER_AGENT}

    with httpx.Client(timeout=WEB_FETCH_TIMEOUT_S) as client:
        for _ in range(_MAX_REDIRECTS):
            try:
                with client.stream("GET", current_url, headers=headers) as response:
                    if response.status_code in _REDIRECT_STATUS_CODES:
                        location = response.headers.get("location")
                        if not location:
                            logger.warning("redirect with no Location header from %s", current_url)
                            return None
                        next_url = urljoin(current_url, location)
                        if not _is_allowed_domain(next_url):
                            logger.warning("redirect to non-SEBI domain rejected: %s", next_url)
                            return None
                        current_url = next_url
                        continue

                    if response.status_code != 200:
                        logger.warning("non-200 status %s fetching %s", response.status_code, current_url)
                        return None

                    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    content = _read_capped(response)
                    return _extract_text(content, content_type, current_url)
            except httpx.TimeoutException:
                logger.warning("timeout fetching %s", current_url)
                return None
            except httpx.HTTPError as exc:
                logger.warning("HTTP error fetching %s: %s", current_url, exc)
                return None

    logger.warning("too many redirects fetching %s", url)
    return None


def fetch_sebi_content(url: str) -> str | None:
    """Best-effort: returns extracted text from an official sebi.gov.in page or
    PDF, using a TTL disk cache. Returns None (never raises) on any failure --
    invalid domain, timeout, oversized download, unsupported content type, or
    extraction error."""
    if not _is_allowed_domain(url):
        logger.warning("rejected URL not on an approved SEBI domain: %s", url)
        return None

    cached = _read_cache(url)
    if cached is not None:
        return cached

    try:
        text = _fetch_and_extract(url)
    except Exception as exc:  # noqa: BLE001 - defensive: this function must never raise
        logger.warning("unexpected error fetching %s: %s", url, exc)
        return None

    if text:
        _write_cache(url, text)
    return text
