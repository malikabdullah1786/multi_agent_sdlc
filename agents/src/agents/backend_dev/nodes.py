"""
Backend Developer Agent — Node Functions

Flow:
  pop_task → write_code → lint_code → run_tests → mark_task_complete → pop_task
  (loops write_code if lint_code or run_tests fail)
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agents.src.agents.backend_dev.state import BackendDevState
from agents.src.agents.backend_dev.tools import (
    code_linter,
    run_unit_tests,
    semantic_code_search,
    db_schema_inspector
)

_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

# ---------------------------------------------------------------------------
# 1. Pop Task Node
# ---------------------------------------------------------------------------
def pop_task_node(state: BackendDevState) -> dict:
    """
    Pulls the next uncompleted task from the queue.
    """
    tasks = list(state.workflow_tasks)
    
    if not tasks:
        # Queue is empty
        return {"current_task": None}
        
    next_task = tasks.pop(0)
    
    return {
        "workflow_tasks": tasks,
        "current_task": next_task,
        "linter_errors": "",
        "test_failures": "",
        "iteration_count": 0
    }

# ---------------------------------------------------------------------------
# 2. Write Code Node
# ---------------------------------------------------------------------------
def write_code_node(state: BackendDevState) -> dict:
    """
    Writes the application code and the unit tests for the current task.
    """
    prompt = PromptTemplate.from_template(
        """You are an elite Backend Developer.
        Write the code to complete the current task. Also write the unit tests for it.
        
        System Design Doc:
        {design}
        
        Current Task:
        {task}
        
        Previous Linter Errors: {linter}
        Previous Test Failures: {tests}
        
        Generate the complete raw file contents to fix any errors or implement the task.
        """
    )
    
    formatted = prompt.format(
        design=state.final_design_doc,
        task=str(state.current_task),
        linter=state.linter_errors or "None.",
        tests=state.test_failures or "None."
    )
    
    response = _llm.invoke(formatted)
    
    return {
        "current_code_draft": response.content,
        "iteration_count": state.iteration_count + 1
    }

# ---------------------------------------------------------------------------
# 3. Lint Code Node
# ---------------------------------------------------------------------------
def lint_code_node(state: BackendDevState) -> dict:
    """
    Runs the syntax linter against the generated code.
    """
    # Assuming code is written to a temp file via MCP
    result = code_linter.invoke({"file_path": "backend/src/temp.py"})
    return {"linter_errors": "" if result == "LINT_PASSED" else result}

# ---------------------------------------------------------------------------
# 4. Run Tests Node
# ---------------------------------------------------------------------------
def run_tests_node(state: BackendDevState) -> dict:
    """
    Runs the unit tests against the generated code.
    """
    result = run_unit_tests.invoke({"test_file_path": "backend/tests/test_temp.py"})
    return {"test_failures": "" if result == "TESTS_PASSED" else result}

# ---------------------------------------------------------------------------
# 5. Mark Task Complete Node
# ---------------------------------------------------------------------------
def mark_task_complete_node(state: BackendDevState) -> dict:
    """
    If tests pass, the task is marked as completed and added to the done pile.
    """
    completed = list(state.completed_tasks)
    if state.current_task:
        completed.append(state.current_task)
        
    return {
        "completed_tasks": completed,
        "current_task": None
    }
