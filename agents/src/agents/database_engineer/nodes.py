"""
Database Engineer Agent — Node Functions

Flow:
  setup_db → write_migrations → execute_migrations → validate_schema
  → [router loops back to write_migrations if validation fails]
"""
import json
import os
import re
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from agents.src.shared.llm import get_llm
from pydantic import BaseModel, Field
from typing import List

from agents.src.agents.database_engineer.state import DatabaseEngineerState
from typing import Dict, Any
from agents.src.agents.database_engineer.tools import (
    create_project_database,
    run_migrations,
    validate_schema_diff,
    run_terminal_command,
)

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_ROOT_DIR = Path(__file__).resolve().parents[4]

# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------
_llm = get_llm(temperature=0.1, max_tokens=4000)


# ---------------------------------------------------------------------------
# 1. Setup DB Node
# ---------------------------------------------------------------------------
def setup_db_node(state: DatabaseEngineerState) -> dict:
    """
    Creates the isolated PostgreSQL database for this project.
    """
    try:
        conn_string = create_project_database.invoke({"project_name": state.project_name})
    except Exception as e:
        conn_string = f"Failed to create DB: {e}"
        print(conn_string)
        
    return {"db_connection_string": conn_string}


from pydantic import BaseModel, Field
from typing import List

class GeneratedFile(BaseModel):
    path: str = Field(description="The relative path to save the file to, e.g. output/db/init.sql")
    content: str = Field(description="The full raw code content of the file")

class CodeGenerationResponse(BaseModel):
    files: List[GeneratedFile] = Field(description="List of files to generate or update")

def _get_codebase_summary() -> str:
    output_dir = _ROOT_DIR / "output" / "db"
    if not output_dir.exists():
        return "No generated database scripts found yet."
        
    code_blocks = []
    allowed_extensions = {".sql"}
    
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            if path.suffix in allowed_extensions:
                try:
                    rel_path = path.relative_to(_ROOT_DIR)
                    content = path.read_text(encoding="utf-8")
                    if len(content) > 10000:
                        content = content[:10000] + "\n... [TRUNCATED] ..."
                    block = f"File: {rel_path}\n```sql\n{content}\n```"
                    code_blocks.append(block)
                except Exception as e:
                    code_blocks.append(f"File: {path.name} (Error: {e})")
                    
    if not code_blocks:
        return "No files generated yet."
        
    return "\n\n".join(code_blocks)

# ---------------------------------------------------------------------------
# 2. Write Migrations Node
# ---------------------------------------------------------------------------
def write_migrations_node(state: DatabaseEngineerState) -> dict:
    """
    Translates the Architect's design document into raw database schema definitions.
    If the design specifies no database is needed, writes a README and skips.
    """
    # ── Early exit: detect no-DB projects ────────────────────────────────────
    design_doc = state.final_design_doc or ""
    
    # Fallback: If state lost the design doc due to a resume, read it from the generated markdown file
    if len(design_doc.strip()) < 50:
        print("DB Engineer: State design doc is empty. Attempting to load from schema_approval file...")
        try:
            import glob
            approval_files = glob.glob(str(_ROOT_DIR / "schema_approval*.md"))
            if approval_files:
                # Sort by modification time to get the latest
                approval_files.sort(key=os.path.getmtime, reverse=True)
                with open(approval_files[0], "r", encoding="utf-8") as f:
                    design_doc = f.read()
                print(f"DB Engineer: Successfully loaded design doc ({len(design_doc)} chars) from {approval_files[0]}")
        except Exception as e:
            print(f"DB Engineer: Failed to load from file: {e}")
            
    print(f"DB Engineer: Received design doc of length {len(design_doc)}")
    
    if len(design_doc.strip()) < 50:
        raise ValueError("System Design Document is empty or missing! DB Engineer cannot proceed without a design doc.")
        
    design_lower = design_doc.lower()
    no_db_signals = [
        "no database", "no db", "database: none", "in-memory", "localstorage",
        "browser game", "client-side only", "client side only", "static site",
        "no backend", "no server", "no persistent", "file-based", "no persistence"
    ]
    if any(signal in design_lower for signal in no_db_signals):
        readme_path = _ROOT_DIR / "output" / "db" / "README.md"
        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text(
            "# Database\n\nNo database is required for this project.\n\n"
            "The System Design specifies that data is managed in-memory, via localStorage, "
            "or through file-based storage. No SQL schema or migrations are needed.\n",
            encoding="utf-8"
        )
        print("DB Engineer: No database needed for this project. Skipping SQL generation.")
        return {"migration_logs": "Skipped: No database required for this project type."}

    prompt_path = _PROMPTS_DIR / "database_engineer.txt"
    prompt = PromptTemplate.from_template(prompt_path.read_text(encoding="utf-8"))
    
    existing_code = _get_codebase_summary()
    
    formatted = prompt.format(
        design_doc=state.final_design_doc,
        existing_code=existing_code,
        logs=state.migration_logs or "None.",
        diff=state.schema_diff_notes or "None."
    )
    
    formatted += "\n\nCRITICAL: You MUST output ONLY valid JSON matching this schema:\n{\n  \"files\": [\n    {\"path\": \"output/db/init.sql\", \"content\": \"raw code\"}\n  ]\n}\n\nDo not use markdown wrappers unless wrapping the entire JSON block in ```json ... ```. Your output MUST parse successfully via json.loads()."
    
    # Use structured output only — bind_tools + with_structured_output conflict
    structured_llm = _llm.with_structured_output(CodeGenerationResponse)
    
    try:
        response = structured_llm.invoke(formatted)
        output_dir = _ROOT_DIR / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for f in response.files:
            clean_path = f.path.lstrip("/")
            if clean_path.startswith("output/"): clean_path = clean_path[7:]
            file_path = _ROOT_DIR / "output" / clean_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f.content, encoding="utf-8")
            print(f"DB Engineer wrote: {f.path}")
            
    except Exception as e:
        print(f"DB Engineer structured output failed: {e}")
    
    return {"iteration_count": state.iteration_count + 1}


