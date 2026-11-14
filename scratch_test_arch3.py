import asyncio
import json
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agents.src.agents.architect.graph import architect_subgraph

async def main():
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        graph = architect_subgraph.compile(checkpointer=checkpointer)
        thread_id = "56a7968d-1a44-48f0-bf70-c442f53cb15a-architect"
        config = {"configurable": {"thread_id": thread_id}}
        state = await graph.aget_state(config)
        print("Subgraph Next:", state.next)
        print("Subgraph Tasks:", state.tasks)
        if state.tasks:
            for t in state.tasks:
                print("Task interrupts:", getattr(t, "interrupts", None))
        val = state.values or {}
        print("Keys in subgraph state:", list(val.keys()))
        for k in ["system_design_draft", "schema_validation_notes", "api_validation_notes", "self_critique_notes", "iteration_count"]:
            if k in val:
                v = val[k]
                print(f"{k}: {type(v)} len={len(str(v))}")

asyncio.run(main())
