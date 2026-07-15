"""
Product Manager Agent — MCP and Internal Tools

Phase A tools: Web search, RAG search
Phase B tools: Jira MCP (Epic + Ticket creation), Slack MCP (Channel creation + messaging)
"""
from langchain_core.tools import tool
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# RAG Search (Internal)
# ---------------------------------------------------------------------------

def _get_rag_pipeline():
    from agents.src.rag import RAGPipeline
    return RAGPipeline()


@tool
def rag_search(query: str, k: int = 5) -> str:
    """
    Search the internal knowledge base for past PRDs, personas, or domain docs.
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
# Jira Tools (via Jira MCP or direct Atlassian REST API)
# ---------------------------------------------------------------------------

@tool
def create_jira_epic(
    project_key: str,
    epic_name: str,
    description: str,
    priority: str = "High"
) -> dict:
    """
    Creates a Jira Epic for the approved project.

    Args:
        project_key: The Jira project key (e.g. 'PROJ').
        epic_name: Name of the Epic (e.g. 'User Authentication System').
        description: Full PRD summary to attach to the Epic.
        priority: 'Low', 'Medium', 'High', or 'Critical'.

    Returns:
        A dict with 'epic_key' and 'epic_url'.
    """
    # TODO: Replace with actual Jira MCP call or Atlassian REST API:
    # POST /rest/api/3/issue with issuetype: Epic
    raise NotImplementedError(
        "Connect Jira MCP server or implement Atlassian REST API client."
    )


@tool
def create_jira_tickets(
    project_key: str,
    epic_key: str,
    tasks: List[Dict[str, Any]]
) -> List[str]:
    """
    Creates individual Jira tickets (Stories or Tasks) from the Task Breakdown output.

    Args:
        project_key: The Jira project key.
        epic_key: The parent Epic key to link all tickets under.
        tasks: List of task dicts from the Task Breakdown Agent.
                Each dict must have: id, title, description, assigned_to, target_files.

    Returns:
        A list of created Jira ticket keys.
    """
    # TODO: Replace with actual Jira MCP call or Atlassian REST API:
    # POST /rest/api/3/issue with issuetype: Story | Task, parent: epic_key
    raise NotImplementedError(
        "Connect Jira MCP server or implement Atlassian REST API client."
    )


# ---------------------------------------------------------------------------
# Slack Tools (via Slack MCP or Slack Web API)
# ---------------------------------------------------------------------------

@tool
def create_slack_channel(channel_name: str) -> dict:
    """
    Creates a dedicated Slack channel for the project.

    Args:
        channel_name: Must be lowercase with hyphens (e.g. 'proj-uber-for-dogs').
                      Max 80 characters, no spaces.

    Returns:
        A dict with 'channel_id' and 'channel_name'.
    """
    # TODO: Replace with Slack MCP call or Slack Web API:
    # POST https://slack.com/api/conversations.create
    raise NotImplementedError(
        "Connect Slack MCP server or implement Slack Web API client."
    )


@tool
def post_slack_message(channel_id: str, message: str, blocks: List[Dict] = None) -> dict:
    """
    Posts a formatted message to a Slack channel.

    Args:
        channel_id: The Slack channel ID to post to.
        message: Plain text fallback message.
        blocks: Optional Slack Block Kit payload for rich formatting.

    Returns:
        A dict with 'message_ts' (message timestamp for threading).
    """
    # TODO: Replace with Slack MCP call or Slack Web API:
    # POST https://slack.com/api/chat.postMessage
    raise NotImplementedError(
        "Connect Slack MCP server or implement Slack Web API client."
    )
