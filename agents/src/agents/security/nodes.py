"""
Security Agent — Node Functions

Flow:
  pop_task → run_sast → check_deps → analyze_vulnerabilities → enforce_security_gate → mark_task_complete → pop_task
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from typing import Dict, Any, List

from agents.src.agents.security.state import SecurityState
from agents.src.agents.security.tools import (
    run_sast_scanner,
    check_dependencies,
    file_security_ticket
)

_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, max_tokens=4000)

class Vulnerability(BaseModel):
    title: str = Field(description="CVE or brief title of the vulnerability")
    severity: str = Field(description="Severity (CRITICAL, HIGH, MEDIUM, LOW)")
    mitigation: str = Field(description="How to fix this vulnerability")

class SecurityAnalysis(BaseModel):
    is_approved: bool = Field(description="True if NO critical/high vulns exist, False otherwise")
    report: str = Field(description="Brief summary report of findings")
    vulnerabilities: List[Vulnerability] = Field(description="Extracted high/critical vulnerabilities")

# ---------------------------------------------------------------------------
# 1. Run SAST Node
# ---------------------------------------------------------------------------
def run_sast_node(state: SecurityState) -> dict:
    """Runs static application security testing."""
    result = run_sast_scanner.invoke({})
    return {"sast_scan_results": result}

# ---------------------------------------------------------------------------
# 2. Check Dependencies Node
# ---------------------------------------------------------------------------
def check_deps_node(state: SecurityState) -> dict:
    """Runs software composition analysis (SCA)."""
    result = check_dependencies.invoke({})
    return {"dependency_vulnerabilities": result}

# ---------------------------------------------------------------------------
# 3. Analyze Vulnerabilities Node
# ---------------------------------------------------------------------------
def analyze_vulnerabilities_node(state: SecurityState) -> dict:
    """
    Evaluates the SAST and SCA reports using LLM structure.
    """
    prompt = PromptTemplate.from_template(
        """You are a Principal AppSec Engineer.
        Review the following security scans.
        
        SAST Report: {sast}
        Dependencies Report: {deps}
        
        If there are any CRITICAL or HIGH vulnerabilities, set is_approved to False and extract the vulnerabilities.
        Otherwise, set is_approved to True.
        """
    )
    
    formatted = prompt.format(
        sast=state.sast_scan_results,
        deps=state.dependency_vulnerabilities
    )
    
    structured_llm = _llm.with_structured_output(SecurityAnalysis)
    response = structured_llm.invoke(formatted)
    
    return {
        "security_report": response.report,
        "security_approved": response.is_approved,
        "internal_vulnerabilities": [v.dict() for v in response.vulnerabilities]
    }

# ---------------------------------------------------------------------------
# Task Queue Management
# ---------------------------------------------------------------------------
def pop_task_node(state: SecurityState) -> dict:
    tasks = list(state.workflow_tasks)
    if not tasks:
        return {"current_task": None}
    next_task = tasks.pop(0)
    return {"workflow_tasks": tasks, "current_task": next_task}

def mark_task_complete_node(state: SecurityState) -> dict:
    return {"current_task": None}

# ---------------------------------------------------------------------------
# 4. Enforce Security Gate Node
# ---------------------------------------------------------------------------
def enforce_security_gate_node(state: SecurityState) -> dict:
    """
    If rejected, files Jira security tickets and SPAWNS dynamic tasks for developers to fix.
    """
    new_tasks = []
    
    if not state.security_approved:
        import time
        vulns = state.get("internal_vulnerabilities", [])
        
        if not vulns:
            # Fallback if the LLM flagged but didn't extract specific items
            vulns = [{"title": "General Security Block", "severity": "HIGH", "mitigation": "Review SAST logs"}]
            
        for v in vulns:
            file_security_ticket.invoke({
                "cve_title": v.get("title", "Vuln"),
                "severity": v.get("severity", "HIGH"),
                "mitigation": v.get("mitigation", "Fix code")
            })
            
            # Spawn a new task for the orchestrator
            new_tasks.append({
                "id": f"task-sec-{int(time.time())}",
                "title": f"Fix Security Vulnerability: {v.get('title')}",
                "description": f"Security scan found a {v.get('severity')} vulnerability.\n\nMitigation:\n{v.get('mitigation')}",
                "assignee_role": "backend", # Usually backend handles sec fixes
                "dependencies": [],
                "priority": 1 # Security fixes are top priority
            })
            time.sleep(1)
            
    return {"new_workflow_tasks": new_tasks}
