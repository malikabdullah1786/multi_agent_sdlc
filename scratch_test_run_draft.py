import asyncio
import json
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agents.src.agents.architect.graph import architect_subgraph

async def main():
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        bound_subgraph = architect_subgraph.builder.compile(checkpointer=checkpointer)
        thread_id = "56a7968d-1a44-48f0-bf70-c442f53cb15a-architect"
        config = {"configurable": {"thread_id": thread_id}}
        print("Starting astream(None)...")
        try:
            async for event in bound_subgraph.astream(None, config=config):
                print("Event received:", event)
                break
        except Exception as e:
            print("Error during astream:", e)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
