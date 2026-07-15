"""
Architect Agent — Subgraph Definition

Flow:
  START
    → research               (Tavily + RAG)
    → design_draft           (full system design document)
    → validate_design        (schema validator + API linter tools)
    → self_critique          (LLM self-evaluation)
    → [revision loop if issues remain]
    → approve_schema         (interrupt: user reviews DB schema section)
    → [revision loop if schema rejected]
    → approve_api            (interrupt: user reviews API endpoints section)
    → [revision loop if API rejected]
    → approve_structure      (interrupt: user reviews directory structure section)
    → [revision loop if structure rejected]
    → finalize_design
  END
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.src.agents.architect.state import ArchitectState
from agents.src.agents.architect.nodes import (
    research_node,
    design_draft_node,
    validate_design_node,
    self_critique_node,
    approve_schema_node,
    approve_api_node,
    approve_structure_node,
    finalize_design_node,
)


# ---------------------------------------------------------------------------
# Router: Should we revise based on critique / validation?
# ---------------------------------------------------------------------------

def _should_revise_after_critique(state: ArchitectState) -> str:
    """
    If the self-critique or validators found significant issues and we haven't
    exceeded 3 iterations, loop back to regenerate the draft.
    """
    max_iterations = 3
    has_issues = (
        state.self_critique_notes
        and "DESIGN_COMPLETE" not in state.self_critique_notes.upper()
        and (
            "SCHEMA_VALID" not in state.schema_validation_notes
            or "API_SPEC_VALID" not in state.api_validation_notes
            or True  # always check critique
        )
        and state.iteration_count < max_iterations
    )
    return "design_draft" if has_issues else "approve_schema"


# ---------------------------------------------------------------------------
# Router: Schema section approved?
# ---------------------------------------------------------------------------

def _schema_approved(state: ArchitectState) -> str:
    """
    If schema was rejected, loop back to redesign with feedback.
    If approved, proceed to API approval.
    """
    return "approve_api" if state.schema_approved else "design_draft"


# ---------------------------------------------------------------------------
# Router: API section approved?
# ---------------------------------------------------------------------------

def _api_approved(state: ArchitectState) -> str:
    """
    If API spec was rejected, loop back to redesign with feedback.
    If approved, proceed to structure approval.
    """
    return "approve_structure" if state.api_approved else "design_draft"


# ---------------------------------------------------------------------------
# Router: Structure section approved?
# ---------------------------------------------------------------------------

def _structure_approved(state: ArchitectState) -> str:
    """
    If directory structure was rejected, loop back to redesign.
    If approved, finalize the design.
    """
    return "finalize_design" if state.structure_approved else "design_draft"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

workflow = StateGraph(ArchitectState)

# Register all nodes
workflow.add_node("research", research_node)
workflow.add_node("design_draft", design_draft_node)
workflow.add_node("validate_design", validate_design_node)
workflow.add_node("self_critique", self_critique_node)
workflow.add_node("approve_schema", approve_schema_node)
workflow.add_node("approve_api", approve_api_node)
workflow.add_node("approve_structure", approve_structure_node)
workflow.add_node("finalize_design", finalize_design_node)

# Linear flow: research → draft → validate → critique
workflow.add_edge(START, "research")
workflow.add_edge("research", "design_draft")
workflow.add_edge("design_draft", "validate_design")
workflow.add_edge("validate_design", "self_critique")

# Revision loop after critique
workflow.add_conditional_edges(
    "self_critique",
    _should_revise_after_critique,
    {
        "design_draft": "design_draft",
        "approve_schema": "approve_schema",
    },
)

# Section-level approval gates (each can loop back to redesign)
workflow.add_conditional_edges(
    "approve_schema",
    _schema_approved,
    {
        "design_draft": "design_draft",
        "approve_api": "approve_api",
    },
)

workflow.add_conditional_edges(
    "approve_api",
    _api_approved,
    {
        "design_draft": "design_draft",
        "approve_structure": "approve_structure",
    },
)

workflow.add_conditional_edges(
    "approve_structure",
    _structure_approved,
    {
        "design_draft": "design_draft",
        "finalize_design": "finalize_design",
    },
)

workflow.add_edge("finalize_design", END)

architect_subgraph = workflow.compile(checkpointer=MemorySaver())
