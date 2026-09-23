"""Input guardrails: length, injection patterns, PII masking."""

import re
from dataclasses import dataclass

from sebisage.config import MAX_QUESTION_CHARS

_INJECTION_PATTERNS = [
    re.compile(r"ignore (all |any )?(previous|prior|above|earlier) instructions", re.IGNORECASE),
    re.compile(r"disregard (all |any )?(previous|prior|above|earlier)", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"\byou are now\b", re.IGNORECASE),
    re.compile(r"act as (if|though) you", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"reveal (your|the) (instructions|prompt)", re.IGNORECASE),
    re.compile(r"pretend (you are|to be)", re.IGNORECASE),
]

# PAN: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F). Aadhaar: 12 digits,
# optionally grouped in 4s. Indian mobile: 10 digits starting 6-9, optional +91.
_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_AADHAAR_RE = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str | None
    text: str  # PII-masked if allowed, original if rejected


def check_length(text: str) -> str | None:
    if len(text) > MAX_QUESTION_CHARS:
        return f"question exceeds {MAX_QUESTION_CHARS} characters"
    return None


def check_injection(text: str) -> str | None:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return "potential prompt injection detected"
    return None


def mask_pii(text: str) -> str:
    text = _PAN_RE.sub("[PAN_REDACTED]", text)
    text = _AADHAAR_RE.sub("[AADHAAR_REDACTED]", text)
    text = _PHONE_RE.sub("[PHONE_REDACTED]", text)
    return text


def check_input(text: str) -> GuardrailResult:
    """Length and injection checks reject outright; PII is masked, not rejected."""
    reason = check_length(text) or check_injection(text)
    if reason:
        return GuardrailResult(allowed=False, reason=reason, text=text)
    return GuardrailResult(allowed=True, reason=None, text=mask_pii(text))
