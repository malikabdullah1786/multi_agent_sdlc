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
def generate_test_scripts_node(state: QAState) -> dict:
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
    output = run_test_suite.invoke({"test_file_path": "tests/e2e/temp_test.spec.ts"})
    
    return {"test_run_output": output}

# ---------------------------------------------------------------------------
# 3. Analyze Results Node
# ---------------------------------------------------------------------------
def analyze_results_node(state: QAState) -> dict:
    """
    Parses the output of the test runner. 
    If failures exist, extracts them into structured bug descriptions.
    """
    # Simple logic for now: if "failed" is in the output, extract a dummy bug
    logs = state.test_run_output.lower()
    discovered_bugs = []
    
    if "fail" in logs:
        discovered_bugs.append({
            "title": "E2E Test Failure: User login flow",
            "steps": "1. Go to /login \n2. Enter creds \n3. Click Submit",
            "expected": "Redirect to dashboard",
            "actual": "Button does nothing, 400 Error in console"
        })
        
    return {"discovered_bugs": discovered_bugs}

# ---------------------------------------------------------------------------
# 4. File Bug Reports Node
# ---------------------------------------------------------------------------
def file_bug_reports_node(state: QAState) -> dict:
    """
    Files a Jira ticket for every bug found during analysis.
    """
    jira_urls = []
    for bug in state.discovered_bugs:
        try:
            # generate_bug_report.invoke(bug)
            pass
        except NotImplementedError as e:
            jira_urls.append(str(e))
            
    # Simulate generated Jira URLs
    if not jira_urls and state.discovered_bugs:
        jira_urls = ["https://jira.company.com/browse/BUG-101"]
        
    return {"jira_ticket_urls": jira_urls, "all_tests_passed": False}

# ---------------------------------------------------------------------------
# 5. Mark QA Complete Node
# ---------------------------------------------------------------------------
def mark_qa_complete_node(state: QAState) -> dict:
    """
    Called when analysis reveals zero bugs. Marks the build as ready for DevOps.
    """
    return {"all_tests_passed": True}
