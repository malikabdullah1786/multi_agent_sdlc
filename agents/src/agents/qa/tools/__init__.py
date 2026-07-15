"""
QA Agent — MCP and Internal Tools

These tools support automated E2E testing, exploratory browser testing, 
and automated Jira bug reporting.
"""
from langchain_core.tools import tool

@tool
def api_integration_tester(endpoint: str, method: str, payload: dict = None) -> str:
    """
    Fires raw HTTP requests against the backend (like Postman or curl).
    Useful for testing API logic independently of the UI.
    """
    # TODO: Implement basic HTTP request execution via requests
    return f"MOCK: {method} {endpoint} returned 200 OK."

@tool
def run_test_suite(test_file_path: str) -> str:
    """
    Executes the automated E2E test suite (e.g., npx playwright test).
    Args:
        test_file_path: Path to the generated test script.
    """
    # TODO: Implement local subprocess call
    return "TEST_EXECUTION_COMPLETE: 3 passed, 1 failed."

@tool
def generate_bug_report(title: str, steps: str, expected: str, actual: str) -> str:
    """
    Formats the bug details and files a ticket directly into Jira via the Jira MCP.
    Args:
        title: Bug summary.
        steps: Steps to reproduce.
        expected: Expected behavior based on the PRD.
        actual: Actual behavior observed during testing.
    """
    # TODO: Connect to Jira MCP
    raise NotImplementedError("MOCK: Bug logged as JIRA-1025")

@tool
def visual_browser_tester(url: str, action: str) -> str:
    """
    Spins up a headless browser to interact with the UI.
    Actions can include clicking buttons, typing text, or grabbing DOM state.
    """
    # TODO: Connect to Browser MCP
    raise NotImplementedError(f"MOCK: Browser action '{action}' performed on {url}")
