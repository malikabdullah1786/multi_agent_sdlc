# System Architecture  

## 1. Tech Stack
- **Frontend**: React 18 + TypeScript, Vite, TailwindCSS  
- **API**: Node.js 20, Express 4, TypeScript, JWT (HS256)  
- **DB**: PostgreSQL 15 (primary), optional read‑replica for scaling  
- **Cache / Rate‑Limit**: Redis 7 (in‑memory counters)  
- **Auth**: Refresh‑token flow, HttpOnly cookies  
- **CI/CD**: GitHub Actions, Docker, Kubernetes (stateless pods)  

## 2. Topology
- **Client (SPA)** → HTTPS → **Load Balancer (ALB)** → **API Service (stateless pods)**  
- API ↔ **Redis** (rate‑limit, session store)  
- API ↔ **PostgreSQL** (primary, sharded by `user_id` for >10 M tasks)  
- API ↔ **Object Store (S3)** – future attachments (not in MVP)  
- **Monitoring**: Prometheus + Grafana; **Logging**: Loki  

## 3. Database Schema
```yaml
tables:
  users:
    columns:
      id: uuid PK default gen_random_uuid()
      email: varchar(255) UNIQUE NOT NULL
      password_hash: varchar(255) NOT NULL
      created_at: timestamptz DEFAULT now()
      updated_at: timestamptz DEFAULT now()
    indexes:
      - email_unique
  refresh_tokens:
    columns:
      token: uuid PK
      user_id: uuid FK users.id ON DELETE CASCADE
      expires_at: timestamptz NOT NULL
      created_at: timestamptz DEFAULT now()
    indexes:
      - user_id_idx
  todos:
    columns:
      id: uuid PK default gen_random_uuid()
      user_id: uuid FK users.id ON DELETE CASCADE
      title: varchar(200) NOT NULL
      completed: boolean DEFAULT false
      created_at: timestamptz DEFAULT now()
      updated_at: timestamptz DEFAULT now()
    indexes:
      - user_id_idx
      - completed_idx
      - created_at_idx
```

## 4. API Contracts
### Auth
| Method | Path               | Req Body                     | Resp (200)                     | Errors |
|--------|--------------------|------------------------------|--------------------------------|--------|
| POST   | /auth/signup       | `{email,password}`           | `{accessToken,refreshToken}`   | 400,409 |
| POST   | /auth/login        | `{email,password}`           | `{accessToken,refreshToken}`   | 401 |
| POST   | /auth/refresh      | `{refreshToken}`             | `{accessToken}`                | 401 |
| POST   | /auth/logout       | `{refreshToken}`             | `{msg}`                        | 200 |

### Todos (JWT‑Bearer)
| Method | Path            | Req Body / Params                     | Resp (200)                     | Errors |
|--------|-----------------|---------------------------------------|--------------------------------|--------|
| GET    | /todos          | query:`?status=all|active|completed` | `[{id,title,completed,...}]`   | 401 |
| POST   | /todos          | `{title}`                             | `{id,...}`                     | 400,401 |
| PATCH  | /todos/:id      | `{title?,completed?}`                 | `{id,...}`                     | 400,401,404 |
| DELETE | /todos/:id      | –                                     | `{msg}`                        | 401,404 |

*All endpoints enforce `Rate-Limit: 60 req/min` via Redis token bucket.*

## 5. Directory Tree
```
/ (repo root)
├─ .github/
│  └─ workflows/
│     └─ ci.yml
├─ docker/
│  ├─ Dockerfile.api
│  └─ Dockerfile.frontend
├─ helm/
│  └─ chart/
│     ├─ Chart.yaml
│     └─ templates/
│        ├─ deployment.yaml
│        ├─ service.yaml
│        └─ ingress.yaml
├─ infra/
│  └─ terraform/
│     └─ main.tf
├─ src/
│  ├─ api/
│  │  ├─ src/
│  │  │  ├─ index.ts
│  │  │  ├─ routes/
│  │  │  │  ├─ auth.ts
│  │  │  │  └─ todos.ts
│  │  │  ├─ middleware/
│  │  │  │  ├─ auth.ts
│  │  │  │  └─ rateLimit.ts
│  │  │  └─ services/
│  │  │     ├─ userService.ts
│  │  │     └─ todoService.ts
│  │  ├─ tsconfig.json
│  │  └─ package.json
│  └─ web/
│     ├─ index.html
│     ├─ src/
│     │  ├─ main.tsx
│     │  ├─ App.tsx
│     │  ├─ components/
│     │  │  ├─ Home.tsx
│     │  │  ├─ TaskModal.tsx
│     │  │  └─ TaskItem.tsx
│     │  └─ hooks/
│     │     └─ useAuth.ts
│     ├─ vite.config.ts
│     ├─ tsconfig.json
│     └─ package.json
├─ prisma/
│  └─ schema.prisma
├─ scripts/
│  └─ db-migrate.sh
├─ .env.example
├─ jest.config.ts
└─ README.md
```

## 6. Security / Performance
- **JWT**: HttpOnly, SameSite=Strict cookie; short‑lived access token (1 h) + rotating refresh token stored server‑side (Redis).  
- **Input Sanitization**: `express-validator` + parameterized queries via Prisma; CSP header `default-src 'self'`.  
- **Rate Limiting**: Redis token‑bucket per `user_id`; 60 req/min enforced at API gateway.  
- **Caching**: `GET /todos` results cached per user for 30 s in Redis; cache invalidated on any write.  
- **DB Indexing**: `user_id` + `completed` composite index for filter queries; `created_at` index for pagination.  
- **Observability**: OpenTelemetry instrumentation on API; latency alerts if 95th‑pct >150 ms.