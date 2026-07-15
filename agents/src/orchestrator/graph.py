from langgraph.graph import StateGraph, START, END
from agents.src.orchestrator.state import WorkflowSate

# Import all compiled subgraphs
from agents.src.agents.planning.graph import planning_subgraph
from agents.src.agents.product_manager.graph import pm_phase_a_subgraph, pm_phase_b_subgraph
from agents.src.agents.architect.graph import architect_subgraph
from agents.src.agents.task_breakdown.graph import task_breakdown_subgraph
from agents.src.agents.database_engineer.graph import database_engineer_subgraph
from agents.src.agents.backend_dev.graph import backend_dev_subgraph
from agents.src.agents.frontend_dev.graph import frontend_dev_subgraph
from agents.src.agents.qa.graph import qa_subgraph
from agents.src.agents.reviewer.graph import reviewer_subgraph
from agents.src.agents.security.graph import security_subgraph
from agents.src.agents.devops.graph import devops_subgraph

# ===========================================================================
# WRAPPER NODES (Passing state between subgraphs)
# ===========================================================================

def planning_stage(state: WorkflowSate) -> dict:
    # Planning uses user_req, outputs nothing to global (internal logic handles it)
    planning_subgraph.invoke({"user_req": state.user_req}, config={"configurable": {"thread_id": state.workflowId}})
    return {}

def pm_phase_a_stage(state: WorkflowSate) -> dict:
    # Phase A writes the PRD
    out = pm_phase_a_subgraph.invoke({"user_req": state.user_req}, config={"configurable": {"thread_id": state.workflowId}})
    return {"prd": out.get("prd", "")}

def architect_stage(state: WorkflowSate) -> dict:
    # Architect uses PRD to write Design Doc
    out = architect_subgraph.invoke({"user_req": state.prd}, config={"configurable": {"thread_id": state.workflowId}})
    return {"final_design_doc": out.get("final_design_doc", "")}

def task_breakdown_stage(state: WorkflowSate) -> dict:
    # Parses docs to create workflow_tasks
    out = task_breakdown_subgraph.invoke({
        "prd": state.prd,
        "final_design_doc": state.final_design_doc
    }, config={"configurable": {"thread_id": state.workflowId}})
    return {"workflow_tasks": out.get("workflow_tasks", [])}

def pm_phase_b_stage(state: WorkflowSate) -> dict:
    # Creates Jira tickets from workflow_tasks
    pm_phase_b_subgraph.invoke({"workflow_tasks": state.workflow_tasks}, config={"configurable": {"thread_id": state.workflowId}})
    return {}

def database_engineer_stage(state: WorkflowSate) -> dict:
    # Creates DB based on Architect's design
    database_engineer_subgraph.invoke({
        "project_name": state.projectId,
        "final_design_doc": state.final_design_doc
    }, config={"configurable": {"thread_id": state.workflowId}})
    return {}

# ---------------------------------------------------------------------------
# FAN-OUT / FAN-IN / TARGETED
# ---------------------------------------------------------------------------
def fan_out_node(state: WorkflowSate) -> dict:
    """Dummy node representing the start of parallel dev execution or targeted fix."""
    return {}

def backend_dev_stage(state: WorkflowSate) -> dict:
    out = backend_dev_subgraph.invoke({
        "final_design_doc": state.final_design_doc,
        "workflow_tasks": state.workflow_tasks
    }, config={"configurable": {"thread_id": state.workflowId}})
    # Append backend changes to final code array
    return {"final_file_changes": state.final_file_changes + out.get("backend_file_changes", [])}

def frontend_dev_stage(state: WorkflowSate) -> dict:
    out = frontend_dev_subgraph.invoke({
        "final_design_doc": state.final_design_doc,
        "workflow_tasks": state.workflow_tasks
    }, config={"configurable": {"thread_id": state.workflowId}})
    # Append frontend changes to final code array
    return {"final_file_changes": state.final_file_changes + out.get("frontend_file_changes", [])}

def fan_in_node(state: WorkflowSate) -> dict:
    """Dummy node where parallel execution converges before QA."""
    return {}

# ---------------------------------------------------------------------------
# GATES
# ---------------------------------------------------------------------------
def qa_stage(state: WorkflowSate) -> dict:
    out = qa_subgraph.invoke({
        "prd": state.prd, 
        "final_design_doc": state.final_design_doc
    }, config={"configurable": {"thread_id": state.workflowId}})
    return {"qa_passed": out.get("all_tests_passed", False)}

def reviewer_stage(state: WorkflowSate) -> dict:
    out = reviewer_subgraph.invoke({
        "backend_file_changes": state.final_file_changes,
        "frontend_file_changes": state.final_file_changes
    }, config={"configurable": {"thread_id": state.workflowId}})
    return {"reviewer_approved": out.get("code_review_approved", False)}

