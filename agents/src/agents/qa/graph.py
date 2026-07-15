"""
QA Agent — Subgraph Definition

Flow:
  START
    → generate_test_scripts
    → execute_tests
    → analyze_results
    → [router: if bugs found] → file_bug_reports → END
    → [router: if no bugs] → mark_qa_complete → END
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.src.agents.qa.state import QAState
from agents.src.agents.qa.nodes import (
    generate_test_scripts_node,
    execute_tests_node,
    analyze_results_node,
    file_bug_reports_node,
    mark_qa_complete_node
)

# ---------------------------------------------------------------------------
# Router: Were Bugs Found?
# ---------------------------------------------------------------------------
def _were_bugs_found(state: QAState) -> str:
    """
    If bugs were discovered during analysis, route to file bug reports.
    Otherwise, mark QA complete.
    """
    if state.discovered_bugs and len(state.discovered_bugs) > 0:
        return "file_bug_reports"
    return "mark_qa_complete"

# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
workflow = StateGraph(QAState)

# Register nodes
workflow.add_node("generate_test_scripts", generate_test_scripts_node)
workflow.add_node("execute_tests", execute_tests_node)
workflow.add_node("analyze_results", analyze_results_node)
workflow.add_node("file_bug_reports", file_bug_reports_node)
workflow.add_node("mark_qa_complete", mark_qa_complete_node)

# Flow execution
workflow.add_edge(START, "generate_test_scripts")
workflow.add_edge("generate_test_scripts", "execute_tests")
workflow.add_edge("execute_tests", "analyze_results")

# Routing based on bug analysis
workflow.add_conditional_edges(
    "analyze_results",
    _were_bugs_found,
    {
        "file_bug_reports": "file_bug_reports",
        "mark_qa_complete": "mark_qa_complete"
    }
)

# Terminal edges (Halts the QA agent and returns control to Orchestrator)
workflow.add_edge("file_bug_reports", END)
workflow.add_edge("mark_qa_complete", END)

qa_subgraph = workflow.compile(checkpointer=MemorySaver())