# ---------------------------------------------------------------------------
# 3. Execute Migrations Node
# ---------------------------------------------------------------------------
def execute_migrations_node(state: DatabaseEngineerState) -> dict:
    """
    Runs the migrations against the newly created database.
    """
    try:
        logs = run_migrations.invoke({"connection_string": state.db_connection_string, "tech_stack_hint": "sql"})
    except Exception as e:
        logs = str(e)
        
    return {"migration_logs": logs}


# ---------------------------------------------------------------------------
# 4. Validate Schema Node
# ---------------------------------------------------------------------------
def validate_schema_node(state: DatabaseEngineerState) -> dict:
    """
    Compares the physical database schema against the design document.
    """
    try:
        diff_notes = validate_schema_diff.invoke({
            "connection_string": state.db_connection_string, 
            "design_markdown": state.final_design_doc
        })
    except Exception as e:
        diff_notes = str(e)
        
    is_ready = diff_notes.strip() == "SCHEMA_MATCH"
    return {"db_schema_ready": is_ready, "schema_diff_notes": diff_notes}

# ---------------------------------------------------------------------------
# Task Queue Management
# ---------------------------------------------------------------------------
def pop_task_node(state: DatabaseEngineerState) -> dict:
    tasks = list(state.workflow_tasks)
    if not tasks:
        return {"current_task": None}
    next_task = tasks.pop(0)
    return {"workflow_tasks": tasks, "current_task": next_task}

def mark_task_complete_node(state: DatabaseEngineerState) -> dict:
    return {"current_task": None}

def push_to_github_node(state: DatabaseEngineerState) -> dict:
    """Pushes the current output directory to GitHub with a descriptive commit."""
    from agents.src.shared.github import push_to_github
    current_task = state.current_task or {}
    context = {
        "project_name":      getattr(state, "project_name", "") or "",
        "task_title":        current_task.get("title", "") if isinstance(current_task, dict) else "",
        "task_description":  current_task.get("description", "") if isinstance(current_task, dict) else "",
        "completed_tasks":   list(getattr(state, "completed_task_titles", []) or []),
        "files_changed":     [],  # DB engineer writes migrations; no explicit file list in state
        "scope":             "db",
        "linter_clean":      None,  # No linter concept for DB migrations
    }
    res = push_to_github(state.github_repo_name, "Database Engineer", context=context)
    return {"active_pr_number": res.get("pr_number", 0)}
