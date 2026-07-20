"""
Task Breakdown Agent — Node Functions

Flow:
  generate_tasks
"""
import json
from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from agents.src.agents.task_breakdown.state import TaskBreakdownState

_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, max_tokens=4000)

# ---------------------------------------------------------------------------
# 1. Generate Tasks Node
# ---------------------------------------------------------------------------
class Task(BaseModel):
    title: str = Field(description="The title of the task")
    description: str = Field(description="Detailed description of the task")
    assignee_role: str = Field(description="The role assigned: 'database_engineer', 'devops', 'backend', 'frontend', 'qa', 'reviewer', or 'security'")
    priority: int = Field(description="Priority from 1 (highest) to 5 (lowest). Tasks with no dependencies should have priority 1.")
    dependencies: List[str] = Field(description="List of task titles that this task depends on")

class TaskList(BaseModel):
    tasks: List[Task] = Field(description="A list of granular tasks for the project")

def generate_tasks_node(state: TaskBreakdownState) -> dict:
    """
    Reads the PRD and Architecture Doc, and breaks the project into granular JSON tasks.
    These tasks will be consumed by the Backend and Frontend Developer agents.
    """
    from langchain_core.prompts import ChatPromptTemplate
    import os
    
    # Load system prompt from file
    prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/task_breakdown.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Here is the Design Document:\n{design}\n\nGenerate the tasks now.")
    ])
    
    structured_llm = _llm.with_structured_output(TaskList)
    
    try:
        formatted = prompt.format_messages(design=state.final_design_doc)
        response = structured_llm.invoke(formatted)
        tasks = [task.model_dump() for task in response.tasks]
    except Exception as e:
        tasks = [{"title": "Parse Error", "description": f"Structured Output failed: {e}"}]
        
    return {"workflow_tasks": tasks}
