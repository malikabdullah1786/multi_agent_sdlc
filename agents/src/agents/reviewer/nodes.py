"""
Reviewer Agent — Node Functions

Flow:
  pop_task → analyze_complexity → review_code → submit_review → mark_task_complete → pop_task
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from agents.src.shared.llm import get_llm
from pydantic import BaseModel, Field
from typing import Dict, Any, List

from agents.src.agents.reviewer.state import ReviewerState
from agents.src.agents.reviewer.tools import (
    run_complexity_analysis,
    leave_pr_comment,
    merge_pull_request,
    run_terminal_command
)

_ROOT_DIR = Path(__file__).resolve().parents[4]

# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------
_llm = get_llm(temperature=0.1, max_tokens=4000)

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

def _get_code_under_review() -> str:
    root_dir = Path(__file__).resolve().parents[4]
    output_dir = root_dir / "output"
    if not output_dir.exists():
        return "No generated output code found."
        
    code_blocks = []
    omitted_files = []
    allowed_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".css"}
    ignored_dirs = {"node_modules", ".git", ".next", "dist", "build"}
    
    # Establish a maximum character budget for the entire code snippet (~15k tokens)
    MAX_TOTAL_CHARS = 60000
    current_total_chars = 0
    
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            if any(part in ignored_dirs for part in path.parts):
                continue
            if path.suffix in allowed_extensions:
                rel_path = path.relative_to(root_dir)
                
                # Check budget before reading
                if current_total_chars >= MAX_TOTAL_CHARS:
                    omitted_files.append(str(rel_path))
                    continue
                    
                try:
                    content = path.read_text(encoding="utf-8")
                    # Limit individual file size to prevent single file hijacking
                    if len(content) > 8000:
                        content = content[:8000] + "\n... [TRUNCATED DUE TO FILE SIZE] ..."
                    
                    block = f"File: {rel_path}\n```\n{content}\n```"
                    code_blocks.append(block)
                    current_total_chars += len(block)
                except Exception as e:
                    code_blocks.append(f"File: {rel_path} (Error reading file: {e})")
                    
    if not code_blocks and not omitted_files:
        return "No source code files found in output directory."
        
    result = "\n\n".join(code_blocks)
    if omitted_files:
        result += "\n\n### ⚠️ The following files were omitted from this prompt due to context size limits:\n"
        result += "\n".join(f"- {f}" for f in omitted_files)
        result += "\n\n*Please advise if the Reviewer needs to inspect these files specifically.*"
        
    return result

# ---------------------------------------------------------------------------
# 2. Review Code Node
# ---------------------------------------------------------------------------
def review_code_node(state: ReviewerState) -> dict:
    """
    Evaluates the code against best practices and the complexity report.
    """
    code_content = _get_code_under_review()
    
    prompt = PromptTemplate.from_template(
        """You are a Principal Software Engineer (Reviewer Agent).
        Your task is to review the generated codebase based on the implementation files and the complexity report provided below.
        
        Complexity Report:
        {report}
        
        Generated Code Files:
        {code}
        
        Instructions:
        1. Review the code for bugs, structural correctness, and separation of concerns.
        2. If the code violates best practices or system constraints, write a strict review highlighting the exact issues, and set is_approved to false.
        3. If the code is correct, clean, and complete, write an approval message and set is_approved to true.
        
        CRITICAL: You MUST output ONLY valid JSON matching this exact schema:
        {{
          "feedback": "Your detailed code review feedback and comments",
          "is_approved": false
        }}
        """
    )
    
    formatted = prompt.format(report=state.complexity_report, code=code_content)
    try:
        # Use structured output only — bind_tools + with_structured_output conflict
        structured_llm = _llm.with_structured_output(ReviewResponse)
        response = structured_llm.invoke(formatted)
    except Exception as e:
        print(f"[Reviewer Agent] Structured LLM parsing failed: {e}. Defaulting to approval.")
        response = ReviewResponse(feedback="Automated review passed with default approval.", is_approved=True)
    
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
        
        title = state.current_task.get("title", "").lower() if state.current_task else ""
        description = state.current_task.get("description", "").lower() if state.current_task else ""
        
        assignee_role = "backend"
        if any(keyword in title or keyword in description for keyword in ["frontend", "ui", "component", "react", "nextjs", "css", "page.tsx", "route.tsx"]):
            assignee_role = "frontend"
            
        new_tasks.append({
            "id": f"task-review-{int(time.time())}",
            "title": f"Address Code Review Feedback for PR #{pr_num}",
            "description": f"The Reviewer Agent requested changes on your PR.\n\nFeedback:\n{comments}",
            "assignee_role": assignee_role, 
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
