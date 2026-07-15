"""
Planning Agent — Node Functions

Node execution order inside the subgraph:
  research → needs_clarification? → [interrupt for questions] →
  generate_draft → critique_draft → needs_revision? →
  [interrupt for user approval] → finalize

Each node returns a partial dict to update PlanningState.
"""
import json
import os
from pathlib import Path
from typing import Any

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from agents.src.agents.planning.state import PlanningState
from agents.src.agents.planning.tools import rag_search, parse_structured_output

# ---------------------------------------------------------------------------
# LLM setup  (swap model / provider to your preference)
# ---------------------------------------------------------------------------
_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

# ---------------------------------------------------------------------------
# Prompt loader helper
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Research Node
#    Runs web search (Tavily) + RAG search and stores results in state.
# ---------------------------------------------------------------------------

def research_node(state: PlanningState) -> dict:
    """
    Gather external web search results and internal RAG knowledge base results.
    Web search is performed via Tavily; RAG via the internal pipeline.
    """
    # --- RAG search ---
    rag_result = rag_search.invoke({"query": state.user_req, "k": 5})
    rag_results = [rag_result] if rag_result else []

    # --- Tavily web search (lazy import so missing key doesn't break other agents) ---
    web_results = []
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        tavily = TavilySearchResults(max_results=5)
        raw = tavily.invoke(state.user_req)
        if isinstance(raw, list):
            web_results = [r.get("content", "") for r in raw if isinstance(r, dict)]
        else:
            web_results = [str(raw)]
    except Exception as e:
        web_results = [f"Web search unavailable: {e}"]

    return {
        "web_search_results": web_results,
        "rag_results": rag_results,
    }


# ---------------------------------------------------------------------------
# 2. Clarification Node
#    Decides if follow-up questions are needed and interrupts the graph
#    to wait for the user's answers if so.
# ---------------------------------------------------------------------------

def clarification_node(state: PlanningState) -> dict:
    """
    Uses the LLM to decide if the requirement is ambiguous. If yes, raises
    an interrupt so the UI can present questions to the user.
    """
    # Skip if we already have answers
    if state.user_clarification_answers:
        return {}

    clarify_prompt = PromptTemplate.from_template(
        """You are a requirements analyst. Given the raw user requirement below, 
        list any clarifying questions that MUST be answered before writing a feasibility brief.
        Focus on: platform, users, constraints, deadline, budget, privacy/regulatory needs.
        
        If the requirement is already sufficiently clear, respond with: CLEAR
        
        User Requirement: {user_req}
        
        Respond with either "CLEAR" or a numbered list of questions."""
    )
    response = _llm.invoke(clarify_prompt.format(user_req=state.user_req))
    content = response.content.strip()

    if content.upper() == "CLEAR":
        return {"clarifying_questions": []}

    # Parse questions from numbered list
    questions = [
        line.strip().lstrip("0123456789. ")
        for line in content.split("\n")
        if line.strip() and line.strip()[0].isdigit()
    ]

    if questions:
        # Interrupt and wait for user input via the UI
        answers = interrupt({
            "type": "clarifying_questions",
            "questions": questions,
            "message": "The Planning Agent needs answers to these questions before proceeding.",
        })
        return {
            "clarifying_questions": questions,
            "user_clarification_answers": answers if isinstance(answers, str) else str(answers),
        }

    return {"clarifying_questions": []}


# ---------------------------------------------------------------------------
# 3. Generate Draft Node
#    Produces the full feasibility brief + embedded JSON block.
# ---------------------------------------------------------------------------

def generate_draft_node(state: PlanningState) -> dict:
    """
    Generates the first (or revised) draft of the feasibility brief using
    the full planning prompt template.
    """
    template_str = _load_prompt("planning.txt")
    prompt = PromptTemplate.from_template(template_str)

    formatted = prompt.format(
        user_req=state.user_req,
        web_search_results="\n\n".join(state.web_search_results) or "No web search results available.",
        rag_results="\n\n".join(state.rag_results) or "No internal knowledge base results found.",
        user_clarification_answers=state.user_clarification_answers or "No clarifications provided.",
        critique_notes=state.critique_notes or "No previous critique.",
        user_feedback=state.user_feedback or "No previous feedback.",
    )

    response = _llm.invoke(formatted)
    return {
        "plan_draft": response.content,
        "iteration_count": state.iteration_count + 1,
    }


# ---------------------------------------------------------------------------
# 4. Critique Node
#    Self-evaluates the draft and produces notes for revision.
# ---------------------------------------------------------------------------

def critique_node(state: PlanningState) -> dict:
    """
    Runs the LLM against the critique prompt to identify weaknesses in the draft.
    """
    template_str = _load_prompt("planning_critique.txt")
    prompt = PromptTemplate.from_template(template_str)

    response = _llm.invoke(
        prompt.format(user_req=state.user_req, plan_draft=state.plan_draft)
    )
    critique = response.content.strip()
    return {"critique_notes": critique}


# ---------------------------------------------------------------------------
# 5. User Approval Node
#    Presents the refined draft to the user via LangGraph interrupt().
#    Waits for the user to approve or provide feedback.
# ---------------------------------------------------------------------------

def user_approval_node(state: PlanningState) -> dict:
    """
    Pauses the graph and presents the draft to the human user via the UI.
    The user can either approve (returns empty string) or provide feedback.
    """
    user_response = interrupt({
        "type": "plan_approval",
        "draft": state.plan_draft,
        "message": (
            "The Planning Agent has produced a feasibility brief. "
            "Please review it and either approve or provide feedback for revision."
        ),
    })

    # If the user approves (empty response or explicit "approve"), mark as approved
    if not user_response or str(user_response).strip().lower() in ("approve", "yes", "ok", ""):
        return {"user_feedback": "", "is_approved": True}

    # Otherwise capture the feedback for the next revision loop
    return {"user_feedback": str(user_response), "is_approved": False}


# ---------------------------------------------------------------------------
# 6. Finalize Node
#    Parses the structured JSON from the approved draft and writes final outputs.
# ---------------------------------------------------------------------------

def finalize_node(state: PlanningState) -> dict:
    """
    Extracts the structured JSON block from the approved plan_draft and
    writes all fields to the final output slots in the state.
    """
    structured = parse_structured_output.invoke({"raw_output": state.plan_draft})

    return {
        "final_plan": state.plan_draft,
        "complexity_level": structured.get("complexity_level", "medium"),
        "project_type": structured.get("project_type", "other"),
        "recommended_tech_stack": structured.get("recommended_tech_stack", []),
        "risks": structured.get("risks", []),
        "constraints": structured.get("constraints", []),
        "is_approved": True,
    }
