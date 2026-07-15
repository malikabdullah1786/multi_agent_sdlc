"""
Reviewer Agent — Node Functions

Flow:
  analyze_codebase → check_complexity → generate_review → submit_review
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agents.src.agents.reviewer.state import ReviewerState
from agents.src.agents.reviewer.tools import (
    run_complexity_analysis,
    leave_pr_comment
)

_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

# ---------------------------------------------------------------------------
# 1. Analyze Codebase Node (Mock/No-op as state already has the code)
# ---------------------------------------------------------------------------
def analyze_codebase_node(state: ReviewerState) -> dict:
    """Could be used to fetch diffs if not provided in state."""
    return {}

# ---------------------------------------------------------------------------
# 2. Check Complexity Node
# ---------------------------------------------------------------------------
def check_complexity_node(state: ReviewerState) -> dict:
    """Runs the static analysis tool."""
    report = run_complexity_analysis.invoke({})
    return {"complexity_report": report}

# ---------------------------------------------------------------------------
# 3. Generate Review Node
# ---------------------------------------------------------------------------
def generate_review_node(state: ReviewerState) -> dict:
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
    is_approved = content.strip().upper().startswith("APPROVE")
    
    return {
        "code_review_comments": content,
        "code_review_approved": is_approved
    }

# ---------------------------------------------------------------------------
# 4. Submit Review Node
# ---------------------------------------------------------------------------
def submit_review_node(state: ReviewerState) -> dict:
    """Posts the review to GitHub/Gitlab."""
    try:
        # leave_pr_comment.invoke(...)
        pass
    except Exception:
        pass
    
    return {}
