
<think>
Here's a thinking process:

1.  **Analyze User Input & Context:**
   - **User Request:** "create design" (initially), then provided a PRD/Project Plan context in the prompt.
   - **Context Provided:** The prompt contains a detailed PRD for a "Personal/Professional Portfolio & Contact Website (v1.0 MVP)" with specific tech stack (Next.js, TypeScript, Tailwind, Vercel, React Hook Form, Zod, Resend), constraints (static/marketing site, contact form only, WCAG 2.1 AA, Lighthouse >= 90, serverless deployment), and detailed sections (Overview, Personas, User Stories, Functional Specs, Non-Functional, Out of Scope, Release Plan).
   - **Task:** Draft a comprehensive, production-ready System Design and Architecture document based on the PRD.
   - **Required Sections:**
     1. System & Interaction Topology
     2. Database Schema Specifications
     3. API Contracts & Endpoints
     4. Directory Structure Blueprint
     5. Security, Scalability, & Performance Design
   - **Format:** Structured, comprehensive Markdown. Highly detailed.

2.  **Deconstruct Requirements & Align with PRD:**
   - *Tech Stack:* Next.js (App Router), TypeScript, Tailwind CSS, Vercel, React Hook Form, Zod, Resend.
   - *Architecture Type:* Serverless/Static-first with edge/serverless functions for form handling. No traditional persistent database needed for v1 (static content + form submissions to email), but the prompt explicitly asks for "Database Schema Specifications" and "Database tables". I need to reconcile this. Since it's a portfolio site with a contact form, I'll design a lightweight PostgreSQL schema (via Vercel Postgres or similar) to store form submissions for reliability, audit trails, and future scalability, even though email is the primary delivery mechanism. This satisfies the prompt's requirement while staying true to the PRD's constraints.
   - *Data Flows:* Client (Next.js) -> Serverless API Route -> Zod Validation -> Rate Limiting -> DB Insert (optional but requested) -> Resend Email -> Response to Client.
   - *APIs:* RESTful endpoints for form submission, maybe a health check, and potentially a protected admin endpoint for viewing submissions (though out of scope for v1, I'll stick to the contact form endpoint as primary).
   - *Directory Structure:* Next.js App Router standard structure.
   - *Security/Scalability/Performance:* Serverless best practices, edge caching, rate limiting, input validation, CSP, HTTPS, connection pooling (if DB used), indexing.

3.  **Draft - Section by Section:**

   **1. System & Interaction Topology**
   - *Components:* Next.js Frontend (Static/SSR), Vercel Edge Network, Serverless API Routes, PostgreSQL (Vercel Postgres/Neon), Resend (Email Service), Redis/Upstash (Rate Limiting/Cache).
   - *Data Flow:* 
     1. User requests page -> Vercel Edge Cache serves static assets/SSR pages.
     2. User submits contact form -> Next.js API route (`/api/v1/contact`) receives POST.
     3. Zod validates payload -> Rate limiter checks IP/Email -> DB transaction inserts submission -> Resend sends email -> Success response.
   - *Communication:* REST over HTTPS. No WebSockets/PubSub needed for v1 (static site + form). I'll explicitly state why and keep it REST-only as per PRD constraints.

   **2. Database Schema Specifications**
   - Need SQL tables, columns, exact data types, PKs, FKs, indexes, constraints.
   - Table: `contact_submissions`
     - `id` UUID PRIMARY KEY DEFAULT gen_random_uuid()
     - `name` VARCHAR(150) NOT NULL
     - `email` VARCHAR(255) NOT NULL UNIQUE (or just NOT NULL, but I'll add a unique constraint for deduplication in short windows, or just index it)
     - `message` TEXT NOT NULL
     - `ip_address` INET
     - `user_agent` VARCHAR(500)
     - `status` VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed'))
     - `created_at` TIMESTAMPTZ DEFAULT NOW()
     - `updated_at` TIMESTAMPTZ DEFAULT NOW()
   - Indexes: `idx_contact_submissions_email`, `idx_contact_submissions_created_at`, `idx_contact_submissions_status`
   - Relationships: None needed for v1 (single table). I'll note that future modules (projects, blog) would use junction tables, but keep it focused.
   - I'll format this as raw SQL DDL for precision.

   **3. API Contracts & Endpoints**
   - Endpoint: `POST /api/v1/contact`
   - Query/Path params: None
   - Request Payload: `{ name: string, email: string, message: string }`
   - Response Payload: Success (201), Validation Error (400), Rate Limit (429), Server Error (500)
   - I'll detail the JSON schemas exactly as requested (Pydantic-like/JSON Schema style).
   - I'll also add a `GET /api/v1/health` for completeness.

   **4. Directory Structure Blueprint**
   - Next.js App Router structure:
     ```
     src/
     ├── app/
     │   ├── (marketing)/
     │   │   ├── page.tsx          # Home
     │   │   ├── about/page.tsx
     │   │   └── contact/page.tsx
     │   ├── api/
     │   │   └── v1/
     │   │       ├── contact/route.ts
     │   │       └── health/route.ts
     │   ├── layout.tsx
     │   └── globals.css
     ├── components/
     │   ├── ui/
     │   ├── layout/
     │   └── forms/
     ├── lib/
     │   ├── db.ts
     │   ├── resend.ts
     │   ├── rate-limit.ts
     │   └── validators.ts
     ├── types/
     ├── middleware.ts
     └── next.config.ts
     ```
   - I'll make it comprehensive and production-ready.

   **5. Security, Scalability, & Performance Design**
   - *Security:* Input validation (Zod), Rate limiting (Upstash Redis/Sliding window), CSRF protection (Next.js built-in + SameSite cookies), CSP headers, HTTPS enforcement, SQL parameterization (Prisma/Drizzle), Email sanitization.
   - *Scalability:* Serverless auto-scaling, Edge caching, Stateless API routes, Connection pooling (PgBouncer/Neon), Horizontal scaling via Vercel regions.
   - *Performance:* Static generation (SSG) for marketing pages, Image optimization (next/image), Font optimization, Tree-shaking, Lighthouse targets, DB indexing strategy, Caching strategies (stale-while-revalidate).

4.  **Self-Correction/Refinement during drafting:**
   - *Check against PRD:* The PRD says "contact form only", "static site", "serverless deployment". My design aligns perfectly. I'm adding a lightweight DB for form submissions as requested by the prompt's explicit requirement for "Database Schema Specifications". I'll clarify that it's optional but recommended for auditability, and the system works without it if needed, but I'll provide the full schema as requested.
   - *Check API format:* Must show HTTP method, path, params, request schema, response schema with status codes. I'll format it strictly.
   - *Check DB format:* Must show exact data types, PKs, FKs, indexes, constraints. I'll use standard PostgreSQL DDL.
   - *Check Topology:* Must describe data flows, component relationships, communication protocols. I'll detail the request lifecycle.
   - *Check Directory:* Must be a visual folder tree. I'll make it detailed.
   - *Check Security/Scalability/Performance:* Must cover threats, connection pooling, indexing, caching. I'll be explicit and technical.
   - *Tone/Format:* Principal Enterprise Systems Architect voice. Structured Markdown. Extreme detail.

   All constraints met. I will now generate the response. 
   Structure of output:
   # System Design & Architecture Document
   ## 1. System & Interaction Topology
   ## 2. Database Schema Specifications
   ## 3. API Contracts & Endpoints
   ## 4. Directory Structure Blueprint
   ## 5. Security, Scalability, & Performance Design
   (Detailed content follows)
   Ready.✅
   Output matches the final response. 
   *Self-Correction/Note during thought*: I need to ensure the API contract section explicitly matches the requested format. I'll use a table or structured list for clarity. I'll also make sure the DB schema uses exact SQL types as requested. I'll add connection pooling details (PgBouncer/Neon) and indexing strategies explicitly. I'll ensure the topology explains why WebSockets/PubSub are excluded (not needed for v1) but how they'd be integrated if scope expands. All good. Proceeds. 
   Output Generation. 
   [Done.] 
   *Output Generation* (matches the response)
   - System Topology: Clear diagram description, data flow steps, protocol choices.
   - DB Schema: PostgreSQL DDL with constraints, indexes, relationships noted.
   - API Contracts: Strict format with methods, paths, params, request/response schemas, status codes.
   - Directory: Comprehensive Next.js App Router tree.
   - Security/Scalability/Performance: Detailed strategies for each requirement.
   All aligned with PRD and prompt constraints.✅
</think>

# System Design & Architecture Document
**Project:** Personal/Professional Portfolio & Contact Website (v1.0 MVP)  
**Architecture Type:** Serverless-First, Static-Optimized, Edge-Cached  
**Tech Stack:** Next.js (App Router), TypeScript, Tailwind CSS, Vercel, PostgreSQL, Resend, Upstash Redis, Zod, React Hook Form  
**Document Version:** 1.0  
**Author:** Principal Enterprise Systems Architect  

---

## 1. System & Interaction Topology

### 1.1 Component Relationships & Data Flow
The architecture follows a **serverless, stateless API pattern** with edge-cached static assets. All stateful operations are isolated to isolated, ephemeral serverless functions to ensure zero cold-start overhead for marketing pages and predictable scaling for form submissions.

```
[Client Browser] 
       │ (HTTPS/REST)
       ▼
[Vercel Edge Network] ──┬── Serves static assets, fonts, CSS (Cache-Control: public, max-age=31536000)
       │                 └── Routes API requests to Serverless Functions
       ▼
[Next.js Serverless Functions] 
       │ (Zod Validation → Rate Limit Check → DB Insert → Email Dispatch)
       ▼
[PostgreSQL (Vercel/Neon)] ←── Stores contact submissions for audit & future CRM sync
       │
       ▼
[Resend API] ←── Handles transactional email delivery via SMTP/API
       │
       ▼
[Upstash Redis] ←── Sliding-window rate limiting & IP thrott