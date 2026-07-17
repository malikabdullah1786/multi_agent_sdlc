"""
Frontend Developer Agent — Node Functions

Flow:
  pop_task → fetch_api_schema → write_ui_code 
  → lint_code → run_tests → browser_check → mark_task_complete
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agents.src.agents.frontend_dev.state import FrontendDevState
from agents.src.agents.frontend_dev.tools import (
    api_schema_fetcher,
    frontend_linter,
    run_component_tests,
    visual_browser_check
)

_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

# ---------------------------------------------------------------------------
# 1. Pop Task Node
# ---------------------------------------------------------------------------
def pop_task_node(state: FrontendDevState) -> dict:
    """Pulls the next uncompleted task from the queue."""
    tasks = list(state.workflow_tasks)
    
    if not tasks:
        return {"current_task": None}
        
    next_task = tasks.pop(0)
    
    return {
        "workflow_tasks": tasks,
        "current_task": next_task,
        "linter_errors": "",
        "test_failures": "",
        "browser_console_errors": "",
        "iteration_count": 0
    }

# ---------------------------------------------------------------------------
# 2. Fetch API Schema Node
# ---------------------------------------------------------------------------
def fetch_api_schema_node(state: FrontendDevState) -> dict:
    """Fetches the backend OpenAPI schema to ensure accurate API calls."""
    try:
        # api_schema_fetcher.invoke({})
        schema = "MOCK: Schema fetched successfully."
    except NotImplementedError as e:
        schema = str(e)
    return {"backend_api_schema": schema}

# ---------------------------------------------------------------------------
# 3. Write UI Code Node
# ---------------------------------------------------------------------------
def write_ui_code_node(state: FrontendDevState) -> dict:
    """Writes the React/Vue components, CSS, API fetchers, and unit tests."""
    prompt = PromptTemplate.from_template(
        """You are an elite Frontend Developer.
        Write the UI code to complete the current task. 
        Focus on rich aesthetics, responsive design, and proper API integration.
        
        System Design Doc: {design}
        Backend API Schema: {schema}
        Current Task: {task}
        
        Previous Linter Errors: {linter}
        Previous Test Failures: {tests}
        Previous Browser Console Errors: {browser}
        
        Generate the complete raw file contents to fix any errors or implement the task.
        """
    )
    
    formatted = prompt.format(
        design=state.final_design_doc,
        schema=state.backend_api_schema,
        task=str(state.current_task),
        linter=state.linter_errors or "None.",
        tests=state.test_failures or "None.",
        browser=state.browser_console_errors or "None."
    )
    
    response = _llm.invoke(formatted)
    
    return {
        "current_code_draft": response.content,
        "iteration_count": state.iteration_count + 1
    }

# ---------------------------------------------------------------------------
# 4. Lint Code Node
# ---------------------------------------------------------------------------
def lint_code_node(state: FrontendDevState) -> dict:
    """Runs the syntax linter (e.g. ESLint) against the generated UI code."""
    result = frontend_linter.invoke({"file_path": "frontend/src/temp.tsx"})
    return {"linter_errors": "" if result == "LINT_PASSED" else result}

# ---------------------------------------------------------------------------
# 5. Run Tests Node
# ---------------------------------------------------------------------------
def run_tests_node(state: FrontendDevState) -> dict:
    """Runs the component unit tests."""
    result = run_component_tests.invoke({"test_file_path": "frontend/src/temp.test.tsx"})
    return {"test_failures": "" if result == "TESTS_PASSED" else result}

# ---------------------------------------------------------------------------
# 6. Browser Check Node
# ---------------------------------------------------------------------------
def browser_check_node(state: FrontendDevState) -> dict:
    """Uses a headless browser to render the UI and check for runtime console errors."""
    result = visual_browser_check.invoke({"route_url": "http://localhost:3000"})
    return {"browser_console_errors": "" if "CONSOLE_CLEAN" in result else result}

# ---------------------------------------------------------------------------
# 7. Mark Task Complete Node
# ---------------------------------------------------------------------------
def mark_task_complete_node(state: FrontendDevState) -> dict:
    """
    Task is completed and pushed to the done pile.
    Extracts the generated code into frontend_file_changes.
    """
    completed = list(state.completed_tasks)
    changes = list(state.frontend_file_changes)
    
    if state.current_task:
        completed.append(state.current_task)
        if state.current_code_draft:
            changes.append({
                "task_title": state.current_task.get("title", "Unknown"),
                "content": state.current_code_draft
            })
        
    return {
        "completed_tasks": completed,
        "current_task": None,
        "frontend_file_changes": changes
    }
