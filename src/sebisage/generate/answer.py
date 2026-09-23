"""LangChain answer chain with citations."""

import json
import re
import time
from functools import lru_cache

from sebisage.config import K_FINAL, K_FUSED, PROCESSED_DIR
from sebisage.generate.grounding import check_grounding
from sebisage.generate.llm import LLMClient
from sebisage.generate.prompts import ANSWER_PROMPT_V1, GROUNDING_RETRY_SUFFIX, PROMPT_VERSION
from sebisage.retrieve.hybrid import retrieve as hybrid_retrieve
from sebisage.retrieve.rerank import rerank

_CITATION_RE = re.compile(r"\[(\d+)\]")


@lru_cache(maxsize=1)
def _chunk_store() -> dict[str, dict]:
    store = {}
    with (PROCESSED_DIR / "chunks_structured.jsonl").open(encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            store[c["id"]] = c
    return store


def _format_context(chunks: list[dict]) -> str:
    """`chunks`: ordered list of {"id","text"}, numbered [1], [2], ... in that order."""
    return "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(chunks, start=1))


def _parse_citations(answer_text: str, chunks: list[dict]) -> list[str]:
    numbers = {int(n) for n in _CITATION_RE.findall(answer_text)}
    return [chunks[n - 1]["id"] for n in sorted(numbers) if 1 <= n <= len(chunks)]


def retrieve_context(question: str, k_final: int = K_FINAL) -> list[dict]:
    """Runs the Phase 3 winning pipeline (hybrid RRF + rerank) and returns chunk dicts with text."""
    store = _chunk_store()
    fused = hybrid_retrieve(question, "structured", k=K_FUSED)
    candidates = [{"id": h["id"], "text": store[h["id"]]["text"]} for h in fused if h["id"] in store]
    return rerank(question, candidates, k=k_final)


def answer(question: str, llm_client: LLMClient | None = None, k_final: int = K_FINAL) -> dict:
    """retrieve -> format context -> prompt -> llm -> parse, with one grounding-retry.

    Returns: {answer, citations, usage, latency_ms, grounded, grounding_flags} plus
    `error` if the LLM call failed (e.g. quota exceeded), in which case `answer` is None.
    """
    t0 = time.perf_counter()
    llm_client = llm_client or LLMClient()

    context_chunks = retrieve_context(question, k_final)
    context = _format_context(context_chunks)
    prompt = ANSWER_PROMPT_V1.format(context=context, question=question)

    result = llm_client.invoke([{"role": "user", "content": prompt}], prompt_version=PROMPT_VERSION)
    if result.error:
        return {
            "answer": None,
            "citations": [],
            "usage": {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens},
            "latency_ms": (time.perf_counter() - t0) * 1000,
            "grounded": False,
            "grounding_flags": [],
            "error": result.error,
        }

    grounding = check_grounding(result.text, context_chunks)
    total_input, total_output = result.input_tokens, result.output_tokens

    if not grounding.grounded:
        retry_prompt = prompt + GROUNDING_RETRY_SUFFIX.format(flags=", ".join(grounding.flags))
        retry_result = llm_client.invoke([{"role": "user", "content": retry_prompt}], prompt_version=f"{PROMPT_VERSION}-retry")
        if not retry_result.error:
            total_input += retry_result.input_tokens
            total_output += retry_result.output_tokens
            retry_grounding = check_grounding(retry_result.text, context_chunks)
            result, grounding = retry_result, retry_grounding

    citations = [] if result.text.strip().startswith("INSUFFICIENT_CONTEXT") else _parse_citations(result.text, context_chunks)

    return {
        "answer": result.text,
        "citations": citations,
        "usage": {"input_tokens": total_input, "output_tokens": total_output},
        "latency_ms": (time.perf_counter() - t0) * 1000,
        "grounded": grounding.grounded,
        "grounding_flags": grounding.flags,
    }
