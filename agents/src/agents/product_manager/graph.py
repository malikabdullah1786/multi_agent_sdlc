"""
Product Manager Agent — Subgraph Definition

SPLIT INTO TWO GRAPHS:

PHASE A: PRD Writing
  START → research → write_prd → user_approval → [revision loop] → finalize_prd → END

PHASE B: Jira + Slack
  START → create_slack_channel → create_jira_epic → create_jira_tickets → notify_slack → END
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.src.agents.product_manager.state import ProductManagerState
from agents.src.agents.product_manager.nodes import (
    # Phase A
    research_node,
    write_prd_node,
    user_approval_node,
    finalize_prd_node,
    # Phase B
    create_slack_channel_node,
    create_jira_epic_node,
    create_jira_tickets_node,
    notify_slack_node,
)

# ===========================================================================
# PHASE A GRAPH (PRD Writing)
# ===========================================================================

def _should_revise_prd(state: ProductManagerState) -> str:
    """If user rejected the PRD draft, loop back to rewrite it."""
    return "finalize_prd" if state.is_approved else "write_prd"

phase_a = StateGraph(ProductManagerState)

phase_a.add_node("research", research_node)
phase_a.add_node("write_prd", write_prd_node)
phase_a.add_node("user_approval", user_approval_node)
phase_a.add_node("finalize_prd", finalize_prd_node)

phase_a.add_edge(START, "research")
phase_a.add_edge("research", "write_prd")
phase_a.add_edge("write_prd", "user_approval")

phase_a.add_conditional_edges(
    "user_approval",
    _should_revise_prd,
    {
        "write_prd": "write_prd",
        "finalize_prd": "finalize_prd",
    },
)

phase_a.add_edge("finalize_prd", END)
pm_phase_a_subgraph = phase_a.compile(checkpointer=MemorySaver())


# ===========================================================================
# PHASE B GRAPH (Jira + Slack)
# ===========================================================================

phase_b = StateGraph(ProductManagerState)

phase_b.add_node("create_slack_channel", create_slack_channel_node)
phase_b.add_node("create_jira_epic", create_jira_epic_node)
phase_b.add_node("create_jira_tickets", create_jira_tickets_node)
phase_b.add_node("notify_slack", notify_slack_node)

phase_b.add_edge(START, "create_slack_channel")
phase_b.add_edge("create_slack_channel", "create_jira_epic")
phase_b.add_edge("create_jira_epic", "create_jira_tickets")
phase_b.add_edge("create_jira_tickets", "notify_slack")
phase_b.add_edge("notify_slack", END)

pm_phase_b_subgraph = phase_b.compile(checkpointer=MemorySaver())
