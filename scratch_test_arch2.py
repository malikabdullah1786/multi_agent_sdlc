import asyncio
import json
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agents.src.orchestrator.graph import parent_workflow

async def main():
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        graph = parent_workflow.compile(checkpointer=checkpointer)
        with open(".active_session.json", "r") as f:
            session = json.load(f)
        thread_id = session["thread_id"]
        config = {"configurable": {"thread_id": thread_id}}
        state = await graph.aget_state(config)
        print("Next:", state.next)
        tasks = state.tasks
        print(f"Tasks: {len(tasks)}")
        for t in tasks:
            print("Task:", t.name, "Interrupts:", getattr(t, "interrupts", None), "State:", getattr(t, "state", None))

asyncio.run(main())
