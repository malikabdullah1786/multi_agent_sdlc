"""
Planning Agent — Subgraph Definition

Flow:
  START
    → research          (web search + RAG)
    → clarification     (interrupt if ambiguous questions exist)
    → generate_draft    (full feasibility brief + JSON block)
    → critique          (self-evaluation loop)
    → [revision check]  → generate_draft again if critique found issues
    → user_approval     (interrupt: user reviews and approves or gives feedback)
    → [approval check]  → generate_draft again if user rejected
    → finalize          (parse structured JSON, write final outputs)
  END
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.src.agents.planning.state import PlanningState
from agents.src.agents.planning.nodes import (
    research_node,
    clarification_node,
    generate_draft_node,
    critique_node,
    user_approval_node,
    finalize_node,
)

# ---------------------------------------------------------------------------
# Router: Should we revise the draft based on critique?
# ---------------------------------------------------------------------------

def _should_revise_after_critique(state: PlanningState) -> str:
    """
    If the critique found issues and we haven't exceeded 3 iterations,
    loop back to generate another draft. Otherwise proceed to user approval.
    """
    max_iterations = 3
    has_issues = (
        state.critique_notes
        and "NO_ISSUES_FOUND" not in state.critique_notes.upper()
        and state.iteration_count < max_iterations
    )
    return "generate_draft" if has_issues else "user_approval"


# ---------------------------------------------------------------------------
# Router: Did the user approve the draft?
# ---------------------------------------------------------------------------

def _should_revise_after_feedback(state: PlanningState) -> str:
    """
    If the user provided feedback (rejected the draft), loop back to regenerate.
    If the user approved, proceed to finalize.
    """
    return "finalize" if state.is_approved else "generate_draft"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

workflow = StateGraph(PlanningState)

# Register nodes
workflow.add_node("research", research_node)
workflow.add_node("clarification", clarification_node)
workflow.add_node("generate_draft", generate_draft_node)
workflow.add_node("critique", critique_node)
workflow.add_node("user_approval", user_approval_node)
workflow.add_node("finalize", finalize_node)

# Edges: Linear flow up to the branching points
workflow.add_edge(START, "research")
workflow.add_edge("research", "clarification")
workflow.add_edge("clarification", "generate_draft")
workflow.add_edge("generate_draft", "critique")

# Branch: Revision loop after critique
workflow.add_conditional_edges(
    "critique",
    _should_revise_after_critique,
    {
        "generate_draft": "generate_draft",
        "user_approval": "user_approval",
    },
)

# Branch: Revision loop after user feedback
workflow.add_conditional_edges(
    "user_approval",
    _should_revise_after_feedback,
    {
        "generate_draft": "generate_draft",
        "finalize": "finalize",
    },
)

workflow.add_edge("finalize", END)

# Compile with in-memory checkpointer (parent graph will inject Postgres checkpointer)
planning_subgraph = workflow.compile(checkpointer=MemorySaver())
