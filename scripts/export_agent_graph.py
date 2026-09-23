"""Phase 5.1: draws the agent graph with LangGraph's built-in Mermaid export.
Writes reports/figures/agent_graph.md.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sebisage.agent.graph import compiled_graph
from sebisage.config import FIGURES_DIR


def main() -> None:
    mermaid = compiled_graph().get_graph().draw_mermaid()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURES_DIR / "agent_graph.md"
    out_path.write_text(f"# SebiSage Agent Graph\n\n```mermaid\n{mermaid}```\n", encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
