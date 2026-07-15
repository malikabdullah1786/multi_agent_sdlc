"""
Task Breakdown Agent — Subgraph Definition

Flow:
  START
    → generate_tasks
  END
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.src.agents.task_breakdown.state import TaskBreakdownState
from agents.src.agents.task_breakdown.nodes import generate_tasks_node

# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
workflow = StateGraph(TaskBreakdownState)

workflow.add_node("generate_tasks", generate_tasks_node)

workflow.add_edge(START, "generate_tasks")
workflow.add_edge("generate_tasks", END)

task_breakdown_subgraph = workflow.compile(checkpointer=MemorySaver())
