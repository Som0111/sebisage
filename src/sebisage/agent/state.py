"""LangGraph state definition."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    question: str
    standalone_question: str
    route: str
    route_reason: str
    retrieved: list[dict]
    web_results: list[dict]
    answer: str
    citations: list[str]
    grounded: bool
    grounding_flags: list[str]
    usage_total: dict
    trace_id: str
