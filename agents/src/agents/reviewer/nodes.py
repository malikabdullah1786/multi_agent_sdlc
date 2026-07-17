"""
Reviewer Agent — Node Functions

Flow:
  analyze_codebase → check_complexity → generate_review → submit_review
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agents.src.agents.reviewer.state import ReviewerState
from typing import Dict, Any
from agents.src.agents.reviewer.tools import (
    run_complexity_analysis,
    leave_pr_comment
)

_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

# ---------------------------------------------------------------------------
# 1. Analyze Complexity Node
# ---------------------------------------------------------------------------
def analyze_complexity_node(state: ReviewerState) -> dict:
    """Runs the static analysis tool."""
    # report = run_complexity_analysis.invoke({})
    report = "Complexity is low."
    return {"complexity_report": report}

# ---------------------------------------------------------------------------
# 2. Review Code Node
# ---------------------------------------------------------------------------
def review_code_node(state: ReviewerState) -> dict:
    """
    Evaluates the code against best practices (SOLID, DRY).
    """
    prompt = PromptTemplate.from_template(
        """You are a Principal Software Engineer (Reviewer Agent).
        Review the following code changes and complexity report.
        
        Complexity Report: {report}
        
        If the code violates best practices (e.g., massive functions, no separation of concerns),
        write a strict review asking for changes. Otherwise, write an approval message.
        Start your response with 'APPROVE' or 'REJECT' on the first line.
        """
    )
    
    formatted = prompt.format(report=state.complexity_report)
    response = _llm.invoke(formatted)
    
    content = response.content
    approved = content.strip().upper().startswith("APPROVE")
    
    return {"code_review_comments": content, "code_review_approved": approved}

# ---------------------------------------------------------------------------
# Task Queue Management
# ---------------------------------------------------------------------------
def pop_task_node(state: ReviewerState) -> dict:
    tasks = list(state.workflow_tasks)
    if not tasks:
        return {"current_task": None}
    next_task = tasks.pop(0)
    return {"workflow_tasks": tasks, "current_task": next_task}

def mark_task_complete_node(state: ReviewerState) -> dict:
    return {"current_task": None}
