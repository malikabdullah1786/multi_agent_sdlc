"""
Frontend Developer Agent — Node Functions

Flow:
  pop_task → write_ui_code → lint_code → run_tests
  → browser_check → mark_task_complete → pop_task
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import subprocess
import json
import os

load_dotenv()

from pydantic import BaseModel, Field
from typing import List

from agents.src.agents.frontend_dev.state import FrontendDevState
from agents.src.agents.frontend_dev.tools import (
    api_schema_fetcher,
    frontend_linter,
    run_component_tests,
    visual_browser_check
)

# ---------------------------------------------------------------------------
# Pydantic structured output models
# ---------------------------------------------------------------------------
class GeneratedFile(BaseModel):
    path: str = Field(description="The relative path to save the file to, e.g. src/app/page.tsx")
    content: str = Field(description="The full raw code content of the file")

class CodeGenerationResponse(BaseModel):
    terminal_commands: List[str] = Field(default_factory=list, description="List of shell commands to execute to set up the environment, e.g. npm install zod")
    files: List[GeneratedFile] = Field(description="List of files to generate or update")

# ---------------------------------------------------------------------------
# LLM & paths
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_ROOT_DIR = Path(__file__).resolve().parents[4]

_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, max_tokens=4000)

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
# 2. Write UI Code Node
# ---------------------------------------------------------------------------
def write_ui_code_node(state: FrontendDevState) -> dict:
    """Writes React/Next.js components and pages without native tool calling."""
    prompt_path = _PROMPTS_DIR / "frontend_dev.txt"
    prompt = PromptTemplate.from_template(prompt_path.read_text(encoding="utf-8"))
    
    # Read the DB schema from output/ if it exists
    db_schema = "No database schema found."
    db_file = _ROOT_DIR / "output" / "db" / "init.sql"
    if db_file.exists():
        db_schema = db_file.read_text(encoding="utf-8")
    
    # Append instructions to output raw JSON
    formatted = prompt.format(
        design_doc=state.final_design_doc,
        tasks=str(state.current_task),
        db_schema=db_schema,
        linter=state.linter_errors or "None.",
        tests=state.test_failures or "None."
    )
    
    formatted += "\n\nCRITICAL: You MUST output ONLY valid JSON matching this schema:\n{\n  \"terminal_commands\": [\"cmd1\", \"cmd2\"],\n  \"files\": [\n    {\"path\": \"src/file.tsx\", \"content\": \"raw code\"}\n  ]\n}\n\nDo not use markdown wrappers unless wrapping the entire JSON block in ```json ... ```. Your output MUST parse successfully via json.loads()."
    
    generated_code_dump = []
    
    try:
        response = _llm.invoke(formatted)
        output_dir = _ROOT_DIR / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import re
        content = response.content
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
        if match:
            content = match.group(1)
        else:
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                content = content[start:end+1]
                
        data = json.loads(content, strict=False)
        
        # Execute terminal commands
        for cmd in data.get("terminal_commands", []):
            BLOCKED_PREFIXES = [
                "npx create-", "npm init", "yarn create", "npm run dev",
                "npm run start", "npm start", "node server", "python manage.py runserver",
                "flask run", "uvicorn", "npx next dev", "npx ts-jest", "npx prisma"
            ]
            if any(cmd.strip().startswith(prefix) for prefix in BLOCKED_PREFIXES):
                print(f"Frontend Dev skipped (interactive): {cmd}")
                continue
                
            if cmd.startswith("npm install") and "--legacy-peer-deps" not in cmd:
                cmd += " --legacy-peer-deps"
                
            print(f"Frontend Dev executing: {cmd}")
            try:
                subprocess.run(cmd, shell=True, cwd=str(output_dir), capture_output=True, timeout=120, check=False)
            except subprocess.TimeoutExpired:
                print(f"Frontend Dev skipped (Timeout): {cmd}")
                generated_code_dump.append({cmd: "Timed out"})
            
        # Write files
        for f in data.get("files", []):
            file_path = output_dir / f.get("path", "")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_content = f.get("content", "")
            if f.get("path", "").endswith(".json"):
                file_content = re.sub(r'//.*?\n', '\n', file_content)
                file_content = re.sub(r'/\*.*?\*/', '', file_content, flags=re.DOTALL)
                
            file_path.write_text(file_content, encoding="utf-8")
            generated_code_dump.append({f.get("path", ""): "Generated"})
            print(f"Frontend Dev wrote: {file_path.relative_to(_ROOT_DIR)}")
            
    except Exception as e:
        print(f"Raw JSON parsing failed: {e}")
        generated_code_dump.append(f"Error generating code: {e}")
        
    return {
        "current_code_draft": "\n\n".join(str(item) for item in generated_code_dump),
        "iteration_count": state.iteration_count + 1
    }

# ---------------------------------------------------------------------------
# 3. Lint Code Node
# ---------------------------------------------------------------------------
def lint_code_node(state: FrontendDevState) -> dict:
    """Runs the syntax linter (e.g. ESLint) against the generated UI code."""
    result = frontend_linter.invoke({"file_path": "frontend/src/temp.tsx"})
    return {"linter_errors": "" if result == "LINT_PASSED" else result}

# ---------------------------------------------------------------------------
# 4. Run Tests Node
# ---------------------------------------------------------------------------
def run_tests_node(state: FrontendDevState) -> dict:
    """Runs the component unit tests."""
    result = run_component_tests.invoke({"test_file_path": "frontend/src/temp.test.tsx"})
    return {"test_failures": "" if result == "TESTS_PASSED" else result}

# ---------------------------------------------------------------------------
# 5. Browser Check Node
# ---------------------------------------------------------------------------
def browser_check_node(state: FrontendDevState) -> dict:
    """Uses a headless browser to render the UI and check for runtime console errors."""
    result = visual_browser_check.invoke({"route_url": "http://localhost:3000"})
    return {"browser_console_errors": "" if "CONSOLE_CLEAN" in result else result}

# ---------------------------------------------------------------------------
# 6. Mark Task Complete Node
# ---------------------------------------------------------------------------
def mark_task_complete_node(state: FrontendDevState) -> dict:
    """Task is completed and pushed to the done pile."""
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

# ---------------------------------------------------------------------------
# 7. GitHub Push Node
# ---------------------------------------------------------------------------
def push_to_github_node(state: FrontendDevState) -> dict:
    """Pushes the current output directory to GitHub."""
    from agents.src.shared.github import push_to_github
    res = push_to_github(state.github_repo_name, "Frontend Developer Agent")
    return {"active_pr_number": res.get("pr_number", 0)}
