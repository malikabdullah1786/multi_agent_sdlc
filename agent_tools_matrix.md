# Agent Tool Selection Matrix

To ensure our agents are capable but securely sandboxed, we need to carefully select their tools. This matrix defines exactly which **MCP Servers** (Model Context Protocol) and **Internal Python Tools** each agent gets.

## 1. Planners & Strategists
These agents do not write code. Their job is to gather information and output markdown/JSON to the state.

| Agent | MCP Tools | Internal Python Tools | Purpose |
|-------|-----------|-----------------------|---------|
| **Planning** | Web Search MCP (e.g., Brave or Tavily) | RAG Search (`RAGPipeline`) | Researching feasibility and querying internal knowledge base. |
| **Product Manager** | Web Search MCP | RAG Search (`RAGPipeline`) | Researching user personas, competitors, and internal docs. |
| **Architect** | None | RAG Search (`RAGPipeline`) | Querying internal architecture guidelines and ADRs. |
| **Task Breakdown** | None | None | Pure reasoning based on the Architect's design document. |

---

## 2. Core Builders
These agents write code. Their file access MUST be scoped to specific directories to prevent them from destroying each other's work.

| Agent | MCP Tools | Internal Python Tools | Scope/Restrictions |
|-------|-----------|-----------------------|--------------------|
| **Database Engineer** | Postgres MCP, Filesystem MCP | `run_alembic_migration` | Filesystem restricted to `backend/.../models/` and `alembic/`. Postgres MCP allows running exact SQL to verify tables. |
| **Backend Dev** | Filesystem MCP | `run_backend_linter` (ruff), `run_pytest` | Filesystem strictly scoped to `/backend`. |
| **Frontend Dev** | Filesystem MCP | `run_frontend_linter` (eslint), `run_jest` | Filesystem strictly scoped to `/frontend`. |

---

## 3. Validators & Enforcers
These agents verify the builders' work and require broad read access but restricted write access.

| Agent | MCP Tools | Internal Python Tools | Scope/Restrictions |
|-------|-----------|-----------------------|--------------------|
| **QA (Tester)** | Filesystem MCP | `run_test_suite` (Full access) | Filesystem: Read-only for `src/` folders. Read/Write for `/tests` folders. Needs command execution to run end-to-end tests. |
| **Reviewer** | GitHub MCP, Filesystem MCP | None | Filesystem: Read-only. GitHub MCP used to create Issues for unfixable bugs or escalate to human devs. |
| **Security** | None | `run_semgrep` or `run_bandit` | Filesystem: Read-only. Runs SAST (Static Application Security Testing) tools against the codebase. |

---

## 4. Deployment
The final agent that ships the code.

| Agent | MCP Tools | Internal Python Tools | Scope/Restrictions |
|-------|-----------|-----------------------|--------------------|
| **DevOps** | Docker MCP, GitHub MCP | `trigger_deployment` | Filesystem: Scoped to `/infra`, `Dockerfiles`, and `.github/workflows`. Uses Docker MCP to build images and verify containers. |

---

> [!IMPORTANT]
> **Open Questions for Review:**
> 1. Are you planning to use a standard MCP server for the filesystem (like the official `@modelcontextprotocol/server-filesystem`), or should we build custom internal Python file tools so we have tighter programmatic control over the scoping?
> 2. For the DevOps agent, do you deploy using Docker directly, or do you use a specific cloud provider (AWS, GCP, Vercel)? There are specific MCPs for those.
