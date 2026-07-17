"""
DevOps Agent — Subgraph Definition

Flow:
  START
    → generate_deployment_plan
    → validate_plan
    → [router: if invalid loop back]
    → approve_deployment (Human Interrupt Block)
    → [router: if rejected loop back]
    → execute_deployment
    → verify_health
  END
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.src.agents.devops.state import DevOpsState
from agents.src.agents.devops.nodes import (
    generate_deployment_plan_node,
    validate_plan_node,
    approve_deployment_node,
    execute_deployment_node,
    verify_health_node,
    pop_task_node,
    mark_task_complete_node
)

# ---------------------------------------------------------------------------
# Router: Is Queue Empty?
# ---------------------------------------------------------------------------
def _is_queue_empty(state: DevOpsState) -> str:
    return "END" if state.current_task is None else "generate_deployment_plan"

# ---------------------------------------------------------------------------
# Router: Validate IaC Configs
# ---------------------------------------------------------------------------
def _should_approve_plan(state: DevOpsState) -> str:
    """
    If the IaC linters found errors, loop back up to fix them autonomously
    before bothering the human.
    """
    max_iterations = 3
    if "VALIDATION_PASSED" not in state.iac_validation_notes and state.iteration_count < max_iterations:
        return "generate_deployment_plan"
    return "approve_deployment"

# ---------------------------------------------------------------------------
# Router: Human Approval
# ---------------------------------------------------------------------------
def _is_deployment_approved(state: DevOpsState) -> str:
    """
    If the human rejects the deployment plan, route back up to generate it again.
    """
    if state.deployment_approved:
        return "execute_deployment"
    return "generate_deployment_plan"

# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
workflow = StateGraph(DevOpsState)

# Register all nodes
workflow.add_node("pop_task", pop_task_node)
workflow.add_node("generate_deployment_plan", generate_deployment_plan_node)
workflow.add_node("validate_plan", validate_plan_node)
workflow.add_node("approve_deployment", approve_deployment_node)
workflow.add_node("execute_deployment", execute_deployment_node)
workflow.add_node("verify_health", verify_health_node)
workflow.add_node("mark_task_complete", mark_task_complete_node)

# Flow execution
workflow.add_edge(START, "pop_task")
workflow.add_conditional_edges("pop_task", _is_queue_empty, {"END": END, "generate_deployment_plan": "generate_deployment_plan"})
workflow.add_edge("generate_deployment_plan", "validate_plan")

# Autonomous IaC fixing loop
workflow.add_conditional_edges(
    "validate_plan",
    _should_approve_plan,
    {
        "generate_deployment_plan": "generate_deployment_plan",
        "approve_deployment": "approve_deployment"
    }
)

# Human approval blocking loop
workflow.add_conditional_edges(
    "approve_deployment",
    _is_deployment_approved,
    {
        "generate_deployment_plan": "generate_deployment_plan",
        "execute_deployment": "execute_deployment"
    }
)

# Execution phase
workflow.add_edge("execute_deployment", "verify_health")
workflow.add_edge("verify_health", "mark_task_complete")
workflow.add_edge("mark_task_complete", "pop_task")

devops_subgraph = workflow.compile(checkpointer=MemorySaver())
