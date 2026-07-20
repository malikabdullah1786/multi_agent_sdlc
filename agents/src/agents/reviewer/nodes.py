"""
Reviewer Agent — Node Functions

Flow:
  pop_task → analyze_complexity → review_code → submit_review → mark_task_complete → pop_task
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import Dict, Any, List

from agents.src.agents.reviewer.state import ReviewerState
from agents.src.agents.reviewer.tools import (
    run_complexity_analysis,
    leave_pr_comment,
    merge_pull_request
)

_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, max_tokens=4000)

class ReviewResponse(BaseModel):
    is_approved: bool = Field(description="True if the code passes all standards, False if it needs changes")
    feedback: str = Field(description="Detailed code review comments or approval message")

# ---------------------------------------------------------------------------
# 1. Analyze Complexity Node
# ---------------------------------------------------------------------------
def analyze_complexity_node(state: ReviewerState) -> dict:
    """Runs the static analysis tool."""
    report = run_complexity_analysis.invoke({})
    return {"complexity_report": report}

# ---------------------------------------------------------------------------
# 2. Review Code Node
# ---------------------------------------------------------------------------
def review_code_node(state: ReviewerState) -> dict:
    """
    Evaluates the code against best practices and the complexity report.
    """
    prompt = PromptTemplate.from_template(
        """You are a Principal Software Engineer (Reviewer Agent).
        Review the project based on the following complexity report.
        
        Complexity Report:
        {report}
        
        If the code violates best practices (e.g., massive functions, no separation of concerns),
        write a strict review asking for changes and set is_approved to false. 
        Otherwise, write an approval message and set is_approved to true.
        """
    )
    
    formatted = prompt.format(report=state.complexity_report)
    structured_llm = _llm.with_structured_output(ReviewResponse)
    response = structured_llm.invoke(formatted)
    
    return {
        "code_review_comments": response.feedback,
        "code_review_approved": response.is_approved
    }

# ---------------------------------------------------------------------------
# 3. Submit Review Node
# ---------------------------------------------------------------------------
def submit_review_node(state: ReviewerState) -> dict:
    """
    Submits the review via GitHub API. 
    If rejected, dynamically spawns a new task for the developer.
    If approved, merges the PR.
    """
    repo = state.github_repo_name
    pr_num = state.active_pr_number
    comments = state.code_review_comments
    is_approved = state.code_review_approved
    
    # 1. Leave the comment
    leave_pr_comment.invoke({
        "github_repo_name": repo,
        "pr_number": pr_num,
        "comment_body": comments,
        "is_approved": is_approved
    })
    
    new_tasks = []
    if is_approved:
        # Merge the PR
        merge_pull_request.invoke({
            "github_repo_name": repo,
            "pr_number": pr_num,
            "commit_message": comments
        })
    else:
        # SPAWN A NEW TASK FOR THE FEEDBACK LOOP
        import time
        new_tasks.append({
            "id": f"task-review-{int(time.time())}",
            "title": f"Address Code Review Feedback for PR #{pr_num}",
            "description": f"The Reviewer Agent requested changes on your PR.\n\nFeedback:\n{comments}",
            # Assign it back to whoever created the PR. 
            # We assume 'backend' for now, but a more robust system would track the PR author.
            "assignee_role": "backend", 
            "dependencies": [],
            "priority": 1 # High priority to fix immediately
        })
        
    return {"new_workflow_tasks": new_tasks}

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
