"""Tests for sebisage.generate.grounding, on hand-written answers covering each flag."""

from sebisage.generate.grounding import check_grounding

CONTEXT = [
    {"id": "lodr_2015.pdf:30:1-2:0", "text": "Every listed entity shall disclose material events under Regulation 30."},
    {"id": "lodr_2015.pdf:17:2:0", "text": "The board of directors shall meet at least four times a financial year under Regulation 17."},
]


def test_clean_answer_is_grounded():
    answer = (
        "A listed entity must disclose material events promptly [1]. "
        "The board must meet at least four times a year [2].\n"
        "Source: [1], [2]"
    )
    result = check_grounding(answer, CONTEXT)
    assert result.grounded is True
    assert result.flags == []


def test_insufficient_context_passthrough_is_grounded():
    result = check_grounding("INSUFFICIENT_CONTEXT", CONTEXT)
    assert result.grounded is True
    assert result.flags == []


def test_insufficient_context_with_stray_trailing_source_line_is_still_grounded():
    # Real observed model behavior: it sometimes appends "Source: None" anyway.
    result = check_grounding("INSUFFICIENT_CONTEXT\n\nSource: None", CONTEXT)
    assert result.grounded is True
    assert result.flags == []


def test_invalid_citation_flag():
    answer = "A listed entity must disclose material events promptly [5].\nSource: [5]"
    result = check_grounding(answer, CONTEXT)
    assert "invalid_citation" in result.flags
    assert result.details["invalid_citation_numbers"] == [5]
    assert result.grounded is False


def test_uncited_sentence_flag():
    answer = (
        "A listed entity must disclose material events promptly [1]. "
        "The board must meet regularly.\n"
        "Source: [1]"
    )
    result = check_grounding(answer, CONTEXT)
    assert "uncited_sentence" in result.flags
    assert result.details["uncited_sentences"] == ["The board must meet regularly."]
    assert result.grounded is False


def test_hallucinated_reference_flag():
    answer = "A listed entity must disclose material events under Regulation 45 [1].\nSource: [1]"
    result = check_grounding(answer, CONTEXT)
    assert "hallucinated_reference" in result.flags
    assert result.details["hallucinated_regs"] == ["45"]
    assert result.grounded is False


def test_multiple_flags_can_fire_together():
    answer = "Some unrelated claim about Regulation 99 with no citation at all."
    result = check_grounding(answer, CONTEXT)
    assert set(result.flags) == {"uncited_sentence", "hallucinated_reference"}
    assert result.grounded is False


def test_reg_mention_is_ok_if_present_in_cited_chunk():
    answer = "Material events must be disclosed under Regulation 30 [1].\nSource: [1]"
    result = check_grounding(answer, CONTEXT)
    assert "hallucinated_reference" not in result.flags