def security_stage(state: WorkflowSate) -> dict:
    out = security_subgraph.invoke({
        "backend_file_changes": state.final_file_changes,
        "frontend_file_changes": state.final_file_changes
    }, config={"configurable": {"thread_id": state.workflowId}})
    return {"security_approved": out.get("security_approved", False)}

def devops_stage(state: WorkflowSate) -> dict:
    devops_subgraph.invoke({
        "final_design_doc": state.final_design_doc,
        "source_code_paths": ["/backend", "/frontend"]
    }, config={"configurable": {"thread_id": state.workflowId}})
    return {}


# ===========================================================================
# ROUTERS
# ===========================================================================

def _fan_out_router(state: WorkflowSate) -> list:
    """Routes to parallel agents if initial build, otherwise to target agent."""
    if state.is_initial_build:
        return ["backend_dev_stage", "frontend_dev_stage"]
    
    if state.target_agent == "backend":
        return ["backend_dev_stage"]
    elif state.target_agent == "frontend":
        return ["frontend_dev_stage"]
    else:
        # Fallback to backend
        return ["backend_dev_stage"]

def _qa_router(state: WorkflowSate) -> str:
    """If QA fails, bounce back to fan-out to fix bugs."""
    if state.qa_passed:
        return "reviewer_stage"
    return "fan_out_node"

def _reviewer_router(state: WorkflowSate) -> str:
    """If Reviewer rejects, bounce back to fan-out to fix code smells."""
    if state.reviewer_approved:
        return "security_stage"
    return "fan_out_node"

def _security_router(state: WorkflowSate) -> str:
    """If Security rejects, bounce back to fan-out to fix vulnerabilities."""
    if state.security_approved:
        return "devops_stage"
    return "fan_out_node"


# ===========================================================================
# PARENT GRAPH ASSEMBLY
# ===========================================================================

parent_workflow = StateGraph(WorkflowSate)

# Add nodes
parent_workflow.add_node("planning_stage", planning_stage)
parent_workflow.add_node("pm_phase_a_stage", pm_phase_a_stage)
parent_workflow.add_node("architect_stage", architect_stage)
parent_workflow.add_node("task_breakdown_stage", task_breakdown_stage)
parent_workflow.add_node("pm_phase_b_stage", pm_phase_b_stage)
parent_workflow.add_node("database_engineer_stage", database_engineer_stage)

parent_workflow.add_node("fan_out_node", fan_out_node)
parent_workflow.add_node("backend_dev_stage", backend_dev_stage)
parent_workflow.add_node("frontend_dev_stage", frontend_dev_stage)
parent_workflow.add_node("fan_in_node", fan_in_node)

parent_workflow.add_node("qa_stage", qa_stage)
parent_workflow.add_node("reviewer_stage", reviewer_stage)
parent_workflow.add_node("security_stage", security_stage)
parent_workflow.add_node("devops_stage", devops_stage)

# ── Linear Setup Phase ──────────────────────────────────────────────────
parent_workflow.add_edge(START, "planning_stage")
parent_workflow.add_edge("planning_stage", "pm_phase_a_stage")
parent_workflow.add_edge("pm_phase_a_stage", "architect_stage")
parent_workflow.add_edge("architect_stage", "task_breakdown_stage")
parent_workflow.add_edge("task_breakdown_stage", "pm_phase_b_stage")
parent_workflow.add_edge("pm_phase_b_stage", "database_engineer_stage")
parent_workflow.add_edge("database_engineer_stage", "fan_out_node")

# ── Parallel Fan-Out Execution ──────────────────────────────────────────
parent_workflow.add_conditional_edges(
    "fan_out_node",
    _fan_out_router,
    ["backend_dev_stage", "frontend_dev_stage"]
)

# ── Fan-In Convergence ──────────────────────────────────────────────────
parent_workflow.add_edge("backend_dev_stage", "fan_in_node")
parent_workflow.add_edge("frontend_dev_stage", "fan_in_node")
parent_workflow.add_edge("fan_in_node", "qa_stage")

# ── Quality Gates with Self-Healing Feedback Loops ──────────────────────
parent_workflow.add_conditional_edges(
    "qa_stage",
    _qa_router,
    {"reviewer_stage": "reviewer_stage", "fan_out_node": "fan_out_node"}
)

parent_workflow.add_conditional_edges(
    "reviewer_stage",
    _reviewer_router,
    {"security_stage": "security_stage", "fan_out_node": "fan_out_node"}
)

parent_workflow.add_conditional_edges(
    "security_stage",
    _security_router,
    {"devops_stage": "devops_stage", "fan_out_node": "fan_out_node"}
)

parent_workflow.add_edge("devops_stage", END)

orchestration_graph = parent_workflow.compile()
