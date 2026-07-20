"""
QA Agent — Node Functions

Flow:
  pop_task → generate_test_scripts → execute_tests → analyze_results → mark_task_complete → pop_task
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import Dict, Any, List

from agents.src.agents.qa.state import QAState
from agents.src.agents.qa.tools import (
    run_test_suite,
    generate_bug_report,
)

_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, max_tokens=4000)

class BugReport(BaseModel):
    title: str = Field(description="Short summary of the bug")
    steps: str = Field(description="Steps to reproduce")
    expected: str = Field(description="What should have happened")
    actual: str = Field(description="What actually happened")

class TestAnalysis(BaseModel):
    discovered_bugs: List[BugReport] = Field(description="List of bugs extracted from the test logs")
    all_tests_passed: bool = Field(description="True if the test suite is completely green, False if any failures")

# ---------------------------------------------------------------------------
# 1. Generate Test Scripts Node
# ---------------------------------------------------------------------------
def generate_tests_node(state: QAState) -> dict:
    """
    Reads the PRD and generates comprehensive E2E test scripts.
    Writes a Playwright test file to the output directory so the execute node can run it.
    """
    prompt = PromptTemplate.from_template(
        """You are the Lead QA Automation Agent.
        Write a complete Playwright E2E test script (in TypeScript) based on the Product Requirements Document.
        
        PRD:
        {prd}
        
        Design Doc:
        {design}
        
        Return ONLY the raw TypeScript code for the Playwright test. Do not include markdown formatting or explanations.
        Make sure the tests hit 'http://localhost:3000' (or the relevant port).
        """
    )
    
    formatted = prompt.format(
        prd=state.prd,
        design=state.final_design_doc
    )
    
    response = _llm.invoke(formatted)
    test_code = response.content.replace("```typescript", "").replace("```ts", "").replace("```", "").strip()
    
    # Write the test to the output directory
    from pathlib import Path
    output_dir = Path(__file__).resolve().parents[5] / "output"
    
    # Ensure tests directory exists
    test_dir = output_dir / "tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Write the spec file
    test_file = test_dir / "e2e.spec.ts"
    test_file.write_text(test_code, encoding="utf-8")
    
    # Write a basic playwright config if it doesn't exist
    config_file = output_dir / "playwright.config.ts"
    if not config_file.exists():
        config_content = """
import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  use: { baseURL: 'http://localhost:3000' },
});
"""
        config_file.write_text(config_content.strip(), encoding="utf-8")
    
    return {"e2e_test_scripts": test_code}

# ---------------------------------------------------------------------------
# 2. Execute Tests Node
# ---------------------------------------------------------------------------
def execute_tests_node(state: QAState) -> dict:
    """
    Runs the generated test suite using the real tool.
    """
    # Actually execute the tests in the output directory
    output = run_test_suite.invoke({})
    return {"test_run_output": output}

# ---------------------------------------------------------------------------
# 3. Analyze Failures Node
# ---------------------------------------------------------------------------
def analyze_failures_node(state: QAState) -> dict:
    """
    Parses the output of the test runner. 
    If failures exist, extracts them into structured bug descriptions,
    logs them, and spawns new workflow tasks to fix them.
    """
    logs = state.test_run_output
    
    if "TEST_FAILED: No test suite configuration found" in logs or "TEST_EXECUTION_COMPLETE: Tests passed" in logs:
        # No bugs to report
        return {
            "discovered_bugs": [],
            "all_tests_passed": True,
            "new_workflow_tasks": []
        }
        
    prompt = PromptTemplate.from_template(
        """You are the Lead QA Automation Agent.
        Analyze the following test runner logs and identify all distinct bugs or test failures.
        
        Test Logs:
        {logs}
        
        Extract each failure into a structured bug report. If there are no failures, return an empty list and set all_tests_passed to true.
        """
    )
    
    formatted = prompt.format(logs=logs)
    structured_llm = _llm.with_structured_output(TestAnalysis)
    response = structured_llm.invoke(formatted)
    
    new_tasks = []
    import time
    
    # For each bug, log it using the tool and create a workflow task
    for bug in response.discovered_bugs:
        # 1. Log bug to BUGS.md
        generate_bug_report.invoke({
            "title": bug.title,
            "steps": bug.steps,
            "expected": bug.expected,
            "actual": bug.actual
        })
        
        # 2. Spawn task for Dispatcher
        new_tasks.append({
            "id": f"task-bugfix-{int(time.time())}",
            "title": f"Fix QA Bug: {bug.title}",
            "description": f"A bug was discovered during QA testing.\n\nSteps:\n{bug.steps}\n\nExpected:\n{bug.expected}\n\nActual:\n{bug.actual}",
            "assignee_role": "frontend", # Defaulting to frontend, could be smart-routed
            "dependencies": [],
            "priority": 1 # High priority
        })
        time.sleep(1) # Ensure unique IDs
        
    return {
        "discovered_bugs": [bug.dict() for bug in response.discovered_bugs],
        "all_tests_passed": response.all_tests_passed,
        "new_workflow_tasks": new_tasks
    }

# ---------------------------------------------------------------------------
# Task Queue Management
# ---------------------------------------------------------------------------
def pop_task_node(state: QAState) -> dict:
    tasks = list(state.workflow_tasks)
    if not tasks:
        return {"current_task": None}
    next_task = tasks.pop(0)
    return {"workflow_tasks": tasks, "current_task": next_task}

def mark_task_complete_node(state: QAState) -> dict:
    return {"current_task": None}
