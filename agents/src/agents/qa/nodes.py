"""
QA Agent — Node Functions

Flow:
  generate_test_scripts → execute_tests → analyze_results 
  → [router: if bugs found] → file_bug_reports
  → [router: if clean] → mark_qa_complete
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agents.src.agents.qa.state import QAState
from typing import Dict, Any
from agents.src.agents.qa.tools import (
    api_integration_tester,
    run_test_suite,
    generate_bug_report,
    visual_browser_tester
)

_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

# ---------------------------------------------------------------------------
# 1. Generate Test Scripts Node
# ---------------------------------------------------------------------------
def generate_tests_node(state: QAState) -> dict:
    """
    Reads the PRD and generates comprehensive E2E test scripts
    (e.g., Cypress/Playwright) to verify user stories.
    """
    prompt = PromptTemplate.from_template(
        """You are the Lead QA Automation Agent.
        Write Playwright E2E test scripts based on the Product Requirements Document.
        
        PRD:
        {prd}
        
        Design Doc:
        {design}
        
        Generate the raw test code.
        """
    )
    
    formatted = prompt.format(
        prd=state.prd,
        design=state.final_design_doc
    )
    
    response = _llm.invoke(formatted)
    
    return {"e2e_test_scripts": response.content}

# ---------------------------------------------------------------------------
# 2. Execute Tests Node
# ---------------------------------------------------------------------------
def execute_tests_node(state: QAState) -> dict:
    """
    Runs the generated test suite.
    """
    # Simulate writing test script to disk and running it
    output = "E2E tests failed" # run_test_suite.invoke({"test_file_path": "tests/e2e/temp_test.spec.ts"})
    
    return {"test_run_output": output}

# ---------------------------------------------------------------------------
# 3. Analyze Failures Node
# ---------------------------------------------------------------------------
def analyze_failures_node(state: QAState) -> dict:
    """
    Parses the output of the test runner. 
    If failures exist, extracts them into structured bug descriptions.
    """
    logs = state.test_run_output.lower()
    discovered_bugs = []
    jira_urls = []
    
    if "fail" in logs:
        discovered_bugs.append({
            "title": "E2E Test Failure: User login flow",
            "steps": "1. Go to /login \n2. Enter creds \n3. Click Submit",
            "expected": "Redirect to dashboard",
            "actual": "Button does nothing, 400 Error in console"
        })
        jira_urls.append("https://jira.company.com/browse/BUG-101")
        
    return {
        "discovered_bugs": discovered_bugs,
        "jira_ticket_urls": jira_urls,
        "all_tests_passed": len(discovered_bugs) == 0
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
