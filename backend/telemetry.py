import datetime
import logging
from backend.websocket_manager import ws_manager

logger = logging.getLogger("telemetry")

# Context variable to hold active project_id across threads
import contextvars
CURRENT_PROJECT_ID: contextvars.ContextVar[str] = contextvars.ContextVar("CURRENT_PROJECT_ID", default="")

def set_active_project_id(project_id: str):
    """Sets the active project ID for the current thread execution context."""
    CURRENT_PROJECT_ID.set(str(project_id))

def get_active_project_id() -> str:
    """Gets the active project ID for the current thread execution context."""
    return CURRENT_PROJECT_ID.get()

def broadcast_tool_call(tool_name: str, details: str, event_type: str = "LOG_EMITTED", payload_extra: dict = None):
    """Broadcasts agent tool calls, file edits, web searches, and terminal commands live to the UI."""
    project_id = get_active_project_id()
    if not project_id:
        return

    now_str = str(datetime.datetime.utcnow())
    msg = f"🛠️ **Tool Call**: `{tool_name}` → {details[:150]}"

    # Always log tool call in Chat panel
    ws_manager.broadcast_sync(project_id, "LOG_EMITTED", {
        "agent_name": "tool_execution",
        "message": msg,
        "timestamp": now_str
    })

    # Extra panel specific broadcasts
    if event_type == "TERMINAL_COMMAND" and payload_extra:
        ws_manager.broadcast_sync(project_id, "TERMINAL_COMMAND", payload_extra)
    elif event_type == "FILE_CHANGE" and payload_extra:
        ws_manager.broadcast_sync(project_id, "FILE_CHANGE", payload_extra)

def broadcast_subgraph_node(sub_node: str, thread_id: str = ""):
    """Broadcasts internal subgraph node execution live to the visual React Flow graph in UI."""
    project_id = get_active_project_id()
    if not project_id:
        return

    ws_manager.broadcast_sync(project_id, "SUBGRAPH_NODE_CHANGED", {
        "sub_node": sub_node,
        "thread_id": thread_id
    })
    
    # Fire and forget DB update
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            async def _update_db():
                from backend.database import async_session_maker
                from backend.models import Workflow
                from sqlalchemy import update
                async with async_session_maker() as session:
                    await session.execute(
                        update(Workflow)
                        .where(Workflow.project_id == int(project_id))
                        .values(current_subgraph_node=sub_node)
                    )
                    await session.commit()
            loop.create_task(_update_db())
    except Exception:
        pass
