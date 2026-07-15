"""
Backend Developer Agent — Subgraph Definition

Flow:
  START
    → pop_task
    → [router: if queue empty, END]
    → write_code
    → lint_code
    → [router: if lint fails, loop back to write_code]
    → run_tests
    → [router: if tests fail, loop back to write_code]
    → mark_task_complete
    → pop_task (Loop back to start)
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.src.agents.backend_dev.state import BackendDevState
from agents.src.agents.backend_dev.nodes import (
    pop_task_node,
    write_code_node,
    lint_code_node,
    run_tests_node,
    mark_task_complete_node
)

# ---------------------------------------------------------------------------
# Router: Is Queue Empty?
# ---------------------------------------------------------------------------
def _is_queue_empty(state: BackendDevState) -> str:
    """If there is no current task after popping, we are done."""
    return "END" if state.current_task is None else "write_code"

# ---------------------------------------------------------------------------
# Router: Did Linter Pass?
# ---------------------------------------------------------------------------
def _did_linter_pass(state: BackendDevState) -> str:
    """If there are linter errors, loop back to write_code."""
    max_iterations = 5
    if state.linter_errors and state.iteration_count < max_iterations:
        return "write_code"
    return "run_tests"

# ---------------------------------------------------------------------------
# Router: Did Tests Pass?
# ---------------------------------------------------------------------------
def _did_tests_pass(state: BackendDevState) -> str:
    """If there are test failures, loop back to write_code."""
    max_iterations = 5
    if state.test_failures and state.iteration_count < max_iterations:
        return "write_code"
    return "mark_task_complete"

# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
workflow = StateGraph(BackendDevState)

# Register all nodes
workflow.add_node("pop_task", pop_task_node)
workflow.add_node("write_code", write_code_node)
workflow.add_node("lint_code", lint_code_node)
workflow.add_node("run_tests", run_tests_node)
workflow.add_node("mark_task_complete", mark_task_complete_node)

# Flow execution
workflow.add_edge(START, "pop_task")

# Routing based on queue state
workflow.add_conditional_edges(
    "pop_task",
    _is_queue_empty,
    {
        "END": END,
        "write_code": "write_code"
    }
)

workflow.add_edge("write_code", "lint_code")

# Routing based on linter results
workflow.add_conditional_edges(
    "lint_code",
    _did_linter_pass,
    {
        "write_code": "write_code",
        "run_tests": "run_tests"
    }
)

# Routing based on test results
workflow.add_conditional_edges(
    "run_tests",
    _did_tests_pass,
    {
        "write_code": "write_code",
        "mark_task_complete": "mark_task_complete"
    }
)

# Loop back to get the next task
workflow.add_edge("mark_task_complete", "pop_task")

backend_dev_subgraph = workflow.compile(checkpointer=MemorySaver())
