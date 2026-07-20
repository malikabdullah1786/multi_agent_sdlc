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
import re
from pathlib import Path
from typing import Any

from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langgraph.types import interrupt

from agents.src.agents.planning.state import PlanningState
from agents.src.agents.planning.tools import rag_search, parse_structured_output

# ---------------------------------------------------------------------------
# LLM setup  (swap model / provider to your preference)
# ---------------------------------------------------------------------------
_llm_draft = ChatGroq(
    model="qwen/qwen3.6-27b",
    temperature=0.7,
    max_tokens=4000  # Give as much as possible to the draft
)

_llm_critique = ChatGroq(
    model="qwen/qwen3.6-27b",
    temperature=0.7,
    max_tokens=2000  # Restrict critique to avoid blowing out 8000 TPM limit
)

# ---------------------------------------------------------------------------
# Prompt loader helper
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


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

    # --- DuckDuckGo web search (lazy import so missing package doesn't break other agents) ---
    web_results = []
    try:
        from langchain_community.tools import DuckDuckGoSearchResults
        ddg = DuckDuckGoSearchResults(max_results=5)
        raw = ddg.invoke(state.user_req)
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
    prompt_path = _PROMPTS_DIR / "planning_qa.txt"
    clarify_prompt = PromptTemplate.from_template(prompt_path.read_text(encoding="utf-8"))
    response = _llm_critique.invoke(clarify_prompt.format(
        user_req=state.user_req,
        qa_history=state.user_clarification_answers or "None"
    ))
    content = response.content.strip()

    # Strip out any <think>...</think> blocks from Qwen before checking for CLEAR
    clean_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

    if clean_content.upper() == "CLEAR":
        return {"clarifying_questions": []}

    # Pass the entire conversational response back to the user
    questions = [clean_content]
    
    if questions:
        # Interrupt and wait for user input via the UI
        answers = interrupt({
            "type": "clarifying_questions",
            "questions": questions,
            "message": "The Planning Agent needs answers to these questions before proceeding.",
        })
        answers_str = answers if isinstance(answers, str) else str(answers)
        new_history = f"Questions asked:\n" + "\n".join(f"- {q}" for q in questions) + f"\nUser answered:\n{answers_str}\n\n"
        accumulated_history = (state.user_clarification_answers + "\n" + new_history).strip()
        
        return {
            "clarifying_questions": questions,
            "user_clarification_answers": accumulated_history,
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

    response = _llm_draft.invoke(formatted)
    content = response.content
    clean_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
    return {
        "plan_draft": clean_content,
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

    response = _llm_critique.invoke(
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

    # Write the human-readable draft to a markdown file
    output_file = Path(__file__).resolve().parents[4] / "final_plan.md"
    output_file.write_text(state.plan_draft, encoding="utf-8")

    return {
        "final_plan": state.plan_draft,
        "complexity_level": structured.get("complexity_level", "medium"),
        "project_type": structured.get("project_type", "other"),

        "risks": structured.get("risks", []),
        "constraints": structured.get("constraints", []),
        "is_approved": True,
    }
