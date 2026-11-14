import asyncio
import json
import sqlite3
import msgpack

conn = sqlite3.connect('checkpoints.sqlite')
c = conn.cursor()
c.execute("SELECT checkpoint FROM checkpoints WHERE thread_id LIKE '%architect%' ORDER BY rowid DESC LIMIT 1")
raw = c.fetchone()[0]
data = msgpack.unpackb(raw)
channels = data.get('channel_values', {})
print("Channels:", list(channels.keys()))

user_req = channels.get('user_req', '')
prd = channels.get('prd', '')
web_search_results = channels.get('web_search_results', [])
rag_results = channels.get('rag_results', [])
constraints = channels.get('constraints', [])

print(f"user_req len: {len(user_req)}")
print(f"prd len: {len(prd)}")
print(f"web_search_results count: {len(web_search_results)}")
print(f"rag_results count: {len(rag_results)}")

from agents.src.shared.llm import get_llm
from agents.src.shared.tools import rag_search
from agents.src.agents.architect.tools import validate_schema, lint_api_spec
from langchain_core.prompts import PromptTemplate
from pathlib import Path

prompts_dir = Path("agents/src/prompts")
template_str = (prompts_dir / "architect.txt").read_text(encoding="utf-8")
prompt = PromptTemplate.from_template(template_str)

matrix_path = Path("agent_tools_matrix.md")
team_capabilities = matrix_path.read_text(encoding="utf-8") if matrix_path.exists() else ""

formatted = prompt.format(
    user_req=user_req,
    prd_or_plan=(prd or "No PRD available.")[:6000],
    team_capabilities=team_capabilities[:2000],
    web_search_results=("\n\n".join(web_search_results) or "No web results.")[:2000],
    rag_results=("\n\n".join(rag_results) or "No past designs found.")[:2000],
    constraints="\n".join(f"- {c}" for c in constraints) or "None.",
    previous_draft="No previous draft.",
    schema_feedback="No schema feedback.",
    api_feedback="No API feedback.",
    structure_feedback="No structure feedback.",
    self_critique="No previous critique.",
)

print(f"Formatted prompt length: {len(formatted)} chars (~{len(formatted)//4} tokens)")

llm = get_llm(temperature=0.1, max_tokens=4000)
print(f"LLM type: {type(llm)}, model: {getattr(llm, 'model', None)}")
