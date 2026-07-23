"""
Frontend Developer Agent — Node Functions

Flow:
  pop_task → write_ui_code → lint_code → run_tests
  → browser_check → mark_task_complete → pop_task
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from agents.src.shared.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
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
    visual_browser_check,
    read_file_range,
    semantic_code_search
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

_llm = get_llm(temperature=0.1, max_tokens=4000)

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
def _get_codebase_summary() -> str:
    output_dir = _ROOT_DIR / "output"
    if not output_dir.exists():
        return "No generated code found yet."
        
    code_blocks = []
    omitted_files = []
    allowed_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".css"}
    ignored_dirs = {"node_modules", ".git", ".next", "dist", "build"}
    
    MAX_TOTAL_CHARS = 50000
    current_total_chars = 0
    
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            if any(part in ignored_dirs for part in path.parts):
                continue
            if path.suffix in allowed_extensions:
                rel_path = path.relative_to(_ROOT_DIR)
                if current_total_chars >= MAX_TOTAL_CHARS:
                    omitted_files.append(str(rel_path))
                    continue
                    
                try:
                    content = path.read_text(encoding="utf-8")
                    if len(content) > 8000:
                        content = content[:8000] + "\n... [TRUNCATED] ..."
                    block = f"File: {rel_path}\n```\n{content}\n```"
                    code_blocks.append(block)
                    current_total_chars += len(block)
                except Exception as e:
                    code_blocks.append(f"File: {rel_path} (Error: {e})")
                    
    if not code_blocks and not omitted_files:
        return "No files generated yet."
        
    res = "\n\n".join(code_blocks)
    if omitted_files:
        res += "\n\n### Omitted files due to context limits:\n" + "\n".join(f"- {f}" for f in omitted_files)
    return res

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
    
    existing_code = _get_codebase_summary()
    
    # Append instructions to output raw JSON
    formatted = prompt.format(
        design_doc=state.final_design_doc,
        tasks=str(state.current_task),
        db_schema=db_schema,
        existing_code=existing_code,
        linter_errors=state.linter_errors or "None.",
        test_failures=state.test_failures or "None.",
    )
    
    formatted += "\n\nCRITICAL: You MUST output ONLY valid JSON matching this schema:\n{\n  \"terminal_commands\": [\"cmd1\", \"cmd2\"],\n  \"files\": [\n    {\"path\": \"src/file.tsx\", \"content\": \"raw code\"}\n  ]\n}\n\nDo not use markdown wrappers unless wrapping the entire JSON block in ```json ... ```. Your output MUST parse successfully via json.loads()."
    
    from langchain_core.tools import tool
    from agents.src.shared.llm import safe_web_search
    from agents.src.shared.tools import run_terminal_command
    
    @tool
    def search_web(query: str) -> str:
        """Searches the web for documentation, tutorials, or solutions to coding problems."""
        return safe_web_search(query)
        
    # Bind tools to the LLM
    llm_with_tools = _llm.bind_tools([read_file_range, semantic_code_search, search_web, run_terminal_command])
    
    # Inform the agent it can execute terminal commands, read chunks or search existing code
    formatted += "\n\nNote: You have FULL generic terminal access. You can call the `run_terminal_command` tool to execute any shell command in the project directory, call `semantic_code_search` to locate code patterns, call `read_file_range` to view files, or call `search_web` to look up docs. Gather whatever context you need first. Once ready, output your final file generation response."
    formatted += "\n\nCRITICAL RULE: DO NOT use tool calling for your final JSON output. You MUST output your final JSON directly in your message text response, surrounded by ```json ... ```. If you wrap your final JSON in a tool call (like 'json' or 'CodeGenerationResponse'), it will crash the system."
    
    messages = [
        SystemMessage(content=formatted),
        HumanMessage(content="Start your implementation. You can execute shell commands with `run_terminal_command`, search the codebase with `semantic_code_search`, or read files with `read_file_range`. When done, output the final code JSON as plain text.")
    ]
    
    generated_code_dump = []
    
    try:
        # Loop for up to 4 turns of tool execution
        for turn in range(4):
            try:
                response = llm_with_tools.invoke(messages)
            except Exception as invoke_e:
                error_str = str(invoke_e)
                # Catch Groq tool_use_failed exceptions where it puts the payload in failed_generation
                if "failed_generation" in error_str:
                    fg_idx = error_str.find("'failed_generation': '")
                    if fg_idx != -1:
                        start_idx = fg_idx + len("'failed_generation': '")
                        end_idx = error_str.rfind("'}}")
                        if end_idx == -1 or end_idx <= start_idx:
                            end_idx = error_str.rfind("'")
                        try:
                            raw_fg = error_str[start_idx:end_idx].replace("\\n", "\n").replace("\\'", "'")
                            failed_gen = json.loads(raw_fg, strict=False)
                            args = failed_gen.get("arguments", {})
                            class DummyResponse:
                                content = json.dumps(args) if isinstance(args, dict) else str(args)
                                tool_calls = []
                            response = DummyResponse()
                        except Exception:
                            raise invoke_e
                    else:
                        raise invoke_e
                else:
                    raise invoke_e
                    
            messages.append(response)
            
            if not getattr(response, "tool_calls", None):
                break
                
            # Process tool calls
            for tool_call in response.tool_calls:
                try:
                    from backend.telemetry import broadcast_tool_call
                    broadcast_tool_call(tool_call["name"], str(tool_call.get("args", {})))
                except Exception:
                    pass

                if tool_call["name"] == "read_file_range":
                    # Execute tool physically
                    print(f"Frontend Dev calling tool: {tool_call['name']} with args {tool_call['args']}")
                    result = read_file_range.invoke(tool_call["args"])
                    messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
                elif tool_call["name"] == "semantic_code_search":
                    # Execute tool physically
                    print(f"Frontend Dev calling tool: {tool_call['name']} with args {tool_call['args']}")
                    result = semantic_code_search.invoke(tool_call["args"])
                    messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
                elif tool_call["name"] == "search_web":
                    print(f"Frontend Dev calling tool: {tool_call['name']} with args {tool_call['args']}")
                    result = search_web.invoke(tool_call["args"])
                    messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
                elif tool_call["name"] == "run_terminal_command":
                    print(f"Frontend Dev calling tool: {tool_call['name']} with args {tool_call['args']}")
                    result = run_terminal_command.invoke(tool_call["args"])
                    messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
                    
        final_content = messages[-1].content
        
        # Now parse final_content as the code JSON response
        output_dir = _ROOT_DIR / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import re
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', final_content, re.DOTALL)
        if match:
            content = match.group(1)
        else:
            start = final_content.find('{')
            end = final_content.rfind('}')
            if start != -1 and end != -1:
                content = final_content[start:end+1]
            else:
                content = final_content
                
        data = json.loads(content, strict=False)
        
        # Execute terminal commands
        for cmd in data.get("terminal_commands", []):
            # Only block infinite blocking dev server daemons that hang execution
            DAEMON_SERVER_PREFIXES = [
                "npm run dev", "npm run start", "npm start", "node server", 
                "python manage.py runserver", "flask run", "uvicorn", "npx next dev"
            ]
            if any(cmd.strip().startswith(prefix) for prefix in DAEMON_SERVER_PREFIXES):
                print(f"Frontend Dev skipped (infinite server daemon): {cmd}")
                continue
                
            if cmd.startswith("npm install") and "--legacy-peer-deps" not in cmd:
                cmd += " --legacy-peer-deps"
                
            print(f"Frontend Dev executing: {cmd}")
            try:
                res = subprocess.run(cmd, shell=True, cwd=str(output_dir), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, check=False)
                try:
                    from backend.telemetry import broadcast_tool_call
                    broadcast_tool_call("execute_command", cmd, event_type="TERMINAL_COMMAND", payload_extra={"command": cmd, "stdout": res.stdout or "", "stderr": res.stderr or "", "exit_code": res.returncode})
                except Exception:
                    pass
            except subprocess.TimeoutExpired:
                print(f"Frontend Dev skipped (Timeout): {cmd}")
                generated_code_dump.append({cmd: "Timed out"})
            
        # Write files
        for f in data.get("files", []):
            clean_path = f.get("path", "").lstrip("/")
            if clean_path.startswith("output/"): clean_path = clean_path[7:]
            file_path = output_dir / clean_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_content = f.get("content", "")
            if f.get("path", "").endswith(".json"):
                file_content = re.sub(r'//.*?\n', '\n', file_content)
                file_content = re.sub(r'/\*.*?\*/', '', file_content, flags=re.DOTALL)
                
            file_path.write_text(file_content, encoding="utf-8")
            generated_code_dump.append({f.get("path", ""): "Generated"})
            print(f"Frontend Dev wrote: {file_path.relative_to(_ROOT_DIR)}")
            try:
                from backend.telemetry import broadcast_tool_call
                rel_p = str(file_path.relative_to(output_dir))
                broadcast_tool_call("create_file", rel_p, event_type="FILE_CHANGE", payload_extra={"path": rel_p, "action": "CREATED", "diff": f"+ Created file {rel_p}"})
            except Exception:
                pass
            
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
                "status": "completed"
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
    """Pushes the current output directory to GitHub with a descriptive commit."""
    from agents.src.shared.github import push_to_github
    current_task = state.current_task or {}
    ui_files = getattr(state, "generated_ui_code", []) or []
    context = {
        "project_name":      getattr(state, "project_name", "") or "",
        "task_title":        current_task.get("title", "") if isinstance(current_task, dict) else "",
        "task_description":  current_task.get("description", "") if isinstance(current_task, dict) else "",
        "completed_tasks":   list(getattr(state, "completed_task_titles", []) or []),
        "files_changed":     [f if isinstance(f, dict) else {"path": str(f)} for f in ui_files],
        "scope":             "ui",
        "linter_clean":      not bool(getattr(state, "linter_errors", "")),
    }
    res = push_to_github(state.github_repo_name, "Frontend Developer Agent", context=context)
    return {"active_pr_number": res.get("pr_number", 0)}
