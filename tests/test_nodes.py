"""Tests for sebisage.agent.nodes, all mocked (no real LLM/retrieval/search calls)."""

from langchain_core.messages import AIMessage, HumanMessage

from sebisage.agent import nodes
from sebisage.generate.llm import LLMResult

CONTEXT = [{"id": "lodr_2015.pdf:30:1-2:0", "text": "Every listed entity shall disclose material events [1]."}]


class FakeLLMClient:
    def __init__(self, text: str, error: str | None = None):
        self.text = text
        self.error = error
        self.calls: list[dict] = []

    def invoke(self, messages, prompt_version="v1"):
        self.calls.append({"messages": messages, "prompt_version": prompt_version})
        return LLMResult(text=self.text, input_tokens=5, output_tokens=5, cached=False, error=self.error)


# --- rewrite_followup ---


def test_rewrite_followup_no_history_is_unchanged_and_skips_llm():
    state = {"question": "What is Regulation 30?", "messages": []}
    out = nodes.rewrite_followup(state, llm_client="should never be used")
    assert out == {"standalone_question": "What is Regulation 30?"}


def test_rewrite_followup_with_history_calls_llm_and_rewrites():
    state = {
        "question": "What about for insiders?",
        "messages": [
            HumanMessage(content="What is unpublished price sensitive information?"),
            AIMessage(content="UPSI is information that is not generally available..."),
        ],
    }
    client = FakeLLMClient("What are the disclosure obligations for insiders under PIT Regulations?")
    out = nodes.rewrite_followup(state, llm_client=client)
    assert out["standalone_question"] == "What are the disclosure obligations for insiders under PIT Regulations?"
    assert len(client.calls) == 1
    assert "unpublished price sensitive information" in client.calls[0]["messages"][0]["content"]


# --- router ---


def test_router_recent_keyword_short_circuits_before_retrieval(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("retrieve_context should not be called for a keyword match")

    monkeypatch.setattr(nodes, "retrieve_context", boom)
    state = {"standalone_question": "What is the latest circular on disclosures?"}
    out = nodes.router(state)
    assert out["route"] == "recent"


def test_router_high_confidence_routes_to_regulation_without_llm(monkeypatch):
    monkeypatch.setattr(nodes, "retrieve_context", lambda q: [{"id": "c1", "rerank_score": 5.0}])
    monkeypatch.setattr(nodes, "REFUSE_THRESHOLD", 0.0)
    state = {"standalone_question": "When must a company disclose a material event?"}
    out = nodes.router(state, llm_client="should never be used")
    assert out["route"] == "regulation"


def test_router_low_confidence_defers_to_classifier_regulation(monkeypatch):
    monkeypatch.setattr(nodes, "retrieve_context", lambda q: [{"id": "c1", "rerank_score": -5.0}])
    monkeypatch.setattr(nodes, "REFUSE_THRESHOLD", 0.0)
    client = FakeLLMClient("regulation")
    out = nodes.router({"standalone_question": "some obscure question"}, llm_client=client)
    assert out["route"] == "regulation"
    assert len(client.calls) == 1


def test_router_low_confidence_defers_to_classifier_out_of_scope(monkeypatch):
    monkeypatch.setattr(nodes, "retrieve_context", lambda q: [{"id": "c1", "rerank_score": -5.0}])
    monkeypatch.setattr(nodes, "REFUSE_THRESHOLD", 0.0)
    client = FakeLLMClient("out_of_scope")
    out = nodes.router({"standalone_question": "what's the weather today"}, llm_client=client)
    assert out["route"] == "out_of_scope"


def test_router_empty_retrieval_defers_to_classifier(monkeypatch):
    monkeypatch.setattr(nodes, "retrieve_context", lambda q: [])
    client = FakeLLMClient("out_of_scope")
    out = nodes.router({"standalone_question": "??"}, llm_client=client)
    assert out["route"] == "out_of_scope"


# --- rag ---


def test_rag_delegates_to_answer_chain_and_reuses_retrieval(monkeypatch):
    captured = {}

    def fake_answer(question, llm_client=None, context_chunks=None):
        captured["context_chunks"] = context_chunks
        return {"answer": "text [1]", "citations": ["lodr_2015.pdf:30:1-2:0"], "grounded": True, "grounding_flags": [], "usage": {"input_tokens": 1, "output_tokens": 1}}

    monkeypatch.setattr(nodes, "run_answer_chain", fake_answer)
    state = {"standalone_question": "q", "retrieved": CONTEXT}
    out = nodes.rag(state)
    assert out["answer"] == "text [1]"
    assert out["grounded"] is True
    assert captured["context_chunks"] == CONTEXT  # reused, not re-retrieved


# --- web_search / answer_from_web ---


def test_web_search_handles_exception_gracefully(monkeypatch):
    from ddgs.exceptions import DDGSException

    class FailingDDGS:
        def text(self, *a, **k):
            raise DDGSException("rate limited")

    monkeypatch.setattr(nodes, "DDGS", lambda: FailingDDGS())
    out = nodes.web_search({"standalone_question": "recent circular"})
    assert out["web_results"] == []


def test_answer_from_web_no_results_is_graceful():
    out = nodes.answer_from_web({"standalone_question": "q", "web_results": []})
    assert out["grounded"] is True
    assert "rephrasing" in out["answer"] or "sebi.gov.in" in out["answer"]


def test_answer_from_web_with_results_cites_urls():
    results = [{"title": "SEBI Circular", "href": "https://www.sebi.gov.in/foo", "body": "snippet text"}]
    client = FakeLLMClient("Based on the circular... Based on search snippets; verify on sebi.gov.in.")
    out = nodes.answer_from_web({"standalone_question": "q", "web_results": results}, llm_client=client)
    assert out["citations"] == ["https://www.sebi.gov.in/foo"]
    assert out["grounded"] is True


# --- refuse ---


def test_refuse_returns_scope_message():
    out = nodes.refuse({})
    assert "LODR" in out["answer"]
    assert out["citations"] == []
    assert out["grounded"] is True
