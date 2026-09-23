"""Agent graph wiring.

START -> rewrite_followup -> router -+- "regulation"    -> rag -> grounding_check -> END
                                      +- "recent"        -> web_search -> answer_from_web -> END
                                      +- "out_of_scope"  -> refuse -> END
"""

from langgraph.graph import END, START, StateGraph

from sebisage.agent import nodes
from sebisage.agent.state import AgentState


def _route_decision(state: AgentState) -> str:
    return state["route"]


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("rewrite_followup", nodes.rewrite_followup)
    graph.add_node("router", nodes.router)
    graph.add_node("rag", nodes.rag)
    graph.add_node("grounding_check", nodes.grounding_check)
    graph.add_node("web_search", nodes.web_search)
    graph.add_node("answer_from_web", nodes.answer_from_web)
    graph.add_node("refuse", nodes.refuse)

    graph.add_edge(START, "rewrite_followup")
    graph.add_edge("rewrite_followup", "router")
    graph.add_conditional_edges(
        "router",
        _route_decision,
        {"regulation": "rag", "recent": "web_search", "out_of_scope": "refuse"},
    )
    graph.add_edge("rag", "grounding_check")
    graph.add_edge("grounding_check", END)
    graph.add_edge("web_search", "answer_from_web")
    graph.add_edge("answer_from_web", END)
    graph.add_edge("refuse", END)

    return graph


def compiled_graph():
    return build_graph().compile()
