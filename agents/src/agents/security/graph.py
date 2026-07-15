"""
Security Agent — Subgraph Definition

Flow:
  START → run_sast → check_deps → analyze_vulnerabilities → enforce_security_gate → END
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.src.agents.security.state import SecurityState
from agents.src.agents.security.nodes import (
    run_sast_node,
    check_deps_node,
    analyze_vulnerabilities_node,
    enforce_security_gate_node
)

# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
workflow = StateGraph(SecurityState)

workflow.add_node("run_sast", run_sast_node)
workflow.add_node("check_deps", check_deps_node)
workflow.add_node("analyze_vulnerabilities", analyze_vulnerabilities_node)
workflow.add_node("enforce_security_gate", enforce_security_gate_node)

workflow.add_edge(START, "run_sast")
workflow.add_edge("run_sast", "check_deps")
workflow.add_edge("check_deps", "analyze_vulnerabilities")
workflow.add_edge("analyze_vulnerabilities", "enforce_security_gate")
workflow.add_edge("enforce_security_gate", END)

security_subgraph = workflow.compile(checkpointer=MemorySaver())
