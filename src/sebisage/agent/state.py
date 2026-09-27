"""LangGraph state definition."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


def _merge_timings(left: dict[str, float] | None, right: dict[str, float] | None) -> dict[str, float]:
    """Reducer for `timings`: each node returns only its own entry, so a plain
    replace (the TypedDict default) would drop every earlier node's timing."""
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    timings: Annotated[dict[str, float], _merge_timings]
    question: str
    standalone_question: str
    route: str
    route_reason: str
    retrieved: list[dict]
    web_results: list[dict]
    fetched_text: str | None
    fetched_url: str | None
    source_type: str
    answer: str
    citations: list[str]
    grounded: bool
    grounding_flags: list[str]
    usage_total: dict
    trace_id: str
