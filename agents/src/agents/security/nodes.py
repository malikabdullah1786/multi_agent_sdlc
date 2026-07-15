"""
Security Agent — Node Functions

Flow:
  run_sast → check_deps → analyze_vulnerabilities → enforce_security_gate
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agents.src.agents.security.state import SecurityState
from agents.src.agents.security.tools import (
    run_sast_scanner,
    check_dependencies,
    file_security_ticket
)

_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

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
    Evaluates the SAST and SCA reports. Determines if there are critical blockers.
    """
    prompt = PromptTemplate.from_template(
        """You are a Principal AppSec Engineer.
        Review the following security scans.
        
        SAST Report: {sast}
        Dependencies Report: {deps}
        
        If there are any CRITICAL or HIGH vulnerabilities, start your response with 'REJECT'.
        Otherwise, start your response with 'APPROVE'. 
        Provide a brief summary report of the findings.
        """
    )
    
    formatted = prompt.format(
        sast=state.sast_scan_results,
        deps=state.dependency_vulnerabilities
    )
    
    response = _llm.invoke(formatted)
    
    content = response.content
    is_approved = content.strip().upper().startswith("APPROVE")
    
    return {
        "security_report": content,
        "security_approved": is_approved
    }

# ---------------------------------------------------------------------------
# 4. Enforce Security Gate Node
# ---------------------------------------------------------------------------
def enforce_security_gate_node(state: SecurityState) -> dict:
    """
    If rejected, optionally files Jira security tickets.
    The orchestrator relies on the boolean flag to halt the pipeline.
    """
    if not state.security_approved:
        try:
            # mock filing a ticket
            file_security_ticket.invoke({
                "cve_title": "Pipeline blocked due to SAST findings",
                "severity": "HIGH",
                "mitigation": "Review the security report and fix the code."
            })
        except Exception:
            pass
            
    return {}
