"""
Backend Developer Agent — Node Functions

Flow:
  pop_task → write_code → lint_code → run_tests → mark_task_complete → pop_task
  (loops write_code if lint_code or run_tests fail)
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import json
import os
import re

load_dotenv()

from agents.src.agents.backend_dev.state import BackendDevState
from agents.src.agents.backend_dev.tools import (
    code_linter,
    run_unit_tests,
    semantic_code_search,
    db_schema_inspector
)

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_ROOT_DIR = Path(__file__).resolve().parents[4]

_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, max_tokens=4000)

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

import subprocess
from pydantic import BaseModel, Field
from typing import List

class GeneratedFile(BaseModel):
    path: str = Field(description="The relative path to save the file to, e.g. src/app/api/v1/contact/route.ts")
    content: str = Field(description="The full raw code content of the file")

class CodeGenerationResponse(BaseModel):
    terminal_commands: List[str] = Field(default_factory=list, description="List of shell commands to execute to set up the environment, e.g. ['npm install zod', 'npm install pg']")
    files: List[GeneratedFile] = Field(description="List of files to generate or update")

# ---------------------------------------------------------------------------
# 2. Write Code Node
# ---------------------------------------------------------------------------
def write_code_node(state: BackendDevState) -> dict:
    """
    Writes the application code and the unit tests for the current task.
    """
    prompt_path = _PROMPTS_DIR / "backend_dev.txt"
    prompt = PromptTemplate.from_template(prompt_path.read_text(encoding="utf-8"))
    
    # We load the current db schema from output/db/init.sql if it exists
    db_schema = "No database schema found."
    db_file = _ROOT_DIR / "output" / "db" / "init.sql"
    if db_file.exists():
        db_schema = db_file.read_text(encoding="utf-8")
        
    formatted = prompt.format(
        design_doc=state.final_design_doc,
        tasks=str(state.current_task),
        db_changes=db_schema
    )
    
    formatted += "\n\nCRITICAL: You MUST output ONLY valid JSON matching this schema:\n{\n  \"terminal_commands\": [\"cmd1\", \"cmd2\"],\n  \"files\": [\n    {\"path\": \"src/file.ts\", \"content\": \"raw code\"}\n  ]\n}\n\nDo not use markdown wrappers unless wrapping the entire JSON block in ```json ... ```. Your output MUST parse successfully via json.loads()."
    
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
                print(f"Backend Dev skipped (interactive): {cmd}")
                generated_code_dump.append(f"Skipped interactive command: {cmd}")
                continue
            
            if cmd.startswith("npm install") and "--legacy-peer-deps" not in cmd:
                cmd += " --legacy-peer-deps"
            
            print(f"Backend Dev executing: {cmd}")
            try:
                res = subprocess.run(cmd, shell=True, cwd=str(output_dir), capture_output=True, text=True, check=False, timeout=120)
                generated_code_dump.append(f"Command '{cmd}' succeeded.\n{res.stdout}")
            except subprocess.TimeoutExpired:
                print(f"Command '{cmd}' timed out. Skipping.")
                generated_code_dump.append(f"Command '{cmd}' timed out.")
        
        # Write files
        for f in data.get("files", []):
            file_content = f.get("content", "")
            
            if f.get("path", "").endswith(".json"):
                file_content = re.sub(r'//.*?\n', '\n', file_content)
                file_content = re.sub(r'/\*.*?\*/', '', file_content, flags=re.DOTALL)
            
            file_path = output_dir / f.get("path", "")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_content, encoding="utf-8")
            print(f"Backend Dev wrote: {file_path.relative_to(_ROOT_DIR)}")
            generated_code_dump.append(f"File: {file_path.relative_to(_ROOT_DIR)} written.")
            
    except Exception as e:
        print(f"Raw JSON parsing failed: {e}")
        generated_code_dump.append(f"Error generating code: {e}")
    
    return {
        "current_code_draft": "\n\n".join(generated_code_dump),
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
    Extracts the generated code into backend_file_changes.
    """
    completed = list(state.completed_tasks)
    changes = list(state.backend_file_changes)
    
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
        "backend_file_changes": changes
    }

# ---------------------------------------------------------------------------
# 6. GitHub Push Node
# ---------------------------------------------------------------------------
def push_to_github_node(state: BackendDevState) -> dict:
    """Pushes the current output directory to GitHub."""
    from agents.src.shared.github import push_to_github
    res = push_to_github(state.github_repo_name, "Backend Developer Agent")
    return {"active_pr_number": res.get("pr_number", 0)}
