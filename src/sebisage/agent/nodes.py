"""Router, rag, web_search, refuse, rewrite_followup nodes."""

from ddgs import DDGS
from ddgs.exceptions import DDGSException

from sebisage.agent.state import AgentState
from sebisage.config import MEMORY_TURNS, REFUSE_THRESHOLD
from sebisage.generate.answer import answer as run_answer_chain
from sebisage.generate.answer import retrieve_context
from sebisage.generate.llm import LLMClient
from sebisage.generate.prompts import (
    REFUSE_MESSAGE,
    REWRITE_FOLLOWUP_PROMPT,
    ROUTER_CLASSIFIER_PROMPT,
    WEB_ANSWER_PROMPT,
)

# Cheap, free first stage: obvious "ask about something the index can't have"
# keywords route straight to web search before spending a retrieval call.
_RECENT_KEYWORDS = ["latest", "recent circular", "new circular", "new rule", "this year", "2026", "2027"]


def rewrite_followup(state: AgentState, llm_client: LLMClient | None = None) -> dict:
    """Rewrites the latest question into a standalone one using the last MEMORY_TURNS turns.
    Unchanged (and no LLM call) if there is no prior conversation."""
    messages = state.get("messages") or []
    question = state["question"]
    history = messages[-(MEMORY_TURNS * 2) :]
    if not history:
        return {"standalone_question": question}

    llm_client = llm_client or LLMClient()
    history_text = "\n".join(f"{m.type}: {m.content}" for m in history)
    prompt = REWRITE_FOLLOWUP_PROMPT.format(history=history_text, question=question)
    result = llm_client.invoke([{"role": "user", "content": prompt}], prompt_version="rewrite-v1")
    standalone = result.text.strip() if not result.error and result.text.strip() else question
    return {"standalone_question": standalone}


def router(state: AgentState, llm_client: LLMClient | None = None) -> dict:
    """Rules first (free), then retrieval confidence, then an LLM classifier only when unsure."""
    question = state["standalone_question"]
    lower = question.lower()

    for kw in _RECENT_KEYWORDS:
        if kw in lower:
            return {"route": "recent", "route_reason": f"keyword match: '{kw}'", "retrieved": []}

    context_chunks = retrieve_context(question)
    top_score = context_chunks[0]["rerank_score"] if context_chunks else None

    if top_score is not None and top_score >= REFUSE_THRESHOLD:
        return {"route": "regulation", "route_reason": f"high retrieval confidence ({top_score:.2f})", "retrieved": context_chunks}

    llm_client = llm_client or LLMClient()
    prompt = ROUTER_CLASSIFIER_PROMPT.format(question=question)
    result = llm_client.invoke([{"role": "user", "content": prompt}], prompt_version="router-v1")
    label = result.text.strip().lower() if not result.error else "regulation"
    route = "out_of_scope" if "out_of_scope" in label or "out of scope" in label else "regulation"
    reason = f"low retrieval confidence ({top_score}), classifier said '{label}'"
    return {"route": route, "route_reason": reason, "retrieved": context_chunks}


def rag(state: AgentState, llm_client: LLMClient | None = None) -> dict:
    """The Phase 4 grounded answer chain, reusing the router's retrieval when available."""
    question = state["standalone_question"]
    result = run_answer_chain(question, llm_client=llm_client, context_chunks=state.get("retrieved") or None)
    return {
        "answer": result.get("answer"),
        "citations": result.get("citations", []),
        "grounded": result.get("grounded", False),
        "grounding_flags": result.get("grounding_flags", []),
        "usage_total": result.get("usage", {}),
    }


def grounding_check(state: AgentState) -> dict:
    """Pass-through checkpoint node: rag() already ran check_grounding (with its own
    retry) internally, so this node exists only as a distinct graph/trace point
    (a separate Langfuse span in Phase 7), not to redo the check."""
    return {}


def web_search(state: AgentState) -> dict:
    """DuckDuckGo search restricted to sebi.gov.in, top 5 results. Never raises -
    an empty result list on rate-limit/no-result is handled by answer_from_web."""
    question = state["standalone_question"]
    try:
        results = DDGS().text(f"site:sebi.gov.in {question}", max_results=5)
    except DDGSException:
        results = []
    return {"web_results": results}


def answer_from_web(state: AgentState, llm_client: LLMClient | None = None) -> dict:
    results = state.get("web_results") or []
    if not results:
        return {
            "answer": "I couldn't find any recent sebi.gov.in results for that. Please try rephrasing, or check sebi.gov.in directly.",
            "citations": [],
            "grounded": True,
            "grounding_flags": [],
            "usage_total": {},
        }

    formatted = "\n\n".join(f"[{i}] {r.get('title', '')}\nURL: {r.get('href', '')}\n{r.get('body', '')}" for i, r in enumerate(results, start=1))
    prompt = WEB_ANSWER_PROMPT.format(results=formatted, question=state["standalone_question"])

    llm_client = llm_client or LLMClient()
    result = llm_client.invoke([{"role": "user", "content": prompt}], prompt_version="web-answer-v1")
    if result.error:
        return {
            "answer": None,
            "citations": [],
            "grounded": False,
            "grounding_flags": [],
            "usage_total": {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens},
        }

    citations = [r.get("href", "") for r in results]
    return {
        "answer": result.text,
        "citations": citations,
        "grounded": True,
        "grounding_flags": [],
        "usage_total": {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens},
    }


def refuse(state: AgentState) -> dict:
    return {"answer": REFUSE_MESSAGE, "citations": [], "grounded": True, "grounding_flags": [], "usage_total": {}}
