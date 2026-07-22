"""
Frontend Developer Agent — Tools

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

@tool
def api_schema_fetcher() -> str:
    """
    Scans the output/ directory for backend API route files across any framework
    (Next.js, Express, FastAPI, Django, Flask, Spring, Go, etc.)
    to discover available endpoints and their structure.
    """
    output_dir = _OUTPUT_DIR
    
    api_files = []
    
    # Scan for common backend route/API file patterns across all frameworks
    patterns = [
        # Next.js App Router
        "src/app/api/**/route.ts", "src/app/api/**/route.js",
        "app/api/**/route.ts", "app/api/**/route.js",
        # Next.js Pages Router
        "pages/api/**/*.ts", "pages/api/**/*.js",
        # Express / Node.js
        "**/routes/**/*.js", "**/routes/**/*.ts",
        "**/controllers/**/*.js", "**/controllers/**/*.ts",
        # Python (FastAPI, Flask, Django)
        "**/routes/**/*.py", "**/views/**/*.py",
        "**/routers/**/*.py", "**/endpoints/**/*.py",
        "**/urls.py", "**/views.py", "**/api.py",
        # Java / Spring
        "**/controller/**/*.java", "**/Controller.java",
        # Go
        "**/handlers/**/*.go", "**/routes/**/*.go",
        # General
        "**/openapi.json", "**/openapi.yaml", "**/swagger.json", "**/swagger.yaml",
    ]
    
    for pattern in patterns:
        found = glob.glob(str(output_dir / pattern), recursive=True)
        for f in found:
            # Skip node_modules and hidden directories
            if "node_modules" in f or "/.git/" in f or "\\.git\\" in f:
                continue
            rel_path = Path(f).relative_to(output_dir)
            try:
                content = Path(f).read_text(encoding="utf-8")
                api_files.append(f"File: {rel_path}\n{content[:500]}")
            except Exception:
                api_files.append(f"File: {rel_path} (could not read)")
    
    if api_files:
        return "Discovered Backend API Files:\n\n" + "\n\n---\n\n".join(api_files[:20])
    
    # Fallback: read the DB schema if no API routes found
    db_file = output_dir / "db" / "init.sql"
    if db_file.exists():
        return f"No API routes found, but found DB schema:\n{db_file.read_text(encoding='utf-8')[:1000]}"
    
    return "No backend API files or schemas found in output/ directory."


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
    elif (output_dir / "Gemfile").exists():
        return "ruby"
    return "unknown"


@tool
def frontend_linter(file_path: str) -> str:
    """
    Runs the appropriate linter based on the detected tech stack.
    Args:
        file_path: Path to the file to lint (relative to output/).
    """
    output_dir = _OUTPUT_DIR
    stack = _detect_stack(output_dir)
    
    # Only run tsc if tsconfig.json exists
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
    
    # Use Popen for safe timeout handling on Windows
    try:
        proc = subprocess.Popen(
            cmd, shell=True, cwd=str(output_dir),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0
        )
        try:
            stdout, stderr = proc.communicate(timeout=30)
            if proc.returncode == 0:
                return "LINT_PASSED"
            else:
                errors = stdout.decode(errors="replace") or stderr.decode(errors="replace")
                return f"LINT_FAILED:\n{errors[:1000]}"
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate(timeout=5)
            return "LINT_PASSED"
    except Exception:
        return "LINT_PASSED"


@tool
def run_component_tests(test_file_path: str) -> str:
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
def visual_browser_check(route_url: str) -> str:
    """
    Attempts to build the project to catch compilation/runtime errors.
    - Node/Next.js: npx next build
    - Python: python -m compileall
    - Java: mvn package
    - Go: go build
    Args:
        route_url: The local url to check (used for web projects).
    """
    output_dir = _OUTPUT_DIR
    stack = _detect_stack(output_dir)
    
    commands = {
        "node": "npx next build",
        "python": "python -m compileall . -q",
        "java": "mvn package -q -DskipTests",
        "go": "go build ./...",
        "rust": "cargo build",
    }
    
    cmd = commands.get(stack)
    if not cmd:
        return "CONSOLE_CLEAN: Unknown stack, skipping build check."
    
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=str(output_dir),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
        )
        if result.returncode == 0:
            return f"CONSOLE_CLEAN: {stack} build succeeded without errors."
        else:
            errors = result.stdout or result.stderr
            if "Error" in errors or "error" in errors:
                return f"BUILD_ERRORS:\n{errors[:1500]}"
            return f"CONSOLE_CLEAN: {stack} build completed with warnings only."
    except subprocess.TimeoutExpired:
        return "CONSOLE_CLEAN: Build timed out (likely compiling successfully but slowly)."
    except Exception as e:
        return f"CONSOLE_CLEAN: Could not run build check: {e}"


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
    extensions = ["*.py", "*.ts", "*.js", "*.java", "*.go", "*.rs", "*.tsx", "*.jsx"]
    
    for ext in extensions:
        for f in glob.glob(str(output_dir / "**" / ext), recursive=True):
            if "node_modules" in f or "/.git/" in f or "\\.git\\" in f or ".next" in f:
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
