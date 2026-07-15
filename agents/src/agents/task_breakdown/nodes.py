"""
Task Breakdown Agent — Node Functions

Flow:
  generate_tasks
"""
import json
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agents.src.agents.task_breakdown.state import TaskBreakdownState

_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

# ---------------------------------------------------------------------------
# 1. Generate Tasks Node
# ---------------------------------------------------------------------------
def generate_tasks_node(state: TaskBreakdownState) -> dict:
    """
    Reads the PRD and Architecture Doc, and breaks the project into granular JSON tasks.
    These tasks will be consumed by the Backend and Frontend Developer agents.
    """
    prompt = PromptTemplate.from_template(
        """You are the Task Breakdown Agent (Scrum Master).
        Read the PRD and Design Document, and break the project into granular tasks.
        Each task must have a title, description, assignee_role (backend/frontend), and dependencies.
        
        PRD: {prd}
        Design: {design}
        
        Respond with ONLY a raw JSON array of objects.
        """
    )
    
    formatted = prompt.format(prd=state.prd, design=state.final_design_doc)
    
    response = _llm.invoke(formatted)
    
    try:
        # Assuming the LLM returns a raw JSON array
        tasks = json.loads(response.content)
    except json.JSONDecodeError:
        tasks = [{"title": "Parse Error", "description": "LLM failed to output JSON"}]
        
    return {"workflow_tasks": tasks}
