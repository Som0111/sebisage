"""Tests for sebisage.generate.answer: the retrieve -> prompt -> llm -> parse chain."""

from sebisage.generate import answer as answer_module
from sebisage.generate.llm import LLMResult

CONTEXT = [
    {"id": "lodr_2015.pdf:30:1-2:0", "text": "Every listed entity shall disclose material events under Regulation 30."},
    {"id": "lodr_2015.pdf:17:2:0", "text": "The board of directors shall meet at least four times a year under Regulation 17."},
]

GROUNDED_ANSWER = "A listed entity must disclose material events promptly [1].\nSource: [1]"
UNGROUNDED_ANSWER = "A listed entity must disclose material events under Regulation 99.\nSource:"


class FakeLLMClient:
    def __init__(self, responses: list[LLMResult]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def invoke(self, messages, prompt_version="v1"):
        self.calls.append({"messages": messages, "prompt_version": prompt_version})
        return self._responses.pop(0)


def _result(text: str, error: str | None = None) -> LLMResult:
    return LLMResult(text=text, input_tokens=10, output_tokens=5, cached=False, error=error)


def test_happy_path_no_retry_needed(monkeypatch):
    monkeypatch.setattr(answer_module, "retrieve_context", lambda q, k_final: CONTEXT)
    client = FakeLLMClient([_result(GROUNDED_ANSWER)])

    out = answer_module.answer("When must a company disclose a material event?", llm_client=client)

    assert len(client.calls) == 1
    assert out["grounded"] is True
    assert out["citations"] == ["lodr_2015.pdf:30:1-2:0"]
    assert out["usage"] == {"input_tokens": 10, "output_tokens": 5}
    assert out["answer"] == GROUNDED_ANSWER


def test_ungrounded_first_response_triggers_one_retry_that_succeeds(monkeypatch):
    monkeypatch.setattr(answer_module, "retrieve_context", lambda q, k_final: CONTEXT)
    client = FakeLLMClient([_result(UNGROUNDED_ANSWER), _result(GROUNDED_ANSWER)])

    out = answer_module.answer("question", llm_client=client)

    assert len(client.calls) == 2
    assert out["grounded"] is True
    assert out["answer"] == GROUNDED_ANSWER
    assert out["usage"] == {"input_tokens": 20, "output_tokens": 10}  # summed across both calls
    # retry prompt should reference what went wrong
    assert "not fully grounded" in client.calls[1]["messages"][0]["content"]


def test_still_ungrounded_after_retry_returns_grounded_false(monkeypatch):
    monkeypatch.setattr(answer_module, "retrieve_context", lambda q, k_final: CONTEXT)
    client = FakeLLMClient([_result(UNGROUNDED_ANSWER), _result(UNGROUNDED_ANSWER)])

    out = answer_module.answer("question", llm_client=client)

    assert len(client.calls) == 2
    assert out["grounded"] is False
    assert "hallucinated_reference" in out["grounding_flags"]


def test_llm_error_returns_error_object_not_crash(monkeypatch):
    monkeypatch.setattr(answer_module, "retrieve_context", lambda q, k_final: CONTEXT)
    client = FakeLLMClient([_result("", error="quota_exceeded")])

    out = answer_module.answer("question", llm_client=client)

    assert out["answer"] is None
    assert out["error"] == "quota_exceeded"
    assert len(client.calls) == 1


def test_insufficient_context_has_no_citations(monkeypatch):
    monkeypatch.setattr(answer_module, "retrieve_context", lambda q, k_final: CONTEXT)
    client = FakeLLMClient([_result("INSUFFICIENT_CONTEXT")])

    out = answer_module.answer("question", llm_client=client)

    assert out["citations"] == []
    assert out["grounded"] is True


def test_insufficient_context_with_stray_source_line_does_not_trigger_retry(monkeypatch):
    # Real observed model behavior: it sometimes appends "Source: None" anyway;
    # this must not be treated as an ungrounded answer needing a retry.
    monkeypatch.setattr(answer_module, "retrieve_context", lambda q, k_final: CONTEXT)
    client = FakeLLMClient([_result("INSUFFICIENT_CONTEXT\n\nSource: None")])

    out = answer_module.answer("question", llm_client=client)

    assert len(client.calls) == 1
    assert out["citations"] == []
    assert out["grounded"] is True


def test_format_context_numbers_chunks_in_order():
    context = answer_module._format_context(CONTEXT)
    assert context.startswith("[1] Every listed entity")
    assert "[2] The board of directors" in context
