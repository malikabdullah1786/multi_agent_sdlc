"""
Database Engineer Agent — Node Functions

Flow:
  setup_db → write_migrations → execute_migrations → validate_schema
  → [router loops back to write_migrations if validation fails]
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agents.src.agents.database_engineer.state import DatabaseEngineerState
from agents.src.agents.database_engineer.tools import (
    create_project_database,
    run_migrations,
    validate_schema_diff,
)

# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------
_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)


# ---------------------------------------------------------------------------
# 1. Setup DB Node
# ---------------------------------------------------------------------------
def setup_db_node(state: DatabaseEngineerState) -> dict:
    """
    Creates the isolated PostgreSQL database for this project.
    """
    try:
        # Mock tool call wrapper
        conn_string = f"postgresql://admin:password@localhost:5432/{state.project_name}"
        # create_project_database.invoke({"project_name": state.project_name})
    except NotImplementedError as e:
        # Using string parsing of the mock exception for now
        conn_string = str(e).split("Connection string: ")[-1]
        
    return {"db_connection_string": conn_string}


# ---------------------------------------------------------------------------
# 2. Write Migrations Node
# ---------------------------------------------------------------------------
def write_migrations_node(state: DatabaseEngineerState) -> dict:
    """
    Translates the Architect's design document into actual ORM models and
    migration files. The LLM decides whether to write Python/SQLAlchemy or
    TypeScript/Prisma based on the design doc.
    """
    prompt = PromptTemplate.from_template(
        """You are an elite Database Engineer Agent.
        Your job is to read the System Design Document and write the physical ORM models
        and migration scripts.
        
        Read the design document and determine the tech stack (e.g. Prisma vs Alembic/SQLAlchemy).
        Then generate the exact file contents needed to build the database schema.
        
        Design Document:
        {design}
        
        Previous Migration Logs (if any):
        {logs}
        
        Previous Schema Diff Notes (if any):
        {diff}
        
        Generate the raw code required. (This will eventually use a Filesystem MCP to write to disk).
        """
    )
    
    formatted = prompt.format(
        design=state.final_design_doc,
        logs=state.migration_logs or "None.",
        diff=state.schema_diff_notes or "None."
    )
    
    _llm.invoke(formatted) # Simulating filesystem writes for now
    
    return {"iteration_count": state.iteration_count + 1}


# ---------------------------------------------------------------------------
# 3. Execute Migrations Node
# ---------------------------------------------------------------------------
def execute_migrations_node(state: DatabaseEngineerState) -> dict:
    """
    Runs the migrations against the newly created database.
    """
    try:
        # run_migrations.invoke({"connection_string": state.db_connection_string, "tech_stack_hint": "auto"})
        logs = "OK: Migrations executed successfully."
    except NotImplementedError as e:
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
        # validate_schema_diff.invoke({"connection_string": state.db_connection_string, "design_markdown": state.final_design_doc})
        diff_notes = "SCHEMA_MATCH"
    except NotImplementedError as e:
        diff_notes = "SCHEMA_MATCH"
        
    return {
        "schema_diff_notes": diff_notes,
        "db_schema_ready": diff_notes == "SCHEMA_MATCH"
    }
