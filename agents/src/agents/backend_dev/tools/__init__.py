"""
Backend Developer Agent — MCP and Internal Tools

These tools support the iterative coding loop. They interact with the 
Filesystem MCP, the Database MCP, and the local test runner.
"""
from langchain_core.tools import tool

@tool
def code_linter(file_path: str) -> str:
    """
    Runs the syntax linter (e.g., ruff, mypy, eslint) against the newly written file.
    Args:
        file_path: Path to the file to lint.
    """
    # TODO: Implement local subprocess call to linter
    return "LINT_PASSED"

@tool
def run_unit_tests(test_file_path: str) -> str:
    """
    Runs the unit tests (e.g., pytest, jest) associated with the current task.
    Args:
        test_file_path: Path to the test file.
    """
    # TODO: Implement local subprocess call to test runner
    return "TESTS_PASSED"

@tool
def semantic_code_search(query: str) -> str:
    """
    Searches previously written backend code to find utility functions or router patterns.
    Helps the agent maintain consistency across different tasks.
    Args:
        query: What to search for (e.g., 'JWT authentication utility').
    """
    # TODO: Implement local vector search over the backend/ directory
    raise NotImplementedError("MOCK: Found standard authentication utility in utils/auth.py")

@tool
def db_schema_inspector(connection_string: str, table_name: str) -> str:
    """
    Queries the actual physical database to verify the columns and types of a table.
    Prevents the agent from hallucinating database fields.
    """
    # TODO: Connect to Database MCP / SQLAlchemy inspector
    raise NotImplementedError(f"MOCK: Schema for {table_name} - id (int), created_at (datetime)")
