"""
Internal tools available to the Planning Agent.
These are simple Python callables exposed as LangChain tools.
"""
import json
from typing import List
from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# RAG Search Tool
# ---------------------------------------------------------------------------
# Lazily import to avoid circular imports at module load time
def _get_rag_pipeline():
    from agents.src.rag import RAGPipeline
    return RAGPipeline()


@tool
def rag_search(query: str, k: int = 5) -> str:
    """
    Search the internal knowledge base (Chroma DB + BM25) for past projects,
    PRDs, design documents, or uploaded PDFs that are relevant to the query.

    Returns a formatted string of the top-k most relevant document chunks.
    """
    pipeline = _get_rag_pipeline()
    results = pipeline.hybrid_search(query=query, k=k)
    if not results:
        return "No relevant documents found in the internal knowledge base."
    chunks = [
        f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
        for doc in results
    ]
    return "\n\n---\n\n".join(chunks)


# ---------------------------------------------------------------------------
# Structured Output Parser Tool
# ---------------------------------------------------------------------------

@tool
def parse_structured_output(raw_output: str) -> dict:
    """
    Extracts the structured JSON block from the planning agent's raw markdown output.
    Returns a dict with keys: complexity_level, project_type,
    recommended_tech_stack, risks, constraints.
    """
    try:
        start = raw_output.rfind("```json")
        end = raw_output.rfind("```", start + 1)
        if start == -1 or end == -1:
            return {"error": "No JSON block found in output."}
        json_str = raw_output[start + 7:end].strip()
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse failed: {str(e)}"}
