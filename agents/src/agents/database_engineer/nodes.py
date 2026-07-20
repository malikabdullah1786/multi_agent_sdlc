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
from langchain_groq import ChatGroq

from agents.src.agents.database_engineer.state import DatabaseEngineerState
from typing import Dict, Any
from agents.src.agents.database_engineer.tools import (
    create_project_database,
    run_migrations,
    validate_schema_diff,
)

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_ROOT_DIR = Path(__file__).resolve().parents[4]

# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------
_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, max_tokens=2000)


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

# ---------------------------------------------------------------------------
# 2. Write Migrations Node
# ---------------------------------------------------------------------------
def write_migrations_node(state: DatabaseEngineerState) -> dict:
    """
    Translates the Architect's design document into raw SQL schema definitions.
    """
    prompt_path = _PROMPTS_DIR / "database_engineer.txt"
    prompt = PromptTemplate.from_template(prompt_path.read_text(encoding="utf-8"))
    
    formatted = prompt.format(
        design_doc=state.final_design_doc,
        logs=state.migration_logs or "None.",
        diff=state.schema_diff_notes or "None."
    )
    
    formatted += "\n\nCRITICAL: You MUST output ONLY valid JSON matching this schema:\n{\n  \"files\": [\n    {\"path\": \"output/db/init.sql\", \"content\": \"raw code\"}\n  ]\n}\n\nDo not use markdown wrappers unless wrapping the entire JSON block in ```json ... ```. Your output MUST parse successfully via json.loads()."
    
    try:
        response = _llm.invoke(formatted)
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
        
        for f in data.get("files", []):
            file_path = _ROOT_DIR / f.get("path", "")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f.get("content", ""), encoding="utf-8")
            print(f"DB Engineer wrote: {f.get('path', '')}")
            
    except Exception as e:
        print(f"Raw JSON parsing failed: {e}")
    
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
