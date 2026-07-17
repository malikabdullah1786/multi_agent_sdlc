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

# ===========================================================================
# DISPATCHER LOOP & WRAPPERS
# ===========================================================================

def dispatcher_stage(state: WorkflowSate) -> dict:
    """
    Evaluates dependencies and priority, picks the next agent role to execute,
    and queues up their ready tasks.
    """
    all_tasks = state.workflow_tasks
    completed = set(state.completed_task_titles)
    
    # 1. Find all pending tasks whose dependencies are fully met
    ready_tasks = []
    for t in all_tasks:
        title = t.get("title", "")
        if title in completed:
            continue
            
        deps = t.get("dependencies", [])
        if all(dep in completed for dep in deps):
            ready_tasks.append(t)
            
    if not ready_tasks:
        # Either all tasks are done, or there's an unresolvable dependency cycle
        return {"active_role": "", "active_tasks": []}
        
    # 2. Tie-breaker precedence
    precedence = ["database_engineer", "devops", "backend", "frontend", "qa", "reviewer", "security"]
    def get_precedence(role: str) -> int:
        return precedence.index(role) if role in precedence else 99
        
    # 3. Sort by priority (1 is highest), then by precedence
    ready_tasks.sort(key=lambda x: (x.get("priority", 5), get_precedence(x.get("assignee_role", ""))))
    
    # 4. Pick the role of the most important ready task
    chosen_role = ready_tasks[0].get("assignee_role", "")
    
    # 5. Gather ALL ready tasks for that chosen role
    tasks_for_role = [t for t in ready_tasks if t.get("assignee_role", "") == chosen_role]
    
    return {"active_role": chosen_role, "active_tasks": tasks_for_role}

def _dispatcher_router(state: WorkflowSate) -> str:
    """Routes execution to the active agent."""
    role = state.active_role
    if not role:
        return END
        
    if role == "backend":
        return "backend_dev_stage"
    if role == "frontend":
        return "frontend_dev_stage"
        
    return f"{role}_stage"

# ---------------------------------------------------------------------------
# AGENT WRAPPER STAGES
# ---------------------------------------------------------------------------
def _execute_agent_subgraph(state: WorkflowSate, subgraph) -> dict:
    # Send only active_tasks to the sub-agent
    subgraph.invoke({
        "project_name": state.projectId,
        "prd": state.prd,
        "final_design_doc": state.final_design_doc,
        "source_code_paths": ["/backend", "/frontend"],
        "workflow_tasks": state.active_tasks
    }, config={"configurable": {"thread_id": state.workflowId}})
    
    # Mark tasks as completed
    new_completed = state.completed_task_titles.copy()
    for t in state.active_tasks:
        new_completed.append(t.get("title", ""))
        
    return {
        "completed_task_titles": new_completed,
        "active_role": "",
        "active_tasks": []
    }

def database_engineer_stage(state: WorkflowSate) -> dict:
    return _execute_agent_subgraph(state, database_engineer_subgraph)

def devops_stage(state: WorkflowSate) -> dict:
    return _execute_agent_subgraph(state, devops_subgraph)

def backend_dev_stage(state: WorkflowSate) -> dict:
    return _execute_agent_subgraph(state, backend_dev_subgraph)

def frontend_dev_stage(state: WorkflowSate) -> dict:
    return _execute_agent_subgraph(state, frontend_dev_subgraph)

def qa_stage(state: WorkflowSate) -> dict:
    return _execute_agent_subgraph(state, qa_subgraph)

def reviewer_stage(state: WorkflowSate) -> dict:
    return _execute_agent_subgraph(state, reviewer_subgraph)

def security_stage(state: WorkflowSate) -> dict:
    return _execute_agent_subgraph(state, security_subgraph)

# ===========================================================================
# PARENT GRAPH ASSEMBLY
# ===========================================================================

parent_workflow = StateGraph(WorkflowSate)

# Setup Phase Nodes
parent_workflow.add_node("planning_stage", planning_stage)
parent_workflow.add_node("pm_phase_a_stage", pm_phase_a_stage)
parent_workflow.add_node("architect_stage", architect_stage)
parent_workflow.add_node("task_breakdown_stage", task_breakdown_stage)
parent_workflow.add_node("pm_phase_b_stage", pm_phase_b_stage)

# Dispatcher Loop Nodes
parent_workflow.add_node("dispatcher_stage", dispatcher_stage)
parent_workflow.add_node("database_engineer_stage", database_engineer_stage)
parent_workflow.add_node("devops_stage", devops_stage)
parent_workflow.add_node("backend_dev_stage", backend_dev_stage)
parent_workflow.add_node("frontend_dev_stage", frontend_dev_stage)
parent_workflow.add_node("qa_stage", qa_stage)
parent_workflow.add_node("reviewer_stage", reviewer_stage)
parent_workflow.add_node("security_stage", security_stage)

# ── Linear Setup Phase ──────────────────────────────────────────────────
parent_workflow.add_edge(START, "planning_stage")
parent_workflow.add_edge("planning_stage", "pm_phase_a_stage")
parent_workflow.add_edge("pm_phase_a_stage", "architect_stage")
parent_workflow.add_edge("architect_stage", "task_breakdown_stage")
parent_workflow.add_edge("task_breakdown_stage", "pm_phase_b_stage")
parent_workflow.add_edge("pm_phase_b_stage", "dispatcher_stage")

# ── Dispatcher Routing ──────────────────────────────────────────────────
parent_workflow.add_conditional_edges(
    "dispatcher_stage",
    _dispatcher_router,
    {
        "database_engineer_stage": "database_engineer_stage",
        "devops_stage": "devops_stage",
        "backend_dev_stage": "backend_dev_stage",
        "frontend_dev_stage": "frontend_dev_stage",
        "qa_stage": "qa_stage",
        "reviewer_stage": "reviewer_stage",
        "security_stage": "security_stage",
        END: END
    }
)

# ── Loop Back to Dispatcher ─────────────────────────────────────────────
parent_workflow.add_edge("database_engineer_stage", "dispatcher_stage")
parent_workflow.add_edge("devops_stage", "dispatcher_stage")
parent_workflow.add_edge("backend_dev_stage", "dispatcher_stage")
parent_workflow.add_edge("frontend_dev_stage", "dispatcher_stage")
parent_workflow.add_edge("qa_stage", "dispatcher_stage")
parent_workflow.add_edge("reviewer_stage", "dispatcher_stage")
parent_workflow.add_edge("security_stage", "dispatcher_stage")

orchestration_graph = parent_workflow.compile()
