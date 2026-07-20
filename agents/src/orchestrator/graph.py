from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt
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
# SUBGRAPH EXECUTOR WITH INTERRUPT BUBBLING
# ===========================================================================

from langgraph.errors import GraphInterrupt

def _run_subgraph_with_interrupts(subgraph, initial_input, config):
    # Determine if subgraph is currently paused
    sub_state = subgraph.get_state(config)
    has_sub_interrupts = any(task.interrupts for task in sub_state.tasks) if sub_state.tasks else False
    if sub_state.next or has_sub_interrupts:
        # Subgraph is paused. Call interrupt to consume the parent's resume value.
        user_response = interrupt("Awaiting approval")
        # Resume the subgraph
        out = subgraph.invoke(Command(resume=user_response), config=config)
    else:
        # Subgraph is not started. Invoke it fresh.
        out = subgraph.invoke(initial_input, config=config)

    # Check if the subgraph has paused on a new interrupt
    sub_state_after = subgraph.get_state(config)
    sub_interrupts_after = []
    if sub_state_after.tasks:
        for task in sub_state_after.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                sub_interrupts_after.extend(task.interrupts)

    if sub_state_after.next or sub_interrupts_after:
        payload = sub_interrupts_after[0].value if sub_interrupts_after else "Awaiting approval"
        # Pause the parent graph by raising an interrupt with the same payload
        interrupt(payload)

    return out

# ===========================================================================
# WRAPPER NODES (Passing state between subgraphs)
# ===========================================================================

def planning_stage(state: WorkflowSate) -> dict:
    _run_subgraph_with_interrupts(
        planning_subgraph,
        {"user_req": state.user_req},
        {"configurable": {"thread_id": f"{state.workflowId}-planning"}}
    )
    return {}

def pm_phase_a_stage(state: WorkflowSate) -> dict:
    out = _run_subgraph_with_interrupts(
        pm_phase_a_subgraph,
        {"user_req": state.user_req},
        {"configurable": {"thread_id": f"{state.workflowId}-pm_a"}}
    )
    return {
        "prd": out.get("prd", ""),
        "project_name": out.get("project_name", "")
    }

def architect_stage(state: WorkflowSate) -> dict:
    out = _run_subgraph_with_interrupts(
        architect_subgraph,
        {
            "user_req": state.prd,
            "prd": state.prd,
            "project_name": state.project_name
        },
        {"configurable": {"thread_id": f"{state.workflowId}-architect"}}
    )
    return {
        "final_design_doc": out.get("final_design_doc", "")
    }

def task_breakdown_stage(state: WorkflowSate) -> dict:
    out = _run_subgraph_with_interrupts(
        task_breakdown_subgraph,
        {
            "prd": state.prd,
            "final_design_doc": state.final_design_doc,
            "project_name": state.project_name
        },
        {"configurable": {"thread_id": f"{state.workflowId}-task_breakdown"}}
    )
    return {
        "workflow_tasks": out.get("workflow_tasks", []),
        "active_tasks": out.get("workflow_tasks", []),
        "completed_task_titles": []
    }

def pm_phase_b_stage(state: WorkflowSate) -> dict:
    _run_subgraph_with_interrupts(
        pm_phase_b_subgraph,
        {
            "workflow_tasks": state.workflow_tasks,
            "user_req": state.user_req,
            "prd": state.prd,
            "project_name": state.project_name
        },
        {"configurable": {"thread_id": state.workflowId}}
    )
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
    out = _run_subgraph_with_interrupts(
        subgraph,
        {
            "project_name": state.project_name if state.project_name else state.projectId,
            "prd": state.prd,
            "final_design_doc": state.final_design_doc,
            "source_code_paths": ["/backend", "/frontend"],
            "workflow_tasks": state.active_tasks,
            "active_pr_number": state.active_pr_number
        },
        {"configurable": {"thread_id": state.workflowId}}
    )
    
    new_completed = state.completed_task_titles.copy()
    new_global_tasks = state.workflow_tasks.copy()
    active_pr_number = state.active_pr_number
    
    # Check if the agent rejected the work (e.g. reviewer failed)
    # If the sub-agent outputs `code_review_approved: False` or `all_tests_passed: False`, we don't complete the task
    is_rejected = False
    if "code_review_approved" in out and not out["code_review_approved"]:
        is_rejected = True
    if "all_tests_passed" in out and not out["all_tests_passed"]:
        is_rejected = True
    if "security_approved" in out and not out["security_approved"]:
        is_rejected = True
        
    if not is_rejected:
        # Mark tasks as completed
        for t in state.active_tasks:
            new_completed.append(t.get("title", ""))
            
    # Pull any newly spawned tasks (e.g., bug fixes, PR revisions)
    if "new_workflow_tasks" in out and out["new_workflow_tasks"]:
        new_global_tasks.extend(out["new_workflow_tasks"])
        
    # Capture PR number if Developer agents created one
    if "active_pr_number" in out and out["active_pr_number"]:
        active_pr_number = out["active_pr_number"]
        
    return {
        "completed_task_titles": new_completed,
        "workflow_tasks": new_global_tasks,
        "active_role": "",
        "active_tasks": [],
        "active_pr_number": active_pr_number
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

from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
orchestration_graph = parent_workflow.compile(checkpointer=checkpointer)
