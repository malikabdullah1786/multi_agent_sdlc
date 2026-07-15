"""
Architect Agent — Node Functions
Flow:
  research → design_draft → validate_design → self_critique
  → [revision loop if issues] → approve_schema (interrupt)
  → approve_api (interrupt) → approve_structure (interrupt)
  → finalize_design
"""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt
from agents.src.agents.architect.state import ArchitectState
from agents.src.agents.architect.tools import rag_search, validate_schema, lint_api_spec
# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------
_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)  # Low temp for precise technical output
_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"
def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")
# ---------------------------------------------------------------------------
# 1. Research Node
#    Technical web search + RAG for past ADRs and design docs
# ---------------------------------------------------------------------------
def research_node(state: ArchitectState) -> dict:
    """
    Performs technical research via Tavily web search and internal RAG.
    Searches for best practices, library docs, and similar past architectures.
    """
    web_results: list[str] = []
    rag_results: list[str] = []
    # Web search for technical references
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        tavily = TavilySearchResults(max_results=5)
        tech_query = f"system architecture best practices {' '.join(state.recommended_tech_stack)} {state.project_type}"
        raw = tavily.invoke(tech_query)
        if isinstance(raw, list):
            web_results = [r.get("content", "") for r in raw if isinstance(r, dict)]
    except Exception as e:
        web_results = [f"Web search unavailable: {e}"]
    # Internal knowledge base search for past design docs and ADRs
    rag_raw = rag_search.invoke({
        "query": f"system design architecture {state.user_req}",
        "k": 5
    })
    rag_results = [rag_raw] if rag_raw else []
    return {
        "web_search_results": web_results,
        "rag_results": rag_results,
    }
# ---------------------------------------------------------------------------
# 2. Design Draft Node
#    Generates the full system design document
# ---------------------------------------------------------------------------
def design_draft_node(state: ArchitectState) -> dict:
    """
    Generates (or revises) the full System Design Document using the
    architect prompt template.
    """
    template_str = _load_prompt("architect.txt")
    prompt = PromptTemplate.from_template(template_str)
    formatted = prompt.format(
        user_req=state.user_req,
        prd_or_plan=state.prd or "No PRD available.",
        web_search_results="\n\n".join(state.web_search_results) or "No web results.",
        rag_results="\n\n".join(state.rag_results) or "No past designs found.",
        constraints="\n".join(f"- {c}" for c in state.constraints) or "None.",
        recommended_tech_stack=", ".join(state.recommended_tech_stack) or "Not specified.",
        schema_feedback=state.schema_feedback or "No schema feedback.",
        api_feedback=state.api_feedback or "No API feedback.",
        structure_feedback=state.structure_feedback or "No structure feedback.",
        self_critique=state.self_critique_notes or "No previous critique.",
    )
    response = _llm.invoke(formatted)
    return {
        "system_design_draft": response.content,
        "iteration_count": state.iteration_count + 1,
    }
# ---------------------------------------------------------------------------
# 3. Validate Design Node
#    Runs schema validator and API linter tools against the draft
# ---------------------------------------------------------------------------
def validate_design_node(state: ArchitectState) -> dict:
    """
    Extracts the schema and API sections from the draft and runs
    the schema validator and API linter tools against them.
    """
    draft = state.system_design_draft
    schema_notes = validate_schema.invoke({"schema_markdown": draft})
    api_notes = lint_api_spec.invoke({"api_markdown": draft})
    return {
        "schema_validation_notes": schema_notes,
        "api_validation_notes": api_notes,
    }
# ---------------------------------------------------------------------------
# 4. Self Critique Node
#    LLM evaluates its own design for completeness and accuracy
# ---------------------------------------------------------------------------
def self_critique_node(state: ArchitectState) -> dict:
    """
    Runs the LLM against a critique prompt to identify gaps in the design.
    Considers schema validation and API linting results.
    """
    critique_prompt = PromptTemplate.from_template(
        """You are a senior principal architect reviewing a junior architect's system design.
        
        User Requirement: {user_req}
        PRD Summary: {prd}
        
        System Design Draft:
        {draft}
        
        Schema Validation Notes: {schema_notes}
        API Linting Notes: {api_notes}
        
        Evaluate the design on these dimensions:
        1. Are ALL database tables fully defined with exact column types, PKs, FKs, and indexes?
        2. Are ALL required API endpoints listed with methods, paths, payloads, and response codes?
        3. Does the directory structure blueprint cover ALL files mentioned in the design?
        4. Are security strategies (auth, injection prevention) explicitly defined?
        5. Is the design consistent with the PRD requirements? Are any user stories left unaddressed?
        
        Be specific. Point out exactly what is missing or incomplete.
        If the design is complete and production-ready, respond with: DESIGN_COMPLETE
        """
    )
    response = _llm.invoke(critique_prompt.format(
        user_req=state.user_req,
        prd=state.prd[:3000] if state.prd else "Not available.",
        draft=state.system_design_draft,
        schema_notes=state.schema_validation_notes,
        api_notes=state.api_validation_notes,
    ))
    return {"self_critique_notes": response.content.strip()}
# ---------------------------------------------------------------------------
# 5. Section Approval Nodes (3 separate interrupts: Schema, API, Structure)
# ---------------------------------------------------------------------------
def approve_schema_node(state: ArchitectState) -> dict:
    """
    Interrupts the graph and presents ONLY the database schema section
    to the user for section-level review and approval.
    """
    user_response = interrupt({
        "type": "schema_approval",
        "section": "Database Schema",
        "draft": state.system_design_draft,
        "message": (
            "Please review the Database Schema section of the System Design. "
            "Approve it or provide specific feedback to revise this section."
        ),
    })
    if not user_response or str(user_response).strip().lower() in ("approve", "yes", "ok", ""):
        return {"schema_approved": True, "schema_feedback": ""}
    return {"schema_approved": False, "schema_feedback": str(user_response)}
def approve_api_node(state: ArchitectState) -> dict:
    """
    Interrupts the graph and presents ONLY the API endpoints section
    to the user for section-level review and approval.
    """
    user_response = interrupt({
        "type": "api_approval",
        "section": "API Endpoints",
        "draft": state.system_design_draft,
        "message": (
            "Please review the API Endpoints section of the System Design. "
            "Approve it or provide specific feedback to revise this section."
        ),
    })
    if not user_response or str(user_response).strip().lower() in ("approve", "yes", "ok", ""):
        return {"api_approved": True, "api_feedback": ""}
    return {"api_approved": False, "api_feedback": str(user_response)}
def approve_structure_node(state: ArchitectState) -> dict:
    """
    Interrupts the graph and presents ONLY the Directory Structure Blueprint
    to the user for section-level review and approval.
    """
    user_response = interrupt({
        "type": "structure_approval",
        "section": "Directory Structure",
        "draft": state.system_design_draft,
        "message": (
            "Please review the Directory Structure Blueprint section. "
            "Approve it or provide specific feedback to revise this section."
        ),
    })
    if not user_response or str(user_response).strip().lower() in ("approve", "yes", "ok", ""):
        return {"structure_approved": True, "structure_feedback": ""}
    return {"structure_approved": False, "structure_feedback": str(user_response)}
# ---------------------------------------------------------------------------
# 6. Finalize Design Node
# ---------------------------------------------------------------------------
def finalize_design_node(state: ArchitectState) -> dict:
    """
    All three sections are approved. Marks the draft as the final design document.
    """
    return {
        "final_design_doc": state.system_design_draft,
    }
