# System Architecture

## 1. Tech Stack
- **Frontend**: React + TypeScript + Tailwind CSS + Vite
- **Backend**: Python 3.11 + FastAPI + Pydantic (v2)
- **Database**: PostgreSQL 15
- **Migration**: Alembic
- **Communication**: REST / JSON

## 2. Topology
- **Client (Browser)** $\xrightarrow{\text{HTTPS/JSON}}$ **FastAPI Server**
- **FastAPI Server** $\xrightarrow{\text{SQLAlchemy/psycopg2}}$ **PostgreSQL**
- **State Management**: React Context + Optimistic UI updates (Client-side)

## 3. Database Schema
```yaml
tables:
  tasks:
    columns:
      id: { type: UUID, primary_key: true, default: gen_random_uuid() }
      workspace_id: { type: UUID, nullable: false, index: true } # Isolation for non-auth users
      text: { type: VARCHAR(256), nullable: false }
      is_completed: { type: BOOLEAN, default: false, index: true }
      created_at: { type: TIMESTAMP, default: now(), index: true }
      updated_at: { type: TIMESTAMP, default: now(), on_update: now(), index: true }
    indexes:
      - [workspace_id, updated_at]
      - [is_completed]
```

## 4. API Contracts
**Base URL**: `/api/v1`
**Header**: `X-Workspace-ID: <UUID>` (Required for data isolation)

| Method | Endpoint | Payload | Response | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/tasks` | N/A | `Task[]` | Fetch all tasks for workspace |
| `POST` | `/tasks` | `{text: str}` | `Task` | Create task (Validate $\le 256$ chars) |
| `PATCH` | `/tasks/{id}` | `{text?: str, is_completed?: bool}` | `Task` | Update single task |
| `PATCH` | `/tasks/bulk` | `{ids: UUID[], is_completed: bool}` | `Task[]` | Bulk toggle completion |
| `DELETE` | `/tasks/{id}` | N/A | `204 No Content` | Remove task |

## 5. Directory Tree
```text
.
├── pyproject.toml
├── alembic.ini
├── .env
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── requirements.txt
│   ├── alembic/                # Migration scripts
│   │   └── versions/
│   └── src/
│       ├── api/
│       │   ├── routes.py       # Endpoint definitions
│       │   └── dependencies.py # Workspace-ID validation
│       ├── core/
│       │   ├── config.py       # Env vars & settings
│       │   └── security.py     # Input sanitization
│       ├── models/
│       │   └── task.py          # SQLAlchemy models
│       └── schemas/
│           └── task.py          # Pydantic Zod-equivalent schemas
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── components/
        │   ├── TaskInput.tsx
        │   ├── TaskList.tsx
        │   └── TaskItem.tsx
        ├── hooks/
        │   └── useTasks.ts     # Optimistic UI logic
        └── types/
            └── index.ts         # Shared TS interfaces
```

## 6. Security/Perf
- **Data Isolation**: Mandatory `X-Workspace-ID` header used in all SQL `WHERE` clauses to prevent cross-tenant data leakage in the absence of Auth.
- **Injection Prevention**: Use of SQLAlchemy ORM (parameterized queries) to eliminate SQL injection; Pydantic strict typing for input validation.
- **Latency Optimization**: 
    - **Frontend**: Optimistic UI updates (update local state before API confirmation).
    - **Backend**: Indexing on `(workspace_id, updated_at)` to ensure $O(\log n)$ retrieval for task lists.
- **XSS Mitigation**: React's automatic escaping of JSX content + strict `VARCHAR(256)` limit on backend to prevent large payload attacks.