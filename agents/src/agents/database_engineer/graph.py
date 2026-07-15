"""
Database Engineer Agent — Subgraph Definition

Flow:
  START
    → setup_db                 (creates isolated DB)
    → write_migrations         (translates design to ORM/migrations based on tech stack)
    → execute_migrations       (runs migration commands)
    → validate_schema          (diffs physical DB vs design doc)
    → [router: loop back to write_migrations if diff fails, else END]
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.src.agents.database_engineer.state import DatabaseEngineerState
from agents.src.agents.database_engineer.nodes import (
    setup_db_node,
    write_migrations_node,
    execute_migrations_node,
    validate_schema_node,
)


# ---------------------------------------------------------------------------
# Router: Should we revise migrations?
# ---------------------------------------------------------------------------
def _should_revise_migrations(state: DatabaseEngineerState) -> str:
    """
    If validation failed or migrations crashed, and we haven't hit the limit,
    loop back to rewrite the migrations. Otherwise end.
    """
    max_iterations = 3
    if not state.db_schema_ready and state.iteration_count < max_iterations:
        return "write_migrations"
    return END


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
workflow = StateGraph(DatabaseEngineerState)

# Register all nodes
workflow.add_node("setup_db", setup_db_node)
workflow.add_node("write_migrations", write_migrations_node)
workflow.add_node("execute_migrations", execute_migrations_node)
workflow.add_node("validate_schema", validate_schema_node)

# Linear execution
workflow.add_edge(START, "setup_db")
workflow.add_edge("setup_db", "write_migrations")
workflow.add_edge("write_migrations", "execute_migrations")
workflow.add_edge("execute_migrations", "validate_schema")

# Autonomous self-healing loop
workflow.add_conditional_edges(
    "validate_schema",
    _should_revise_migrations,
    {
        "write_migrations": "write_migrations",
        END: END
    }
)

database_engineer_subgraph = workflow.compile(checkpointer=MemorySaver())
