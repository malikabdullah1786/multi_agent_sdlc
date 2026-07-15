"""
Reviewer Agent — Subgraph Definition

Flow:
  START → analyze_codebase → check_complexity → generate_review → submit_review → END
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.src.agents.reviewer.state import ReviewerState
from agents.src.agents.reviewer.nodes import (
    analyze_codebase_node,
    check_complexity_node,
    generate_review_node,
    submit_review_node
)

# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
workflow = StateGraph(ReviewerState)

workflow.add_node("analyze_codebase", analyze_codebase_node)
workflow.add_node("check_complexity", check_complexity_node)
workflow.add_node("generate_review", generate_review_node)
workflow.add_node("submit_review", submit_review_node)

workflow.add_edge(START, "analyze_codebase")
workflow.add_edge("analyze_codebase", "check_complexity")
workflow.add_edge("check_complexity", "generate_review")
workflow.add_edge("generate_review", "submit_review")
workflow.add_edge("submit_review", END)

reviewer_subgraph = workflow.compile(checkpointer=MemorySaver())
