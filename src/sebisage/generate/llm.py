"""Gemini wrapper with disk cache and token counting."""

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from sebisage.config import CACHE_DIR, GEMINI_MODEL, MAX_WAIT_S, REQUEST_TIMEOUT_S
from sebisage.generate.prompts import PROMPT_VERSION

_ROLE_TO_MESSAGE = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}


class QuotaExceededError(Exception):
    """Raised when the Gemini API returns a 429; carries a suggested retry delay."""

    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(f"quota exceeded, retry_after={retry_after}")


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    cached: bool
    error: str | None = None


def _cache_key(model: str, prompt_version: str, messages: list[dict]) -> str:
    payload = json.dumps({"model": model, "prompt_version": prompt_version, "messages": messages}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _to_langchain_messages(messages: list[dict]) -> list:
    return [_ROLE_TO_MESSAGE[m["role"]](content=m["content"]) for m in messages]


def _extract_text(content: str | list) -> str:
    """LangChain's Gemini integration returns .content as a list of
    {"type": "text", "text": ...} parts rather than a plain string."""
    if isinstance(content, str):
        return content
    parts = []
    for part in content:
        if isinstance(part, str):
            parts.append(part)
        elif isinstance(part, dict):
            parts.append(part.get("text", ""))
    return "".join(parts)


def _extract_retry_delay(exc: Exception) -> float | None:
    """Best-effort parse of a Google API error's RetryInfo (e.g. "13s") -> seconds."""
    details = getattr(exc, "details", None)
    entries = details if isinstance(details, list) else [details] if details else []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        delay = entry.get("retryDelay") or entry.get("retry_delay")
        if isinstance(delay, str):
            m = re.match(r"([\d.]+)s?", delay)
            if m:
                return float(m.group(1))
    return None


class LLMClient:
    """Caches (model, prompt_version, messages) -> response on disk; never raises on quota errors."""

    def __init__(self, model_name: str = GEMINI_MODEL, cache_dir: Path = CACHE_DIR):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._model = None
        self.last_usage: dict | None = None

    def _get_model(self):
        if self._model is None:
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._model = ChatGoogleGenerativeAI(model=self.model_name, timeout=REQUEST_TIMEOUT_S)
        return self._model

    def _call(self, lc_messages: list):
        """Calls the real model, translating a 429 into QuotaExceededError."""
        try:
            return self._get_model().invoke(lc_messages)
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code == 429 or "429" in type(exc).__name__:
                raise QuotaExceededError(retry_after=_extract_retry_delay(exc)) from exc
            raise

    def invoke(self, messages: list[dict], prompt_version: str = PROMPT_VERSION) -> LLMResult:
        key = _cache_key(self.model_name, prompt_version, messages)
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            result = LLMResult(text=data["text"], input_tokens=data["input_tokens"], output_tokens=data["output_tokens"], cached=True)
            self.last_usage = {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens}
            return result

        lc_messages = _to_langchain_messages(messages)
        try:
            response = self._call(lc_messages)
        except QuotaExceededError as exc:
            delay = exc.retry_after if exc.retry_after is not None else min(5.0, MAX_WAIT_S)
            if delay > MAX_WAIT_S:
                return LLMResult(text="", input_tokens=0, output_tokens=0, cached=False, error="quota_exceeded")
            time.sleep(delay)
            try:
                response = self._call(lc_messages)
            except QuotaExceededError:
                return LLMResult(text="", input_tokens=0, output_tokens=0, cached=False, error="quota_exceeded")

        usage = getattr(response, "usage_metadata", None) or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        result = LLMResult(text=_extract_text(response.content), input_tokens=input_tokens, output_tokens=output_tokens, cached=False)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"text": result.text, "input_tokens": input_tokens, "output_tokens": output_tokens}),
            encoding="utf-8",
        )
        self.last_usage = {"input_tokens": input_tokens, "output_tokens": output_tokens}
        return result
