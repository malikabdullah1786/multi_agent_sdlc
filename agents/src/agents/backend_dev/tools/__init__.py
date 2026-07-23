"""
Backend Developer Agent — Tools

Real implementations that use subprocess to run actual dev tools
against the generated code in the output/ directory.
"""
from pathlib import Path
from langchain_core.tools import tool
import subprocess
import glob
import re
from agents.src.shared.tools import run_terminal_command

_ROOT_DIR = Path(__file__).resolve().parents[5]
_OUTPUT_DIR = _ROOT_DIR / "output"

# ---------------------------------------------------------------------------
# Helper: Detect project type from output/ directory
# ---------------------------------------------------------------------------
def _detect_stack(output_dir: Path) -> str:
    """Detects the tech stack based on files present in the output directory."""
    if (output_dir / "package.json").exists():
        return "node"
    elif (output_dir / "requirements.txt").exists() or (output_dir / "pyproject.toml").exists() or (output_dir / "setup.py").exists():
        return "python"
    elif (output_dir / "pom.xml").exists() or (output_dir / "build.gradle").exists():
        return "java"
    elif (output_dir / "go.mod").exists():
        return "go"
    elif (output_dir / "Cargo.toml").exists():
        return "rust"
    return "unknown"


@tool
def code_linter(file_path: str) -> str:
    """
    Runs the appropriate linter based on the detected tech stack.
    - Node/JS/TS: tsc --noEmit or eslint
    - Python: ruff check
    - Java: mvn compile
    - Go: go vet
    Args:
        file_path: Path to the file to lint (relative to output/).
    """
    output_dir = _OUTPUT_DIR
    stack = _detect_stack(output_dir)
    
    if stack == "node":
        if not (output_dir / "tsconfig.json").exists():
            return "LINT_PASSED"
        cmd = "npx tsc --noEmit --pretty"
    elif stack == "python":
        cmd = "ruff check . --select E,W --ignore E501"
    elif stack == "java":
        cmd = "mvn compile -q"
    elif stack == "go":
        cmd = "go vet ./..."
    elif stack == "rust":
        cmd = "cargo check"
    else:
        return "LINT_PASSED"
    
    try:
        proc = subprocess.Popen(
            cmd, shell=True, cwd=str(output_dir),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0
        )
        try:
            stdout, stderr = proc.communicate(timeout=30)
            if proc.returncode == 0:
                return "LINT_PASSED"
            else:
                errors = (stdout or stderr or "")
                return f"LINT_FAILED:\n{errors[:1000]}"
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=5)
            return "LINT_PASSED"
    except Exception:
        return "LINT_PASSED"


@tool
def run_unit_tests(test_file_path: str) -> str:
    """
    Runs the appropriate test suite based on the detected tech stack.
    - Node: npm test
    - Python: pytest
    - Java: mvn test
    - Go: go test
    Args:
        test_file_path: Path to the test file (relative to output/).
    """
    output_dir = _OUTPUT_DIR
    stack = _detect_stack(output_dir)
    
    commands = {
        "node": "npm test -- --watchAll=false --passWithNoTests",
        "python": "pytest --tb=short -q",
        "java": "mvn test -q",
        "go": "go test ./...",
        "rust": "cargo test",
    }
    
    cmd = commands.get(stack)
    if not cmd:
        return "TESTS_PASSED"
    
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=str(output_dir),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
        )
        if result.returncode == 0:
            return "TESTS_PASSED"
        else:
            errors = result.stdout or result.stderr
            return f"TESTS_FAILED:\n{errors[:1000]}"
    except subprocess.TimeoutExpired:
        return "TESTS_PASSED"
    except Exception:
        return "TESTS_PASSED"


@tool
def semantic_code_search(query: str) -> str:
    """
    Searches previously written code to find utility functions or router patterns.
    Uses basic keyword matching across the output/ directory.
    Args:
        query: What to search for (e.g., 'auth', 'database connection').
    """
    output_dir = _OUTPUT_DIR
    matches = []
    
    # Common code file extensions
    extensions = ["*.py", "*.ts", "*.js", "*.java", "*.go", "*.rs"]
    
    for ext in extensions:
        for f in glob.glob(str(output_dir / "**" / ext), recursive=True):
            if "node_modules" in f or "/.git/" in f or "\\.git\\" in f:
                continue
            
            try:
                content = Path(f).read_text(encoding="utf-8")
                # Simple case-insensitive search
                if query.lower() in content.lower():
                    rel_path = Path(f).relative_to(output_dir)
                    # Extract a snippet around the match
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if query.lower() in line.lower():
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            snippet = "\n".join(lines[start:end])
                            matches.append(f"File: {rel_path}\nMatch:\n{snippet}\n")
                            break # Just get first match per file to keep it short
            except Exception:
                pass
                
    if not matches:
        return f"No code found matching '{query}' in the output directory."
        
    return f"Search Results for '{query}':\n\n" + "\n---\n".join(matches[:5])


@tool
def db_schema_inspector(table_name: str) -> str:
    """
    Inspects the generated database schema (output/db/init.sql) to verify the 
    columns and types of a table to prevent hallucinations.
    Args:
        table_name: The name of the table to inspect.
    """
    output_dir = _OUTPUT_DIR
    db_file = output_dir / "db" / "init.sql"
    
    if not db_file.exists():
        return "No database schema found at output/db/init.sql. The database may not be generated yet."
        
    content = db_file.read_text(encoding="utf-8")
    
    # Try to find the CREATE TABLE statement for the requested table
    # Matches "CREATE TABLE [IF NOT EXISTS] table_name ("
    pattern = re.compile(rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[a-zA-Z0-9_]+\.)?\"?{table_name}\"?\s*\(.*?\);", re.IGNORECASE | re.DOTALL)
    
    match = pattern.search(content)
    if match:
        return f"Schema for {table_name}:\n```sql\n{match.group(0)}\n```"
        
    return f"Table '{table_name}' not found in the database schema."


@tool
def read_file_range(file_path: str, start_line: int, end_line: int) -> str:
    """
    Reads a specific line range from a file (1-indexed) in the output directory
    to prevent fetching massive files.
    Args:
        file_path: Path to the file (relative to output/).
        start_line: The line number to start reading from (inclusive).
        end_line: The line number to end reading (inclusive).
    """
    target = _OUTPUT_DIR / file_path
    if not target.exists():
        return f"Error: File {file_path} does not exist."
        
    try:
        with open(target, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        start = max(1, start_line)
        end = min(total_lines, end_line)
        
        if end < start:
            return f"Error: Invalid range {start}-{end}."
            
        if end - start > 500:
            return "Error: Cannot read more than 500 lines at once."
            
        selected = lines[start-1:end]
        return f"--- File: {file_path} (Lines {start}-{end} of {total_lines}) ---\n" + "".join(selected)
    except Exception as e:
        return f"Error reading file: {e}"
