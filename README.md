# ✦ Aria Agent Platform

One reusable AI agent platform for many businesses. A single FastAPI backend
and a single React widget serve every tenant -- what a visitor sees, what
the agent can do, and how leads are captured is entirely determined by a
public `agent_token`, resolved server-side to a configuration row in the
database. Adding a new business (a dental clinic, a second jewellery
brand, anything) never requires new frontend code or a new deployment --
only a new row in the `agents` table and a token.

This platform evolved from an earlier single-tenant astrology consultation
agent; the astrology use case is now just one of three sample agents
(Kaur Jewellery, Astrology, Real Estate) running on the shared platform.

Each agent can also have its own **isolated knowledge base**: upload
policies/FAQs/product docs (PDF, DOCX, TXT, CSV, JSON, Markdown), a
background worker extracts/chunks/embeds them into Postgres+pgvector, and
the agent's assistant retrieves relevant chunks on demand -- never another
agent's.

Each agent can also independently choose its own **AI provider and
model** -- Ollama (local, free, default), Groq, OpenAI, OpenRouter, Azure
OpenAI, or any custom OpenAI-compatible endpoint -- configured and tested
entirely from the admin dashboard, with API keys encrypted at rest and
never exposed to the frontend, the widget, or any public API response. Two
agents can run on completely different providers at the same time, and an
admin can switch an agent's provider without a code deployment. See
[How AI providers work](#how-ai-providers-work).

---

## Contents

- [Core concept](#core-concept)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Project structure](#project-structure)
- [Database design](#database-design)
- [How agents are resolved](#how-agents-are-resolved)
- [How tokens work](#how-tokens-work)
- [How tools are isolated](#how-tools-are-isolated)
- [How AI providers work](#how-ai-providers-work)
- [How sessions work](#how-sessions-work)
- [How the knowledge base (RAG) works](#how-the-knowledge-base-rag-works)
- [Example RAG conversation](#example-rag-conversation)
- [Embedding the React widget](#embedding-the-react-widget)
- [WordPress integration](#wordpress-integration)
- [Adding a new agent](#adding-a-new-agent)
- [Adding a new tool](#adding-a-new-tool)
- [Adding a new AI provider](#adding-a-new-ai-provider)
- [Rotating (or disabling) a token](#rotating-or-disabling-a-token)
- [Testing](#testing)
- [Troubleshooting: the agent says success but no lead appears](#troubleshooting-the-agent-says-success-but-no-lead-appears)
- [Design decisions \& known limitations](#design-decisions--known-limitations)
- [Production deployment notes](#production-deployment-notes)

---

## Core concept

```
AgentPlatform
     |
     +--- AgentConfiguration   (prompt, branding, model, tools, lead fields)
     +--- ToolRegistry         (business-specific + common tools)
     +--- SessionManager       (persistent, agent-scoped)
     +--- LangGraph            (one generic graph, every agent)
     +--- LLMFactory           (per-agent model/temperature)
     +--- LeadManager          (generic lead + optional consultation records)
```

There is no `JewelleryAgent` / `AstrologyAgent` / `RealEstateAgent` class
hierarchy. Configuration determines behavior; the code is the same for
every tenant.

---

## Architecture

```
 Website (any domain)
    |
    v
 React AI Widget  (aria-widget.js, bundled, no React needed on host site)
    |
    | { agent_token, session_id, message }
    v
 FastAPI API Gateway  (POST /api/chat)
    |
    v
 Token Validation  ->  Agent Resolver  ->  Domain check  ->  Rate limit
    |
    +-------------------------+
    |                         |
    v                         v
 Agent Configuration     Session Manager
    |                         |
    +------------+------------+
                 |
                 v
              LangGraph:  assistant  <-->  tools  -->  END
                 |                  |
                 v                  v
              Ollama            Business-specific tools + search_knowledge_base
              (per-agent          (only the ones this agent is permitted)
               model/temp)              |
                                         v
                                KnowledgeRetriever
                             (tenant_id + agent_id +
                              knowledge_base_id filter,
                              ALWAYS applied before the
                              vector similarity search)
                                         |
                                         v
                              PostgreSQL + pgvector
                                         |
                              +----------+-----------+-------------+
                              |          |            |             |
                              v          v            v             v
                          Sessions   Leads   Consultations   document_chunks
                                                                    ^
                                                                    |
                                                            Knowledge Worker
                                                         (separate process, polls
                                                          knowledge_jobs; extract ->
                                                          clean -> chunk -> embed -> store)
                                                                    ^
                                                                    |
                                                        POST /api/knowledge/upload
                                                                    ^
                                                                    |
                                                          Admin Dashboard
                                                        (Agents / Tools / Knowledge
                                                         Base / Sessions / Leads / ...)
```

Document upload never blocks on processing: `POST /api/knowledge/upload`
validates the file, stores it, and enqueues a `knowledge_jobs` row, then
returns immediately. The knowledge worker -- a separate process, not part
of the chat/API request path -- polls that queue and does the actual
extract/chunk/embed/store work. The chat request path never touches
ingestion at all; it only ever *reads* already-embedded chunks through
`KnowledgeRetriever`.

---

## Quick start

The knowledge base feature needs Postgres + the `pgvector` extension
(SQLite can't do vector similarity search), so Docker Compose is the
easiest way to get everything running together.

### Windows

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/),
[Ollama](https://ollama.com/download), and Node 18+, then double-click
**`run.bat`**. It checks prerequisites, pulls the chat and embedding
models if missing, starts Postgres+pgvector/backend/worker via
`docker compose up -d --build`, and starts the admin dashboard locally via
`npm run dev`.

### macOS / Linux

```bash
./run.sh
```

Same as `run.bat`: Docker Compose for Postgres/backend/worker, admin
dashboard runs locally with hot reload, logs in `.run-logs/`.

### Manual (Docker Compose directly)

```bash
cp .env.example .env                       # Postgres creds + Ollama host for compose
cp backend/.env.example backend/.env       # app settings
docker compose up -d --build               # postgres + backend + worker

cd frontend
npm install
cp .env.example .env
npm run dev
```

Open **http://localhost:5174** for the admin dashboard (sign in with
`ADMIN_USERNAME`/`ADMIN_PASSWORD` from `backend/.env`, default
`admin`/`changeme123`). The three sample agents' public tokens are logged
by the backend container on first startup:

```bash
docker compose logs backend | grep "Seeded token"
```

### Local Postgres without Docker

If you'd rather not use Docker: install Postgres 16 with the `pgvector`
extension available (e.g. `apt install postgresql-16 postgresql-16-pgvector`
on Debian/Ubuntu), create a database, then run the backend/worker directly:

```bash
# one-time setup
sudo -u postgres psql -c "CREATE DATABASE agent_platform;"
sudo -u postgres psql -d agent_platform -c "CREATE EXTENSION vector;"

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # point DATABASE_URL at your local Postgres
uvicorn app.main:app --reload --port 8000

# second terminal
cd backend && source .venv/bin/activate
python ../worker/knowledge_worker.py
```

### Building the embeddable widget

The widget is a build artifact, not a dev server, so it's a separate step:

```bash
cd widget
npm install
npm run build
```

Output: `widget/dist/aria-widget.js` -- one self-contained script, no
separate CSS file (see [Embedding the React widget](#embedding-the-react-widget)
for why).

---

## Project structure

```
agent-platform/
├── backend/
│   └── app/
│       ├── main.py                 # FastAPI app, split CORS, startup, health
│       ├── config.py
│       ├── api/                    # chat, sessions, admin_agents, admin_tools,
│       │                           # admin_sessions, admin_customers, leads,
│       │                           # admin_auth, knowledge
│       ├── agents/                 # registry, resolver, factory, state, graph
│       ├── tools/                  # registry, common, jewellery, astrology,
│       │                           # realestate, knowledge (search_knowledge_base)
│       ├── rag/
│       │   ├── ingestion/
│       │   │   ├── service.py      # load -> chunk -> embed -> store pipeline
│       │   │   └── loaders/        # base, pdf, docx, text, markdown, csv, json
│       │   ├── embeddings/service.py   # Ollama + deterministic-test-double
│       │   ├── retrieval/retriever.py  # tenant/agent/kb-filtered vector search
│       │   ├── chunking/splitter.py    # configurable, dependency-free
│       │   └── knowledge_base_service.py
│       ├── services/               # astrology/product/property, customer, lead, session
│       ├── models/                 # agent, tool, customer, session, message, lead,
│       │                           # consultation, knowledge_base, document,
│       │                           # document_chunk, knowledge_job
│       ├── security/               # tokens, rate_limit, domains, file_storage
│       └── seed.py                 # seeds tool catalog + 3 sample agents
│   ├── tests/                      # 107 tests (run against real Postgres+pgvector)
│   └── Dockerfile is at the repo root (shared by api + worker, see below)
│
├── worker/
│   └── knowledge_worker.py         # standalone process, polls knowledge_jobs
│
├── frontend/                       # Admin dashboard (Agents, Tools, Knowledge Base,
│   └── src/                        # Sessions, Customers, Leads, Analytics, Settings)
│       └── components/knowledge/   # KnowledgeBase, DocumentUpload, DocumentList,
│                                   # ProcessingStatus
│
├── widget/                         # Standalone embeddable widget (Vite lib build)
│   └── src/
│       ├── AriaChatWidget.tsx
│       ├── components/             # AriaHeader, AriaAvatar, AriaMessage, AriaSuggestions,
│       │                           # AriaInput, AriaLauncher, TypingIndicator, ProductCard,
│       │                           # LeadCapture
│       ├── useAriaChat.ts
│       ├── api.ts
│       └── index.tsx               # window.AriaWidget.mount / mountFloating
│
├── wordpress/kaur-ai-agent/        # WordPress plugin (PHP + built widget asset)
├── examples/                       # Sample documents for the jewellery/real-estate
│                                   # agents, ready to upload to the Knowledge Base
│
├── Dockerfile                      # one image, used for both the api and worker services
├── docker-compose.yml              # postgres (pgvector) + backend + worker
├── run.bat / run.sh
└── .env.example (repo root, + per sub-project)
```

---

## Database design

| Table              | Purpose |
|--------------------|---------|
| `agents`           | One row per tenant: branding, prompt, `public_token_hash`, `allowed_domains`, `suggestions`, `lead_fields`, `theme`, `tenant_id`, `model`/`temperature`/`max_tokens` (overrides), `provider_id`/`fallback_provider_id` |
| `ai_providers`     | Admin-configured AI backends (Ollama/Groq/OpenAI/...); `encrypted_api_key` only, never plaintext at rest |
| `tools`            | Catalog of every tool the platform knows how to build |
| `agent_tools`      | Join table: which tools each agent is permitted to use |
| `customers`        | A real person, matched globally by email/phone |
| `sessions`         | One conversation, **scoped to exactly one agent** |
| `messages`         | Every user/assistant message, persisted immediately |
| `leads`            | Generic lead record; business-specific fields live in `metadata_json` |
| `consultations`    | Optional, agent-specific structured record (used by the astrology agent) |
| `knowledge_bases`  | One (today) per agent; `tenant_id` + `agent_id` scoped |
| `documents`        | One uploaded file; status `PENDING`/`PROCESSING`/`READY`/`FAILED` |
| `document_chunks`  | Embedded chunks -- the table vector search actually queries, pgvector `Vector` column |
| `knowledge_jobs`   | The ingestion job queue the worker polls; status `PENDING`/`RUNNING`/`COMPLETED`/`FAILED` |

The platform runs on **Postgres + the `pgvector` extension** (not SQLite --
knowledge-base vector similarity search needs it). `DATABASE_URL` is still
just a SQLAlchemy URL; nothing in the app talks to psycopg directly.

---

## How agents are resolved

Every request to `/api/chat` or `POST /api/session` carries an
`agent_token`. `app/agents/resolver.py::resolve_agent` is the single choke
point every one of those requests passes through:

1. Hash the incoming token (`app/security/tokens.py::hash_token`, HMAC-SHA256
   keyed by `TOKEN_HASH_SECRET`).
2. Look up an `Agent` row by `public_token_hash`. No match -> `401`.
3. Check `agent.enabled`. Disabled -> `403`.
4. If the request has an `Origin`/`Referer` header, check it against
   `agent.allowed_domains` (`app/security/domains.py`). Empty list = no
   restriction. Mismatch -> `403`.
5. Return the resolved `Agent` row.

Everything downstream -- system prompt, branding, model, allowed tools --
comes from that one row. The widget and the backend never hardcode which
business they're serving.

---

## How tokens work

The token embedded in a website's widget snippet is **public by design**
(anyone can view page source). It identifies *which agent* to load; it is
not a secret credential and must never be treated like one.

- **Generation**: `secrets.token_urlsafe(32)`, prefixed `pub_`.
- **Storage**: only an HMAC-SHA256 hash (`TOKEN_HASH_SECRET`-keyed) is ever
  written to the database. A leaked DB dump cannot be used to derive a
  working token.
- **Verification**: hash the incoming token, look up by hash, compare.
- **What it does *not* protect**: database credentials, the Ollama
  connection, admin credentials, or any third-party secret key -- none of
  those are ever reachable from a public token.
- **Rotation**: generates a brand-new token, overwrites the stored hash;
  the old token stops working immediately (see
  [Rotating a token](#rotating-or-disabling-a-token)).

---

## How tools are isolated

This is the platform's core security property: **an agent must never
execute a tool outside its permissions**, enforced structurally rather than
by convention.

1. `agent_tools` (DB) records which `tool_key`s an agent is granted.
2. Per request, `app/agents/registry.py::get_allowed_tool_keys` reads
   exactly that list.
3. `app/tools/registry.py::build_tools_for_agent` builds **only** those
   tools (as real `StructuredTool` objects) and hands them to
   `llm.bind_tools(...)`.
4. The LLM is never bound any tool outside that list -- there is no code
   path where it *could* call `calculate_birth_chart` while serving the
   Kaur Jewellery agent, because that tool object was never constructed or
   passed to it for that request.
5. Every write-capable tool (`create_lead`, `create_jewellery_lead`,
   `create_astrology_consultation`, ...) also independently validates its
   own inputs and only ever touches rows scoped to the current
   `agent_id`/`session_id` -- the LLM never executes raw DB operations.
6. `search_knowledge_base` (the RAG tool) is isolated the same way, plus
   its own additional layer: see
   [How the knowledge base (RAG) works](#how-the-knowledge-base-rag-works)
   for why knowledge isolation holds even independent of tool permissions.

`backend/tests/test_tool_isolation.py` asserts this directly, including
"Agent A's permission list never yields Agent B's tools" and "an unknown
tool_key is silently ignored rather than crashing." The equivalent test
for knowledge specifically (`test_retrieval_isolation.py::test_CRITICAL_*`)
runs against a real Postgres+pgvector database, not a mock.

---

## How LangGraph orchestrates agent decisions

LangGraph is not a thin wrapper around `llm.bind_tools()` here -- it is the
authorization and execution layer every tool call passes through,
regardless of which provider produced it. `app/agents/graph.py::build_graph`
compiles one reusable `StateGraph` (the same graph for every agent -- see
"do not hard-code business logic into the graph" below) with these nodes:

```
START -> load_context -> agent_decision -+-> respond -> END
                              ^           |
                              |           +-> validate_action -> permission_check
                              |                                       |
                              |                                  execute_tool  (runs allowed
                              |                                       |          actions; denied
                              |                                  process_result  ones never reach
                              |                                       |          the tool function,
                              |                        +--------------+          only a ToolMessage
                              |                        |              |          explaining why)
                              |                  human_handoff   continue_decision
                              |                   (if flagged)        |
                              +-------------------------<-------------+
```

- **load_context**: entry node (agent/session/tools/provider are already
  resolved by the time the graph is built -- this is a seam for future
  per-turn setup, not currently doing anything heavier).
- **agent_decision**: asks the model what to do next via an `ActionPlanner`
  (see below), never `bind_tools()` directly.
- **validate_action / permission_check**: normalizes whatever the model
  asked for into a `PlannedAction` (`{tool_call_id, tool_name, arguments}`)
  and checks it against this agent's actual permissions and each tool's
  `requires_confirmation` metadata -- **before any tool function runs**.
  This is the answer to "never trust an action produced by the LLM": even
  if a provider's response named a tool this agent was never granted, or a
  confirmation-required tool without `confirmed: true`, it is denied here,
  structurally, the same way for every agent and every provider.
- **execute_tool**: runs each allowed action with its registry-configured
  timeout (`app/tools/registry.py`'s `timeout_seconds`, enforced via a
  thread pool) and writes one row per attempt -- success, denied, error, or
  timeout -- to the tool-execution audit log
  (`app/models/tool_execution_log.py` / `app/services/tool_audit_service.py`),
  with arguments and results sanitized before they're ever persisted
  (sensitive-looking keys are redacted to a boolean presence flag; see the
  admin "Tool Activity" panel on an agent's page, or
  `GET /api/admin/agents/{id}/tool-executions`).
- **process_result**: folds what the tool(s) actually did (read from `ctx`,
  the same mutable per-turn object the tool functions themselves write to)
  back into graph state -- never what the model merely claims happened.
- **human_handoff**: when `request_human_handoff` was called, marks
  `handoff_requested`/`handoff_reason` on graph state (the visitor-facing
  text stays generic -- "I can connect you with a team member" -- with no
  internal tool names or reasoning ever exposed).
- **continue_decision / respond**: named passthroughs matching the spec's
  conceptual graph; the real "done vs. call another tool" decision is made
  by the model on the next `agent_decision` call, which is the correct,
  generic place for it rather than re-implementing business logic here.

### Native tool calling vs. normalized action planning

`app/agents/action_planner.py` defines an `ActionPlanner` abstraction with
one concrete implementation today, `NativeToolCallPlanner`, which wraps
`bind_tools()`/`.tool_calls` -- every provider this platform ships
(Ollama, OpenAI-compatible covering Groq/OpenAI/OpenRouter/Azure) supports
native tool calling, so one implementation covers all of them via
`get_action_planner(chat_model, tools, capabilities)`. Crucially, **native
tool calling never bypasses LangGraph**: `extract_actions()` turns
`AIMessage.tool_calls` into plain `PlannedAction` data immediately, and
everything downstream of that (permission_check, execute_tool) treats it
exactly like any other action request. A future provider without native
tool calling plugs in as a second `ActionPlanner` (e.g. a
`StructuredOutputPlanner` driven by `capabilities.supports_structured_output`)
-- `get_action_planner` is the one place that branches on capability, and
no graph node needs to change.

### How confirmation works

A tool's `requires_confirmation` flag (`app/tools/registry.py`) is enforced
twice, independently: the tool function itself checks its own `confirmed`
argument (e.g. `create_lead_fn`), and -- new in this phase -- the graph's
`permission_check` node denies the call generically for *any*
confirmation-required tool whose arguments don't include `confirmed: true`,
before the function is ever invoked. This means a tool author doesn't have
to remember to implement the check correctly for confirmation to be
enforced; the graph enforces it either way.

### How to add a new tool / agent / provider without touching the graph

- **New tool**: add it to `TOOL_REGISTRY` in `app/tools/registry.py`
  (name, description, category, `requires_confirmation`, `risk_level`,
  `timeout_seconds`) and build it in the relevant `build_*_tools(ctx)`
  module. Nothing in `app/agents/graph.py` changes.
- **New agent**: configure it (system prompt, provider, tool grants,
  knowledge base) via the admin API/dashboard -- see
  [Adding a new agent](#adding-a-new-agent). The same compiled graph serves
  it.
- **New provider**: implement `AIProvider` (see
  [How AI providers work](#how-ai-providers-work)) and declare its
  capabilities. If it supports native tool calling, `NativeToolCallPlanner`
  already works with it; nothing in the graph needs to change either way.

`backend/tests/test_graph_orchestration.py` exercises the real compiled
graph end-to-end (only the chat model itself is faked) for: a
confirmation-required tool denied without `confirmed`, the same tool
succeeding and being audited when confirmed, a tool call outside an
agent's permissions being denied as `tool_not_allowed` even if a
misbehaving provider response names it, a tool timing out, a human-handoff
request propagating without leaking internals, and a plain no-tool-call
turn never touching the audit log at all.

---

## How AI providers work

Every agent's chat model is resolved fresh per request, not hard-coded.
The chain is:

```
Agent  ->  agent.provider_id (or platform default)  ->  AIProviderConfig row
       ->  AIProviderFactory.create(config)  ->  concrete AIProvider
       ->  provider.get_chat_model(overrides)  ->  plain LangChain BaseChatModel
       ->  handed to the one generic LangGraph, unchanged
```

**The abstraction.** `app/ai/base.py::AIProvider` is the only interface
`app/agents/graph.py` and every tool ever touch. It exposes
`get_chat_model()`, `list_models()`, and `test_connection()` -- nothing
provider-specific leaks past it. `app/ai/factory.py::AIProviderFactory`
is the only place a `provider_type` string (`"ollama"`, `"groq"`,
`"openai"`, ...) maps to a concrete class. Two implementations ship today:

- `OllamaProvider` (`app/ai/providers/ollama.py`) -- wraps `ChatOllama`,
  no API key.
- `OpenAICompatibleProvider` (`app/ai/providers/openai_compatible.py`) --
  wraps `ChatOpenAI` with a configurable `base_url`, covering **Groq**,
  OpenAI itself, OpenRouter, Azure OpenAI's compatible endpoint mode, and
  any custom OpenAI-compatible endpoint, all through one implementation.

`anthropic` and `google` are registered as selectable provider types
(so they already appear in the admin dropdown) but raise a clean
`PROVIDER_CONFIGURATION_ERROR` ("not yet implemented") until someone adds
`app/ai/providers/anthropic.py` / `google.py` implementing the same
`AIProvider` interface and one line in `app/ai/factory.py`'s
`_IMPLEMENTATIONS` map -- no LangGraph, tool, or RAG code would need to
change.

**Per-agent configuration, admin-managed.** `Agent.provider_id` (nullable
FK to `ai_providers`) plus `agent.model`/`temperature`/`max_tokens` (as
overrides layered on top of the provider's own defaults) let two agents
use completely different providers simultaneously -- e.g. Kaur Jewellery
on Ollama, Astrology on Groq -- with **zero code differences**, purely
data in the `agents` and `ai_providers` tables, editable from
**Admin → Agents → (agent) → AI Provider** and **Admin → AI Providers**.

**Backward compatibility.** `Agent.provider_id = NULL` means "use the
platform default provider" (`app/ai/resolution.py::resolve_provider_config_for_agent`).
`app/seed.py::_seed_default_provider` runs on *every* startup (not just
first-ever seed) and creates a default Ollama provider matching
`OLLAMA_DEFAULT_BASE_URL`/`CHAT_MODEL` if none exists yet -- so an
existing installation upgrading to this feature keeps working immediately,
with every pre-existing agent (all `provider_id = NULL`) resolving to that
seeded default automatically. No admin action required.

**API key security.** Write requests (`AIProviderCreate`/`AIProviderUpdate`)
accept a plaintext `api_key` field; it's encrypted (`app/security/encryption.py`,
Fernet keyed by `ENCRYPTION_KEY`) before the row is ever written.
**Every** response schema (`AIProviderOut`) exposes only
`api_key_configured: bool` -- there is no code path in `app/api/admin_providers.py`
that serializes `encrypted_api_key` or a decrypted key back to a client,
logs one, or lets the public chat/session APIs see one. The public widget
never knows which provider is in use at all -- it only ever calls
`POST /api/chat` with `{agent_token, session_id, message}`, exactly as
before this feature existed.

**Capability checks.** `ProviderCapabilities` (`app/ai/capabilities.py`)
declares what a provider/model combination supports (`supports_tools`,
`supports_streaming`, `supports_vision`, `supports_structured_output`,
`supports_embeddings`, `supports_reasoning`), with per-provider-row
overrides for cases like "this specific Groq-hosted model doesn't support
tool calling even though Groq generally can." Before binding tools,
`app/agents/graph.py::build_graph` checks `capabilities.supports_tools` and
raises `UNSUPPORTED_CAPABILITY` (a clean, standardized error -- see
`app/ai/errors.py::ProviderErrorCode`) rather than letting an agent with
tools enabled silently fail deep inside LangChain against an incompatible
provider.

**Fallback provider.** `Agent.fallback_provider_id` (optional) is wrapped
around the primary chat model by `app/ai/resolution.py::_FallbackChatModel`,
a minimal object exposing just `.bind_tools()`/`.invoke()` (not a real
LangChain subclass, deliberately -- keeps it simple). On a primary-provider
failure, it's used **only** for the retryable categories --
`PROVIDER_TIMEOUT`, `RATE_LIMITED`, `MODEL_UNAVAILABLE`,
`PROVIDER_DISABLED` -- and explicitly **never** for `INVALID_API_KEY` or a
configuration error, per the project brief: silently falling back on bad
credentials would hide a real misconfiguration from the admin instead of
surfacing it. Every fallback use is logged with the failure category (never
the credential itself).

**Testing a provider.** `POST /api/admin/providers/{id}/test` builds the
provider and sends one minimal request, returning `{success, provider,
model, latency_ms}` on success or `{success: false, error_code, message}`
on failure -- classified into the standardized error codes above by
inspecting the exception message only (`app/ai/errors.py::classify_error`),
never by exposing the raw SDK exception or request/response details.
`GET /api/admin/providers/{id}/models` returns available models where the
provider supports discovery (Ollama's `/api/tags`, or an OpenAI-compatible
provider's `/models` endpoint when the API key has access to it) and
`{"supported": false}` otherwise -- manual model entry always remains
available either way.

---

## How sessions work

- The widget generates/reuses a `session_id` via `localStorage`, keyed
  **per agent token** (`aria_session_id_<last-12-chars-of-token>`), so a
  visitor talking to two different agents on two different sites never
  shares state between them.
- Every request sends `{ agent_token, session_id, message }`.
  `app/services/session_service.py::get_or_create_session` only reuses an
  existing `session_id` if it belongs to the *same* `agent_id` -- reusing
  another agent's session_id transparently creates a fresh one instead.
- Every user and assistant message is persisted immediately
  (`messages` table) -- never held only in browser state.
- Closing the browser and coming back: `GET /api/session/{id}` detects a
  gap since `last_activity_at` (`RETURNING_VISITOR_GAP`, default 2 minutes)
  and flags `is_returning: true`; the widget shows a "welcome back" prompt
  and continues the same conversation.
- LangGraph's `AgentState` (`app/agents/state.py`) is scratch space for a
  single turn only -- the database, not that TypedDict, is the system of
  record, so a backend restart mid-conversation loses nothing.

---

## How the knowledge base (RAG) works

**Upload never processes inline.** `POST /api/knowledge/upload` (admin
dashboard, or the API directly) validates the file (extension, size),
writes it to disk under a UUID-based path (never the original filename --
see [Security](#design-decisions--known-limitations) on path traversal),
creates a `documents` row (`status=PROCESSING`) and a `knowledge_jobs` row
(`status=PENDING`), and returns immediately with `{document_id, job_id}`.

**A separate process does the work.** `worker/knowledge_worker.py` polls
`knowledge_jobs` for pending rows (`SELECT ... FOR UPDATE SKIP LOCKED` on
Postgres, so multiple worker instances never double-process one job), then
runs `app/rag/ingestion/service.py::process_job`:

1. Delete any chunks this same job/document might already have written
   (restart-safety: a crash mid-ingestion can never leave duplicates).
2. Load the file with the loader matching its extension
   (`app/rag/ingestion/loaders/`: PDF, DOCX, TXT, CSV, JSON, Markdown --
   adding a new format is one new loader module + one registry line).
3. Split into overlapping chunks (`app/rag/chunking/splitter.py`,
   `CHUNK_SIZE`/`CHUNK_OVERLAP` from env), preserving page numbers where
   the source format has them.
4. Embed each chunk (`app/rag/embeddings/service.py` -- Ollama by
   default; see below for the deterministic test double).
5. Store chunks + vectors in `document_chunks`, tagged with
   `tenant_id`/`agent_id`/`knowledge_base_id`/`document_id`.
6. Mark the document `READY` (or `FAILED` with `processing_error` set, if
   any step raised) and the job `COMPLETED`/`FAILED`.

Reprocessing (admin clicks "Reprocess", or a document previously failed)
just enqueues a fresh job with the same `document_id` -- step 1 above
means old chunks are always cleanly replaced, never duplicated.

**Retrieval is a tool, not a graph node.** Rather than adding a separate
"classify: is this a knowledge question?" node to the LangGraph (as one
reasonable design would), `search_knowledge_base`
(`app/tools/knowledge.py`) is just another tool the existing
`assistant <-> tools` loop can call -- the model decides when it needs
retrieval the same way it decides when to call `search_jewellery` or
`calculate_birth_chart`. This keeps the graph itself (`app/agents/graph.py`)
completely unchanged and reusable: adding RAG to a new agent is granting it
one more tool, never touching graph code.

**Isolation is structural, not a query convention.** The tool never
accepts `tenant_id`/`agent_id`/`knowledge_base_id` as LLM-supplied
arguments -- only a free-text `query` string. Inside the tool,
`ctx.agent.tenant_id`/`ctx.agent.id` (already resolved server-side from
the validated request token, before the graph ever runs) and
`knowledge_base_service.get_for_agent(...)` supply those three values.
`KnowledgeRetriever.retrieve()` (`app/rag/retrieval/retriever.py`) filters
by all three *before* the `ORDER BY ... <=> query_vector` similarity
search, then re-checks every returned row against those same three values
before returning anything -- so even a future refactor that accidentally
loosened the `WHERE` clause would still get caught by that check (and by
`test_retrieval_isolation.py`, which asserts this directly against a real
Postgres+pgvector database, not a mock).

**What the LLM sees back:** only chunk text, nothing else -- no document
IDs, filenames, or chunk indices (see `search_knowledge_base_fn` in
`app/tools/knowledge.py`). The system prompt (`PLATFORM_RULES` in
`app/agents/graph.py`) instructs the model to prefer retrieved knowledge
for business-specific questions, never invent policies/prices/facts, say
plainly when the knowledge base doesn't have an answer, and never reveal
document metadata, tool names, or how retrieval works.

**Embeddings are provider-swappable.** `EmbeddingService`
(`app/rag/embeddings/service.py`) is the only interface ingestion and
retrieval use. `OllamaEmbeddingService` (default, `EMBEDDING_MODEL`, e.g.
`nomic-embed-text`) is what production uses. A `DeterministicEmbeddingService`
(seeded-hash, unit-normalized, `EMBEDDING_PROVIDER=deterministic`) exists
purely so the whole pipeline -- including the critical cross-agent
isolation test -- can run in CI/tests without a live Ollama instance. It
is **not** semantically meaningful (two similar texts won't reliably embed
close together) and must never be used in production; the test suite sets
it via environment variable in `tests/conftest.py`, and production
`.env.example` defaults to `ollama`.

---

## Example RAG conversation

This is real output from `app/rag/ingestion/service.py` and
`app/rag/retrieval/retriever.py`, run against the actual files in
`examples/kaur-jewellery/` and `examples/real-estate/` (using the
deterministic embedding provider, since this was captured without a live
Ollama instance -- see the caveat on ranking quality below).

**Setup:** two agents, each with their own knowledge base, ingest their
own example documents:

```
examples/kaur-jewellery/shipping-policy.md  -> READY, 2 chunks
examples/kaur-jewellery/return-policy.md    -> READY, 3 chunks
examples/kaur-jewellery/faq.json            -> READY, 5 chunks
examples/real-estate/faq.csv                -> READY, 2 chunks
examples/real-estate/mortgage-policy.md     -> READY, 2 chunks
examples/real-estate/communities.txt        -> READY, 3 chunks
```

**Visitor asks the Kaur Jewellery agent:** *"What is your jewellery return
policy?"* -- `search_knowledge_base` retrieves (verbatim, top match):

> \# Kaur Jewellery -- Return & Exchange Policy ## Returns We want you to
> love your jewellery. If you're not completely satisfied, you may return
> most items within **30 days of delivery** for a full re[fund...]

A real LLM turn (not captured here, since this environment has no live
Ollama) would compose this into something like: *"You can return most
items within 30 days of delivery for a full refund, as long as they're
unworn with original packaging and your receipt. Would you like the
exchange details too?"*

**Same visitor then asks:** *"What is the real estate mortgage policy?"*
-- `search_knowledge_base` (still scoped to the Kaur Jewellery agent's
`tenant_id`/`agent_id`/`knowledge_base_id`) returns chunks from Kaur
Jewellery's *own* documents (its FAQ and shipping policy) -- **verified
to contain zero occurrences of "mortgage" or "down payment"**, because
that content simply does not exist in this agent's `document_chunks`
rows, regardless of what the query asks about. The system prompt
instructs the model to say plainly it doesn't have that information rather
than inventing an answer.

**Caveat on this specific captured run:** the deterministic embedding
provider used to generate the output above is a seeded hash, not a real
embedding model -- it guarantees the same text always maps to the same
vector (useful for testing storage/isolation), but it does **not**
guarantee that semantically similar text ends up nearby in vector space.
With a real Ollama embedding model (the production default), the
"mortgage" query would correctly rank far from all of Kaur Jewellery's
content by actual semantic distance, not just by absence -- but the
**isolation guarantee holds either way**, because it comes from the
`WHERE tenant_id = ... AND agent_id = ... AND knowledge_base_id = ...`
filter applied before any similarity ranking happens at all, not from the
embedding being good.

---

## Embedding the React widget

### Generic HTML (any website)

```html
<script src="https://your-cdn.example.com/aria-widget.js"></script>
<script>
  AriaWidget.mountFloating({
    agentToken: "pub_...",
    apiUrl: "https://api.example.com",
  });
</script>
```

This renders a floating launcher button that opens a chat panel on click.
For an inline chat panel embedded in a specific spot on the page instead:

```html
<div id="my-chat-container" style="width:400px;height:600px;"></div>
<script src="https://your-cdn.example.com/aria-widget.js"></script>
<script>
  AriaWidget.mount({
    agentToken: "pub_...",
    apiUrl: "https://api.example.com",
    target: document.getElementById("my-chat-container"),
  });
</script>
```

### Why no React is needed on the host site

`widget/vite.config.ts` builds in library mode with React/ReactDOM bundled
in (not externalized), as a single IIFE (`aria-widget.js`) that assigns
`window.AriaWidget`. The host page needs nothing installed.

### Why there's no separate `aria-widget.css`

The widget's compiled CSS is imported with Vite's `?inline` suffix
(`import widgetCss from "./index.css?inline"`) and injected as a `<style>`
tag into a **Shadow DOM** root created for each `mount()`/`mountFloating()`
call. This means:

- The widget's styles can never be overridden by the host page's CSS.
- The widget's styles can never leak out and affect the host page.
- There is nothing extra to `<link>` -- one `<script>` tag is enough.

This is a deliberate improvement over shipping a separate stylesheet (the
more fragile, classic embeddable-widget approach), at the cost of not
literally matching a `aria-widget.js` + `aria-widget.css` two-file output.
The WordPress plugin's `assets/aria-widget.css` is kept as an intentionally
empty placeholder so the asset layout still matches what's expected.

### Branding, no code changes

Everything the widget shows -- assistant name, brand, welcome message,
accent color (`agent.theme.accent`), suggested prompts -- comes back from
`GET /api/session` / `POST /api/chat` as part of the resolved agent's
public info (`AgentPublicInfo`). The widget component itself has zero
agent-specific logic.

### Self-serve builder: where the embed script actually comes from

The self-serve builder (`/api/builder/agents`) generates a `<script>` tag
pointing at `PUBLIC_WIDGET_SCRIPT_URL` (default
`http://localhost:8000/static/aria-widget.js`). For that URL to resolve
locally, the backend mounts `app/static/` at `/static` (see `app/main.py`)
and `app/static/aria-widget.js` must contain the built bundle:

```bash
cd widget && npm install && npm run build
cp dist/aria-widget.js ../backend/app/static/aria-widget.js
```

A pre-built copy ships in the repo already, but if you change
`widget/src/*`, rebuild and re-copy it the same way you already do for the
WordPress plugin's `assets/aria-widget.js`, or the generated install
snippet will 404 until you do.

In production, don't rely on the backend to host this file -- point
`PUBLIC_WIDGET_SCRIPT_URL` at a CDN copy instead (`/static` on the API
process is a dev convenience, not a CDN) and the `/static` mount is simply
unused.

### Self-serve builder: per-plan knowledge base limits

Every signup starts on the **free** plan (`User.plan`, `app/models/user.py`,
default `"free"`). `app/billing/plans.py` is the single source of truth for
what each plan allows:

| Plan | Documents per agent | Max file size |
|------|---------------------|----------------|
| Free | 3                   | 5 MB           |
| Plus | 25                  | 25 MB          |

The limit is enforced **per agent**, not per account -- each agent has its
own knowledge base, so a customer with three agents gets the full quota on
each, not one quota split across all of them.

Both checks happen server-side in `POST /api/builder/agents/{id}/documents`
(`app/api/builder.py`) before the file is ever written to disk:

1. Count the agent's existing `documents` rows; `>= max_documents_per_agent`
   is a `403`.
2. `max_file_size_bytes` is passed into `ingest_uploaded_document(...,
   max_file_size=...)` -> `validate_upload(..., max_size=...)`
   (`app/security/file_storage.py`), which rejects an oversized file with a
   `400` before anything is read into memory beyond the initial `file.read()`.

`GET /api/builder/me/plan` reports the caller's current limits so the
dashboard (`CustomerAgentDetailPage.tsx`) can show a quota ("2 of 3
documents used") and disable the upload button before a doomed request ever
leaves the browser -- that's a UX nicety only; the server-side checks above
are what actually enforce it, since the client can't be trusted to self-police.

**There is no payment processor wired up.** `plan` only ever changes today
through a platform operator calling `PATCH /api/admin/users/{id}/plan`
(`app/api/admin_users.py`, gated by the same `X-Admin-Key` as the rest of
the platform-admin API) -- never by the customer themselves. Wiring up real
billing later (e.g. a Stripe webhook) means pointing that same write at the
webhook handler; nothing else here needs to change.

Uploads also accept `.xlsx` spreadsheets now (`app/rag/ingestion/loaders/xlsx.py`,
registered in `LOADER_REGISTRY` next to the PDF/DOCX/CSV/JSON/Markdown
loaders) -- each row is rendered as `column: value` lines per sheet, the
same convention `CSVLoader` uses, so a spreadsheet chunks the same way a CSV
export of it would.

---

## WordPress integration

`wordpress/kaur-ai-agent/` is a real, working plugin:

- **No Python/Ollama/LangChain/LangGraph** is installed in WordPress -- it
  only enqueues the pre-built `assets/aria-widget.js` and points it at your
  backend + agent token.
- **Settings page** (Settings -> Kaur AI Agent): API URL, Agent Token,
  Widget Position (floating or inline-shortcode-only), Enable Widget,
  optional assistant name override.
- **Shortcode**: `[aria_ai_agent]` renders an inline mount point and calls
  `AriaWidget.mount(...)`.
- **Floating mode**: hooks `wp_footer` and calls
  `AriaWidget.mountFloating(...)` site-wide when enabled.
- Updating the bundled widget after a source change:

  ```bash
  cd widget && npm install && npm run build
  cp dist/aria-widget.js ../wordpress/kaur-ai-agent/assets/aria-widget.js
  ```

See `wordpress/kaur-ai-agent/README.md` for full install steps.

---

## Adding a new agent

All from the admin dashboard (Agents -> New agent), or via the API:

```bash
curl -X POST http://localhost:8000/api/admin/agents \
  -H "X-Admin-Key: $ADMIN_SECRET_KEY" -H "Content-Type: application/json" \
  -d '{
    "agent_key": "dental-clinic",
    "name": "Dana",
    "brand_name": "Bright Smile Dental",
    "system_prompt": "You are Dana, a friendly dental clinic assistant. ...",
    "welcome_message": "Hi! How can I help with your dental needs today?",
    "suggestions": ["Book an appointment", "Our services"],
    "lead_fields": ["name", "email", "phone", "reason"],
    "tool_keys": ["create_lead"]
  }'
```

The response includes `public_token` **exactly once** -- copy it into a
widget snippet immediately. No frontend code changes are required; the
widget will show this agent's name, brand, welcome message, and
suggestions automatically once given this token.

To let the new agent do more than generic lead capture (e.g. search a
services catalog or book real appointments), see the next section.

To give it business knowledge (policies, FAQs, service descriptions),
grant it `search_knowledge_base` in the tools list, then go to that
agent's **Knowledge base** page in the admin dashboard and upload
documents -- see
[How the knowledge base (RAG) works](#how-the-knowledge-base-rag-works).
`examples/` has sample documents you can upload immediately to try this
without writing your own content first.

---

## Adding a new tool

1. Write the tool's logic in `app/tools/<domain>.py`, following the
   pattern in `jewellery.py`/`astrology.py`/`realestate.py`: a
   `build_<domain>_tools(ctx: ToolContext) -> dict[str, StructuredTool]`
   function, each entry using a Pydantic `args_schema` and delegating to a
   `services/` module for any business-critical calculation (never let the
   LLM invent that data itself).
2. Merge that dict into `_all_available_tools` in
   `app/tools/registry.py`, and add a display entry to `TOOL_REGISTRY`
   (name + description shown in the admin dashboard).
3. Restart the backend -- `seed.py`'s `_seed_tools` inserts any new
   `TOOL_REGISTRY` key into the `tools` table automatically if it doesn't
   already exist (existing tools/agents are left untouched).
4. Grant it to whichever agents should have it, from that agent's page in
   the admin dashboard (or `PUT /api/admin/agents/{id}/tools`).

No agent gets a new tool automatically -- it must be explicitly granted.

**The knowledge base tool (`search_knowledge_base`) works the same way** --
it's just another entry in `TOOL_REGISTRY`, built by
`app/tools/knowledge.py`. There's no special-cased "RAG mode"; granting it
to an agent is identical to granting `search_jewellery`.

---

## Adding a new AI provider

**Configuring an existing implemented provider** (Ollama, Groq, OpenAI,
OpenRouter, Azure OpenAI's compatible mode, or any custom OpenAI-compatible
endpoint) is pure admin-dashboard configuration, no code:

1. **Admin → AI Providers → Add AI Provider.**
2. Pick the provider type. Ollama needs a base URL and model, no API key.
   Everything else needs an API key; "Custom OpenAI-Compatible" (and Azure)
   also needs a base URL.
3. Save, then **Test Connection** to confirm it actually works before
   assigning it to any agent.
4. Optionally **Set as default** -- this is what agents with no explicit
   provider selected resolve to.
5. Go to **Admin → Agents → (agent)** and pick this provider (and
   optionally a fallback provider) from the dropdowns.

**Implementing a genuinely new provider type** (e.g. Anthropic/Claude or
Google Gemini, both already selectable in the admin dropdown but marked
"coming soon"):

1. Create `app/ai/providers/anthropic.py` (or `google.py`), implementing
   the `AIProvider` interface (`app/ai/base.py`) -- at minimum
   `get_chat_model()`, `provider_type`, `model_name`; override
   `list_models()`/`test_connection()` if the default implementations
   (generic "send one minimal request") aren't ideal for that provider.
2. Add one line to `_IMPLEMENTATIONS` in `app/ai/factory.py` and remove
   the type from `_NOT_YET_IMPLEMENTED`.
3. That's it -- no changes to `app/agents/graph.py`, any tool, RAG, the
   admin API, or the widget. The admin dropdown, provider CRUD, encryption,
   capability checks, fallback support, and per-agent selection all already
   work generically against the `AIProvider` interface.

---

## Rotating (or disabling) a token

From the admin dashboard: Agents -> select an agent -> **Rotate token**
(shows the new plaintext token once) or **Disable** (the agent stops
resolving entirely, `403`, without deleting any data).

Via API:

```bash
# Rotate: old token stops working immediately, new one is returned once
curl -X POST http://localhost:8000/api/admin/agents/{id}/rotate-token \
  -H "X-Admin-Key: $ADMIN_SECRET_KEY"

# Disable / re-enable
curl -X POST http://localhost:8000/api/admin/agents/{id}/disable -H "X-Admin-Key: $ADMIN_SECRET_KEY"
curl -X POST http://localhost:8000/api/admin/agents/{id}/enable  -H "X-Admin-Key: $ADMIN_SECRET_KEY"
```

Update every website snippet using the old token after rotating.

---

## Testing

```bash
cd backend
pytest -q
```

**169 tests**, run against a real local Postgres + pgvector instance (not
SQLite, not a mock -- `tests/conftest.py` points at
`postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agent_platform_test`
by default; override with `TEST_DATABASE_URL`). Embeddings use the
deterministic test double (`EMBEDDING_PROVIDER=deterministic`, set in
`conftest.py`) so the suite never needs a live Ollama instance, and cloud
AI provider tests use fake/mocked chat models -- **no real Groq, OpenAI,
Anthropic, or other cloud API key is ever required to run the suite.**

The admin dashboard also has a small (currently header-handling-focused,
but growing) frontend test suite:

```bash
cd frontend
npm run test
```

covering the API client's request-building logic -- most importantly the
header-merge-order regression described in
[Design decisions](#design-decisions--known-limitations), which is worth
reading if you ever add a new `fetch()` wrapper anywhere in this codebase.

Coverage includes everything from the original platform (token
generation/hashing/verification, agent resolution, tool permission
isolation, rate limiting, session lifecycle, chat API behavior with the
LLM mocked out, admin CRUD, leads, customer matching) plus RAG (see
below) plus AI provider configurability:

- **Provider resolution** (`test_ai_resolution.py`): agent with no
  provider resolves to the platform default; agent with an explicit
  provider uses it, not the default; a *disabled* explicit provider falls
  back to the default; no provider anywhere raises `PROVIDER_NOT_FOUND`;
  two agents using different providers (Ollama + Groq) simultaneously
  resolve independently and correctly; capability overrides
  (`supports_tools=False` on a specific provider row) are honored.
- **Fallback behavior** (`test_ai_resolution.py`, `_FallbackChatModel`
  tests): a retryable failure (timeout/rate-limit) on the primary
  triggers the fallback and returns its response; an `INVALID_API_KEY`
  failure does **not** trigger fallback (raises instead, per the "never
  silently mask a bad credential" rule); no fallback configured re-raises
  the original error; a successful primary call never touches the
  fallback at all; `bind_tools()` preserves fallback wrapping through to
  `invoke()`.
- **Admin provider API** (`test_admin_providers_api.py`): CRUD, admin-auth
  enforcement, set-default (and that it un-defaults the previous one),
  connection test success/failure paths (mocked), model discovery where
  supported and gracefully unsupported otherwise, and -- critically --
  **every provider list/detail response is asserted to contain
  `api_key_configured` and never `api_key` or `encrypted_api_key`.**
- **Backward compatibility** (`test_provider_backward_compat.py`): a
  default Ollama provider is seeded automatically on startup; a
  pre-existing agent with `provider_id = NULL` still resolves and works
  unchanged; an agent with tools enabled on a provider that doesn't
  support tool calling raises a clean `UNSUPPORTED_CAPABILITY` error
  rather than failing deep inside LangChain; the same agent with *no*
  tools granted is unaffected by that same capability gap.

### RAG-specific tests

- **Chunking** (`test_chunking.py`): boundary-preserving splits, page
  metadata, never infinite-looping on pathological input.
- **Embeddings** (`test_embeddings.py`): the deterministic provider is
  stable/unit-normalized/dimension-correct.
- **Loaders** (`test_loaders.py`): all 6 file types, including failure
  cases (empty file, invalid JSON, no CSV rows, unsupported extension).
- **Ingestion** (`test_ingestion.py`): successful ingestion marks
  `READY`/sets `chunk_count`, failed ingestion marks `FAILED` with
  `processing_error`/`error_message` set, reprocessing doesn't duplicate
  chunks, and restart-safety (simulated leftover chunks from a "crashed"
  attempt get wiped before reprocessing, never appended to).
- **Retrieval isolation** (`test_retrieval_isolation.py`): relevant-chunk
  retrieval, `top_k` respected, empty KB returns nothing, and the
  **critical test** -- Agent A (jewellery) vs. Agent B (real estate), each
  with real ingested content, proving Agent A never retrieves Agent B's
  chunks even when asked an off-topic question, checked both via the
  retriever's return value AND by directly inspecting what's actually
  stored in `document_chunks` for each agent.
- **Knowledge API** (`test_knowledge_api.py`): upload/list/detail/delete
  (chunks actually removed)/reprocess/job-status, admin-auth enforcement,
  extension/unknown-agent rejection.
- **Knowledge tool** (`test_knowledge_tool.py`): graceful "no knowledge
  base" / "no results" messages, and confirms the tool never leaks
  filenames or storage paths back to the LLM.

A note on the shared test database: since the whole suite runs against one
Postgres database for the session (reset to a clean schema at collection
time, not per-test), a handful of tests that touch the global
"which provider is the platform default" singleton deliberately restore or
re-establish state within their own test function rather than assuming
no other test has touched it -- see the comments in `test_ai_resolution.py`
and `test_provider_backward_compat.py` for exactly where and why.

---

## Troubleshooting: the agent says success but no lead appears

The agent responds with something like "Great, I've saved your details and
someone will reach out!" but nothing shows up under **Admin → Leads**.
This means the conversational LLM *said* a lead was created without the
`create_lead` (or `create_jewellery_lead`/`create_astrology_consultation`)
tool actually having run and succeeded. Since the platform never trusts
what the model claims -- only what a tool actually did (`ChatResponse.lead_created`
is computed from `ctx.leads_created`, never parsed from the assistant's
text) -- this always means one of the following, in order of likelihood:

1. **The model never called the tool at all.** The most common cause,
   especially with smaller/local models or ones not fine-tuned reliably
   for tool calling. The LLM just generates a plausible-sounding
   confirmation instead of invoking anything.
2. **The tool wasn't granted to this agent.** Check
   **Admin → Agents → (agent) → Tools** -- if `create_lead` (or the
   agent-specific lead tool) isn't checked, the model has no way to call
   it at all, confirmed or not.
3. **The tool *was* called, but failed**, and the model didn't relay the
   failure to the visitor (e.g. no email/phone was actually captured from
   the conversation, or the visitor never actually said something
   affirmative enough for the model to set `confirmed=true`).
4. **The provider/model doesn't reliably support tool calling.** If you
   recently switched an agent to a different AI provider (see
   [How AI providers work](#how-ai-providers-work)), some models handle
   `bind_tools()` far less consistently than others.

**How to actually find out which one it was:** check that session's agent
under **Admin → Agents → (agent) → Tool Activity** first -- it's a direct
read of the orchestration graph's audit log
(`GET /api/admin/agents/{id}/tool-executions`, backed by
`app/models/tool_execution_log.py`) and shows every call attempt with its
status (`success`/`denied`/`error`/`timeout`), an `error_category`
(`confirmation_required`, `tool_not_allowed`, `invalid_arguments`,
`tool_timeout`, `tool_execution_error`), and a sanitized result -- no log
grepping required. If `Tool Activity` shows nothing at all for the time in
question, the model never called the tool (cause #1 below). The same
information is also logged at `agent_platform.tools`, and every completed
chat turn is summarized at `agent_platform.chat`, including a `WARNING`
specifically for this scenario:

```bash
docker compose logs backend | grep "session=<the session_id>"
```

- If you see `tool=create_lead ... success=True`, but still no row in the
  dashboard -- that would be a real bug; please report it with these log
  lines.
- If you see `tool=create_lead ... success=False result=...`, the result
  text tells you exactly why (e.g. `not created: no email or phone
  provided`, `not created: confirmed=false`) -- the model called the tool
  but the visitor's message didn't actually satisfy what the tool needs.
- If you see a `possible ungrounded success claim` warning with an empty
  or unrelated `tools_called` list -- the model never called the tool at
  all. Try a more capable/tool-call-reliable model or provider for that
  agent, and/or tighten the agent's system prompt to be more explicit
  about when to call the lead tool.
- If you see nothing at all for that session -- the turn may have hit the
  generic error fallback; check for a `Chat turn failed` error log instead.

This scenario has a dedicated test (`tests/test_chat_grounding.py`) and
prompt-level reinforcement (`PLATFORM_RULES` in `app/agents/graph.py`
explicitly tells the model not to claim success without a same-turn tool
result confirming it) -- but no amount of prompting fully eliminates
cause #1 with a sufficiently unreliable model, which is why the logging
exists as the actual diagnostic tool.

---

## Design decisions & known limitations

- **Frontend `fetch()` options object literal order matters and has bitten
  this project once already.** `{ ...options, headers: {...} }` (options
  spread first, headers set last) is required, not stylistic --
  `{ headers: {...}, ...options }` silently lets any caller-supplied
  `headers` (e.g. `authHeaders(adminKey)`) wipe out the
  `Content-Type: application/json` default entirely, which makes the
  browser send a JSON string body as `text/plain`, which makes FastAPI
  hand Pydantic the raw JSON *string* instead of parsing it --
  producing a confusing "Input should be a valid dictionary or object to
  extract fields from" error on every authenticated save. Both
  `frontend/src/api/client.ts` and `widget/src/api.ts` have a regression
  test for this exact ordering
  (`frontend/tests/api-client-headers.test.ts`, `npm run test` in
  `frontend/`) -- if you add a new fetch wrapper anywhere, copy this
  pattern, not the other one.

- **No real migration tool (Alembic) yet -- `init_db()` does an additive
  auto-migration instead.** `Base.metadata.create_all()` only creates
  tables that don't exist; it never alters a table already present on a
  running database. So that a schema change like adding
  `agents.provider_id` doesn't crash every existing installation forever,
  `app/database/connection.py::_auto_add_missing_columns` runs after
  `create_all()` and adds any column present on a model but missing from
  the live table (`ADD COLUMN IF NOT EXISTS`, Postgres only). This is
  **not** a substitute for real migrations: it only ever adds nullable
  columns, never handles renames, drops, type changes, backfills, or
  new NOT NULL constraints on existing rows. If you add a column that
  needs a default value applied to existing rows, write that as a proper
  one-off script rather than relying on this. If the project outgrows this
  (frequent complex schema changes across many deployed installations),
  it's a good point to introduce Alembic properly.

- **No separate extraction pipeline.** Rather than a bespoke
  per-domain "extract structured fields, then converse" step, each
  agent's tools carry their own Pydantic `args_schema` and validate their
  own inputs; the system prompt instructs the model to ask naturally for
  whatever's missing before calling a tool. This is what makes one graph
  (`app/agents/graph.py`) genuinely reusable across arbitrarily different
  businesses instead of hand-tuned per domain.
- **Rate limiting is in-memory** (`app/security/rate_limit.py`), fine for a
  single-process deployment; swap in Redis for multi-worker/multi-instance
  production use (the call site doesn't need to change).
- **CORS is intentionally split**: strict allow-list for `/api/admin/*`;
  permissive-but-token-authenticated for `/api/chat` and `/api/session/*`,
  since those are meant to be called from arbitrary third-party sites and
  are gated by the `agent_token` + `allowed_domains` check, not by browser
  same-origin policy. See the comment in `app/main.py` for the full
  reasoning.
- **Admin auth is a shared secret**, not full session/OAuth -- adequate for
  a local/small deployment; `app/api/deps.py::require_admin` is the single
  point to replace.
- **Astrology chart calculation** reuses the prior project's demo service:
  sun sign is calculated for real from the calendar date; moon
  sign/ascendant/houses are clearly-labeled deterministic demo data (no
  ephemeris library bundled).
- **Widget CSS ships inline via Shadow DOM** rather than as a separate
  `.css` file -- see [Embedding the React widget](#embedding-the-react-widget)
  for the reasoning; this is a deliberate, documented deviation from a
  literal two-file build output.
- **The knowledge job queue is a plain Postgres table**, polled by
  `worker/knowledge_worker.py`, not Celery/Redis/RabbitMQ/etc. This keeps
  local setup to `docker compose up` with no extra infrastructure while
  still being architecturally a distinct background-processing step the
  chat API never touches. `FOR UPDATE SKIP LOCKED` makes it safe to run
  more than one worker instance. Swap in a real broker later without
  changing the API/worker contract if job volume ever demands it.
- **One knowledge base per agent today.** The schema (`knowledge_bases`
  has its own `id`, `agent_id` is just a foreign key) supports more than
  one per agent later (e.g. "public FAQ" vs. "internal policy"); the admin
  UI and `get_or_create_default` just don't expose that yet.
- **`VECTOR_DIMENSION` is fixed at table-creation time** (pgvector column
  dimension can't change without a migration/re-ingestion). It must match
  whatever embedding model you configure -- `nomic-embed-text` is 768-dim,
  the default. Changing embedding models later means re-ingesting every
  document.
- **The deterministic embedding provider is a test double, not a cheap
  production option.** It guarantees stable, unit-normalized vectors (so
  storage/isolation logic is fully testable without Ollama) but carries no
  real semantic meaning -- see the caveat in
  [Example RAG conversation](#example-rag-conversation). Production always
  uses `EMBEDDING_PROVIDER=ollama`.
- **File storage is local disk** (`UPLOAD_DIR`), not S3/GCS/etc. Fine for
  a single backend+worker deployment sharing a volume (as docker-compose
  does); swap for object storage before scaling to multiple hosts without
  a shared filesystem.
- **Website/FAQ/database/API knowledge sources aren't implemented yet.**
  `Document.source_type` and the `source_type` concept from the project
  brief are modeled in the schema so they can be added later (a
  `WebsiteLoader` implementing the same `DocumentLoader` interface, a
  crawl job type, etc.) without changing the retrieval or tool code at
  all -- only today's `document` source type (file upload) is built.
- **Docker Compose is provided but not verified against a live Docker
  daemon** -- this development environment doesn't have one available. The
  YAML has been validated for correctness (`yaml.safe_load`), and every
  piece it orchestrates (Postgres+pgvector schema creation, the ingestion
  pipeline, the worker's job-claiming logic) has been separately verified
  against a real (non-containerized) local Postgres+pgvector instance. If
  `docker compose up` surfaces an environment-specific issue on your
  machine, the most likely spots are the `host.docker.internal` Ollama
  hostname (Linux sometimes needs a different value -- see
  `.env.example`) or file permissions on the `uploads_data` volume.
- **`_FallbackChatModel` is a hand-rolled duck-typed wrapper, not a real
  LangChain `BaseChatModel` subclass.** It only implements `.bind_tools()`
  and `.invoke()` because that's all `app/agents/graph.py` actually calls.
  This keeps it simple and dependency-free, but means it would need
  extending (e.g. `.stream()`) before use in a code path that needs more
  of the LangChain chat-model surface than this platform's graph does
  today.
- **Anthropic and Google are selectable but not implemented.** They exist
  in the admin dropdown and `ALL_PROVIDER_TYPES` (marked "coming soon")
  specifically to demonstrate the extension point without over-building
  ahead of an actual need -- see
  [Adding a new AI provider](#adding-a-new-ai-provider) for the two
  concrete steps to implement either.
- **Model discovery is best-effort.** Ollama's `/api/tags` and an
  OpenAI-compatible provider's `/models` endpoint are used where available;
  manual model entry is always the fallback, since not every provider (or
  every API key's permissions) supports listing.
- **A tool-execution timeout doesn't forcibly kill the running thread.**
  `execute_tool` (`app/agents/graph.py`) stops *waiting* on a tool past its
  configured `timeout_seconds` and records/returns a timeout -- but Python
  has no safe way to kill a thread outright, so an abandoned call finishes
  in the background and its result is simply discarded. This is fine for
  every tool shipped today (in-process DB reads/writes, nothing that holds
  an external lock or does unbounded I/O), but would matter if a future
  tool called a slow external API.
- **Confirmation is turn-based, not a separate paused state.** A
  confirmation-required tool denied by `permission_check` doesn't put the
  conversation into an explicit "awaiting confirmation" state machine --
  the visitor's next message (e.g. "yes, go ahead") is just the next user
  turn, and the model re-requests the tool call with `confirmed: true`
  once it sees that reply in context, which goes through the exact same
  `validate_action`/`permission_check` path again. This keeps one graph for
  every provider (including ones without multi-step conversational state),
  but means confirmation only works as well as the model's own ability to
  notice it already asked and the visitor already answered -- the same
  reliability ceiling tool calling itself has with a given provider/model.
- **No live Groq/Anthropic/OpenAI integration test runs in CI.** The test
  suite (`test_provider_backward_compat.py`, `test_ai_resolution.py`,
  `test_graph_orchestration.py`) exercises the provider abstraction and the
  graph's permission/audit logic against fake chat models and a
  `supports_tools=False` real config row -- not against a live cloud API
  key, per the spec's own guidance to mock unless credentials are
  intentionally configured. If you have a Groq/OpenAI key, configuring a
  real provider through the admin dashboard and using **Test Connection**
  is the manual equivalent.
- **Human handoff has no outbound notification channel (email/Slack/etc.)
  yet.** `request_human_handoff` flags the conversation (`handoff_requested`/
  `handoff_reason` on graph state, plus a note on the most recent lead if
  one exists) and is visible in that lead's record and the Tool Activity
  log -- there's no push notification to a human yet. Wiring one in is a
  service-level addition (e.g. in `process_result`/`human_handoff` in
  `app/agents/graph.py`), not a change to the graph's shape.

---

## Production deployment notes

- Set real values for `ADMIN_USERNAME`, `ADMIN_PASSWORD`,
  `ADMIN_SECRET_KEY`, `TOKEN_HASH_SECRET`, and `ENCRYPTION_KEY` in
  `backend/.env` -- the defaults are for local development only.
  `ENCRYPTION_KEY` specifically protects every configured cloud provider's
  API key at rest; rotate it deliberately (re-entering provider keys
  afterward), not accidentally.
- Serve the backend behind HTTPS; set `CORS_ALLOWED_ORIGINS` to your real
  admin dashboard origin(s) only.
- Put `widget/dist/aria-widget.js` behind a CDN with a long cache lifetime
  plus a versioned filename or cache-busting query string, since it's
  meant to be embedded on third-party sites you don't control the deploy
  cadence of.
- Move rate limiting to Redis if running multiple backend workers/instances.
- Consider real admin authentication (OAuth/SSO) before exposing the admin
  API beyond a trusted network.
- Run more than one `worker/knowledge_worker.py` instance if ingestion
  volume grows -- job claiming is already safe for concurrent workers.
- Back up the Postgres volume; it now holds both application data and
  every embedded chunk, not just leads/sessions.
- Set `MAX_FILE_SIZE`/`ALLOWED_FILE_EXTENSIONS` deliberately rather than
  leaving development defaults, and put the backend behind a reverse proxy
  with its own upload size limit as a second layer of defense.
