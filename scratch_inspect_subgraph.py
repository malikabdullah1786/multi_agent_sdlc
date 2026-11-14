import asyncio
import json
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agents.src.agents.architect.graph import architect_subgraph

async def main():
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        bound_subgraph = architect_subgraph.builder.compile(checkpointer=checkpointer)
        thread_id = "56a7968d-1a44-48f0-bf70-c442f53cb15a-architect"
        config = {"configurable": {"thread_id": thread_id}}
        sub_state = await bound_subgraph.aget_state(config)
        print("sub_state.next:", sub_state.next)
        print("sub_state.tasks:", len(sub_state.tasks) if sub_state.tasks else 0)
        if sub_state.tasks:
            for t in sub_state.tasks:
                print("Task:", t.name, "Interrupts:", getattr(t, "interrupts", None), "Error:", getattr(t, "error", None))
        val = sub_state.values or {}
        print("sub_state.values keys:", list(val.keys()))
        for k in ["system_design_draft", "schema_validation_notes", "api_validation_notes", "self_critique_notes"]:
            if k in val:
                print(f"Key {k} len: {len(str(val[k]))}")

asyncio.run(main())
