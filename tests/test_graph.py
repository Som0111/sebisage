"""End-to-end tests for the compiled agent graph, all 3 routes, fully mocked."""

from sebisage.agent import nodes
from sebisage.agent.graph import compiled_graph
from sebisage.generate.llm import LLMResult


class FakeLLMClient:
    def __init__(self, text: str):
        self.text = text

    def invoke(self, messages, prompt_version="v1"):
        return LLMResult(text=self.text, input_tokens=5, output_tokens=5, cached=False, error=None)


def _patch_llm_client(monkeypatch, text: str):
    monkeypatch.setattr(nodes, "LLMClient", lambda: FakeLLMClient(text))


def test_regulation_route_end_to_end(monkeypatch):
    monkeypatch.setattr(nodes, "retrieve_context", lambda q: [{"id": "lodr_2015.pdf:30:1-2:0", "text": "chunk text", "rerank_score": 5.0}])
    monkeypatch.setattr(
        nodes,
        "run_answer_chain",
        lambda question, llm_client=None, context_chunks=None: {
            "answer": "Material events must be disclosed [1].",
            "citations": ["lodr_2015.pdf:30:1-2:0"],
            "grounded": True,
            "grounding_flags": [],
            "usage": {"input_tokens": 10, "output_tokens": 10},
        },
    )

    result = compiled_graph().invoke({"question": "When must a company disclose a material event?", "messages": []})

    assert result["route"] == "regulation"
    assert result["grounded"] is True
    assert result["citations"] == ["lodr_2015.pdf:30:1-2:0"]


def test_recent_route_end_to_end(monkeypatch):
    _patch_llm_client(monkeypatch, "Based on the recent circular... Based on search snippets; verify on sebi.gov.in.")
    monkeypatch.setattr(nodes, "DDGS", lambda: type("D", (), {"text": lambda self, *a, **k: [{"title": "t", "href": "https://sebi.gov.in/x", "body": "s"}]})())

    result = compiled_graph().invoke({"question": "What is the latest circular on this?", "messages": []})

    assert result["route"] == "recent"
    assert result["citations"] == ["https://sebi.gov.in/x"]


def test_out_of_scope_route_end_to_end(monkeypatch):
    monkeypatch.setattr(nodes, "retrieve_context", lambda q: [{"id": "c1", "rerank_score": -10.0}])
    monkeypatch.setattr(nodes, "REFUSE_THRESHOLD", 0.0)
    _patch_llm_client(monkeypatch, "out_of_scope")

    result = compiled_graph().invoke({"question": "What is the GST rate on mutual fund fees?", "messages": []})

    assert result["route"] == "out_of_scope"
    assert "LODR" in result["answer"]
