from pydantic import BaseModel, Field
from typing import List, Dict, Any

class ReviewerState(BaseModel):
    # ── Inputs from global state ──────────────────────────────────────────────
    backend_file_changes: List[Dict[str, Any]] = Field(default_factory=list, description="Backend code written")
    frontend_file_changes: List[Dict[str, Any]] = Field(default_factory=list, description="Frontend code written")
    
    # ── Internal State ─────────────────────────────────────────────────────────
    complexity_report: str = Field(default="", description="Output of static analysis tools")
    code_review_comments: str = Field(default="", description="Generated PR comments based on best practices")

    # ── Outputs ─────────────────────────────────────────────────────────────────
    code_review_approved: bool = Field(default=False, description="True if the code passes all standards")
