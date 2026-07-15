"""
Frontend Developer Agent — Subgraph Definition

Flow:
  START
    → pop_task
    → [router: if empty, END]
    → fetch_api_schema
    → write_ui_code
    → lint_code
    → [router: loop if lint fails]
    → run_tests
    → [router: loop if tests fail]
    → browser_check
    → [router: loop if console errors]
    → mark_task_complete
    → pop_task (Loop back)
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.src.agents.frontend_dev.state import FrontendDevState
from agents.src.agents.frontend_dev.nodes import (
    pop_task_node,
    fetch_api_schema_node,
    write_ui_code_node,
    lint_code_node,
    run_tests_node,
    browser_check_node,
    mark_task_complete_node
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
def _is_queue_empty(state: FrontendDevState) -> str:
    return "END" if state.current_task is None else "fetch_api_schema"

def _did_linter_pass(state: FrontendDevState) -> str:
    max_iterations = 5
    if state.linter_errors and state.iteration_count < max_iterations:
        return "write_ui_code"
    return "run_tests"

def _did_tests_pass(state: FrontendDevState) -> str:
    max_iterations = 5
    if state.test_failures and state.iteration_count < max_iterations:
        return "write_ui_code"
    return "browser_check"

def _is_console_clean(state: FrontendDevState) -> str:
    max_iterations = 5
    if state.browser_console_errors and state.iteration_count < max_iterations:
        return "write_ui_code"
    return "mark_task_complete"

# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
workflow = StateGraph(FrontendDevState)

# Register nodes
workflow.add_node("pop_task", pop_task_node)
workflow.add_node("fetch_api_schema", fetch_api_schema_node)
workflow.add_node("write_ui_code", write_ui_code_node)
workflow.add_node("lint_code", lint_code_node)
workflow.add_node("run_tests", run_tests_node)
workflow.add_node("browser_check", browser_check_node)
workflow.add_node("mark_task_complete", mark_task_complete_node)

# Flow execution
workflow.add_edge(START, "pop_task")

workflow.add_conditional_edges(
    "pop_task",
    _is_queue_empty,
    {
        "END": END,
        "fetch_api_schema": "fetch_api_schema"
    }
)

workflow.add_edge("fetch_api_schema", "write_ui_code")
workflow.add_edge("write_ui_code", "lint_code")

workflow.add_conditional_edges(
    "lint_code",
    _did_linter_pass,
    {"write_ui_code": "write_ui_code", "run_tests": "run_tests"}
)

workflow.add_conditional_edges(
    "run_tests",
    _did_tests_pass,
    {"write_ui_code": "write_ui_code", "browser_check": "browser_check"}
)

workflow.add_conditional_edges(
    "browser_check",
    _is_console_clean,
    {"write_ui_code": "write_ui_code", "mark_task_complete": "mark_task_complete"}
)

workflow.add_edge("mark_task_complete", "pop_task")

frontend_dev_subgraph = workflow.compile(checkpointer=MemorySaver())
