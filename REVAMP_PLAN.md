# Analysis AI — Revamp Implementation Plan

**Stack:** Python · FastAPI · LangGraph · OpenAI Python SDK · MongoDB
**Sanitization:** external HTTP service (you build it; backend calls it)
**LLM provider:** OpenAI direct
**Audience:** backend engineer new to AI engineering — this plan teaches concepts as it builds.

> This is a **planning document only**. No application code is written yet. Each phase
> below is a self-contained learning unit; we build and verify one before starting the next.

---

## 0. Guiding principles

1. **Behavior-compatible, implementation-new.** We reproduce the documented pipeline
   (Upload → Sanitize → BRD → Prompt → Planning → Notebook → Summary) but rebuild it in Python.
2. **Keep the REST API contract** close to the original so your frontend can talk to it
   with minimal changes.
3. **LangGraph where it shines** — modeling the agent's reasoning loop as a declarative
   graph — while keeping cross-stage progression explicit and easy to reason about.
4. **Incremental + verifiable.** Every phase ends with something you can run and see work.

---

## 1. Tech stack & libraries (and *why* each)

| Concern | Library | Why |
|--------|---------|-----|
| Web framework | **FastAPI** | Async, Pydantic-native, auto OpenAPI docs (replaces NestJS+Swagger) |
| ASGI server | **uvicorn** | Runs FastAPI |
| Agent/workflow runtime | **langgraph** | Declarative state-machine for agent logic |
| LLM calls | **openai** (Python SDK) | Direct chat/responses API, tokens, streaming |
| LangGraph + OpenAI glue | **langchain-openai** | `ChatOpenAI` model object LangGraph nodes use |
| MongoDB driver | **motor** (async) + **beanie** (ODM) | Beanie = Pydantic models *as* Mongo documents; less boilerplate than raw Motor |
| Validation/schemas | **pydantic v2** | Request/response DTOs + structured LLM output |
| Config | **pydantic-settings** | Typed env-var config (replaces ad-hoc `process.env`) |
| File parsing | **pypdf**, **python-docx** | PDF/DOCX text extraction (replaces pdf-parse/mammoth) |
| HTTP client | **httpx** | Async calls to your sanitization service |
| Tests | **pytest**, **pytest-asyncio** | Unit/integration tests |

---

## 2. Target architecture

```
analysis-ai/
├── app/
│   ├── main.py                  # FastAPI app + startup (DB init)
│   ├── core/
│   │   ├── config.py            # Settings (env vars) via pydantic-settings
│   │   └── logging.py
│   ├── db/
│   │   └── mongo.py             # Beanie/Motor connection + init
│   ├── models/                  # Beanie documents (= Mongo collections)
│   │   ├── analysis.py
│   │   ├── analysis_file.py
│   │   ├── stage_document.py
│   │   ├── stage_chat.py
│   │   ├── agent_prompt.py
│   │   ├── agent_run.py
│   │   └── dictionaries.py      # curated + vendor business dictionaries
│   ├── schemas/                 # Pydantic DTOs (API request/response)
│   ├── repositories/            # data-access layer (one per collection)
│   ├── services/
│   │   ├── analysis_service.py  # create/list/get/start
│   │   ├── pipeline_service.py  # stage progression + persistence orchestration
│   │   ├── sanitizer_client.py  # httpx client → your sanitization service
│   │   ├── dictionary_service.py# curated/vendor lookups → context text
│   │   ├── summary_service.py
│   │   └── file_extractor.py    # txt/pdf/docx → text
│   ├── agents/                  # ← AI layer
│   │   ├── llm.py               # OpenAI client / ChatOpenAI factory + per-stage model config
│   │   ├── outputs.py           # Pydantic schemas for structured agent output
│   │   └── prompts.py           # default system prompts per stage (seed data)
│   ├── graph/                   # ← LangGraph layer
│   │   ├── state.py             # StageState TypedDict
│   │   ├── tools.py             # dictionary-lookup tool
│   │   └── stage_graph.py       # the per-stage agent graph (nodes + edges)
│   └── api/                     # FastAPI routers
│       ├── analyses.py
│       ├── sanitization.py
│       ├── stages.py
│       ├── summary.py
│       └── prompts.py
├── tests/
├── .env.example
├── pyproject.toml
└── docker-compose.yml           # mongo + backend (+ your sanitizer service)
```

---

## 3. Data model (MongoDB, carried from the spec)

Same 8 collections as `PROJECT_DOCUMENTATION.md`, now expressed as **Beanie documents**:
`analyses`, `analysis_files`, `stage_documents`, `stage_chat_messages`,
`agent_prompts`, `agent_runs`, `curated_business_dictionary`, `vendor_business_dictionary`.

Enums to define centrally (in `models` or `schemas`):
- `Stage`: `brd | prompt | planning | notebook`
- `AnalysisStatus`: `created | sanitization | running | completed | failed`
- `AnalysisType`: `curated | vendor`

> **Learning note:** with Beanie, a Mongo document *is* a Pydantic class. You get
> validation, typing, and `await Analysis.get(id)` style access — the repository
> classes wrap these to keep business logic out of the API layer.

---

## 4. The LangGraph design — the heart of the revamp

### 4.1 What we model with LangGraph
A **single agent "turn"** within any stage. When a user sends a chat message (or the
stage auto-runs), we run a small graph that:

1. **assembles context** (system prompt + prior stage docs + dictionary + current draft + user msg)
2. **calls the LLM**, which may **call a tool** (look up business-dictionary entries)
3. **loops** back if a tool was called, otherwise
4. **produces structured output**: `{ content, create_document: bool, message_to_user }`

### 4.2 The State (`graph/state.py`)
```text
StageState (TypedDict):
  stage:            Stage
  analysis_id:      str
  system_prompt:    str
  prior_context:    str          # previous stage docs + goals, pre-rendered
  dictionary_text:  str          # curated/vendor context, pre-rendered
  current_draft:    str | None   # latest stage document, if any
  messages:         list         # running LLM message list (LangGraph `add_messages`)
  result:           StageResult | None   # structured final output
```

### 4.3 Nodes & edges
```
        ┌─────────────┐
        │ build_input │   assemble system+context+history+user msg
        └──────┬──────┘
               ▼
        ┌─────────────┐
        │  call_model │   LLM (bound with dictionary tool + structured output)
        └──────┬──────┘
               ▼
        ╔═════════════╗   conditional edge:
        ║  did it call ║──── yes ──▶ ┌──────────┐
        ║   a tool?    ║             │ run_tool │──┐ (loops back to call_model)
        ╚══════╤══════╝             └──────────┘  │
               │ no                                │
               ▼                ◀──────────────────┘
        ┌─────────────┐
        │  finalize   │   parse structured output → StageResult
        └──────┬──────┘
               ▼
             END
```

**Concepts this teaches you:**
- *Nodes* = pure functions `(state) -> partial update`
- *Conditional edges* = routing based on state (the tool-calling loop)
- *Tool calling* = the LLM requesting `lookup_dictionary(table)` and us executing it
- *Structured output* = forcing a Pydantic shape so `create_document` is reliable

### 4.4 How stages reuse one graph
All four stages share the **same graph**; only the inputs differ
(system prompt, which prior docs are included, whether the dictionary is attached).
`pipeline_service` builds the right `StageState` per stage and invokes the compiled graph.

> **Why not one giant pipeline graph with human-in-the-loop interrupts?**
> That's the advanced/"fully LangGraph-native" evolution (using `interrupt()` +
> MongoDB checkpointer keyed by `analysis_id`). It's powerful but harder to map to
> "manual edit vs. chat vs. next." We start with the per-stage graph (clearer, matches
> the REST contract) and note the upgrade path in Phase 8.

---

## 5. REST API contract (kept close to original)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/analyses` | create analysis, extract+sanitize files |
| GET | `/analyses` | paginated list (cursor, status, stage filters) |
| GET | `/analyses/{id}` | metadata for resume |
| POST | `/analyses/{id}/start` | lock sanitization → status running, stage brd |
| GET | `/analyses/{id}/sanitization` | original + sanitized text per file |
| POST | `/analyses/{id}/sanitization` | update sanitized text (only while in sanitization) |
| GET | `/analyses/{id}/stages/{stage}` | latest doc + chat history |
| POST | `/analyses/{id}/stages/{stage}` | manual edit (`newText`) OR chat (`newChat`) → runs graph |
| POST | `/analyses/{id}/next` | advance brd→prompt→planning→notebook→completed |
| GET | `/analyses/{id}/summary` | all stage outputs combined |
| GET/POST | `/prompts`, `/prompts/{stage}`, `/prompts/{stage}/activate/{id}` | prompt admin/versioning |

FastAPI auto-generates Swagger UI at `/docs` (replaces NestJS Swagger).

---

## 6. Sanitization integration

You own the sanitization service. The backend treats it as a black box over HTTP:

- `services/sanitizer_client.py` — async `httpx` POST to `SANITIZER_URL` with `{ "text": ... }`,
  expects back entities + anonymized text (shape per the spec's `/ner` contract).
- Called during `POST /analyses` for each extracted file; we store `originalText`,
  `sanitisedText`, `issuesCount`.
- Backend is resilient if the service is down (configurable: fail vs. store raw + flag).

When you define your service's exact response shape, we lock the client's Pydantic model to it.

---

## 7. Phased build roadmap (each phase = a runnable milestone + a lesson)

| Phase | What we build | What you learn | "Done" looks like |
|------|----------------|----------------|-------------------|
| **0. Bootstrap** | `pyproject.toml`, folders, `config.py`, `main.py`, health route | project layout, typed settings, FastAPI basics | `GET /health` returns 200, `/docs` loads |
| **1. Database** | Mongo connection, Beanie models, repositories | async Mongo, ODM, repository pattern | app starts, collections init, a smoke CRUD test passes |
| **2. First LLM call** | `agents/llm.py`, a throwaway script calling OpenAI | OpenAI SDK, messages, tokens, errors | a script prints a model reply + token usage |
| **3. First LangGraph node** | minimal graph: build_input → call_model → finalize (no tools) | State, nodes, edges, compile/invoke | invoke graph in a test, get a `StageResult` |
| **4. BRD stage end-to-end** | analyses create/start, file extract, stub sanitize, BRD via graph, persistence, GET/POST stage endpoints | wiring AI into a real request lifecycle | upload a txt → start → chat → BRD doc saved + returned |
| **5. Tools + dictionary** | dictionary collections, `lookup_dictionary` tool, tool-loop edge | tool calling, conditional edges | Prompt stage agent looks up tables on demand |
| **6. Remaining stages + next** | Prompt/Planning/Notebook nodes, `/next`, notebook `.ipynb` validation | reuse one graph across stages, prompt-per-stage config | full pipeline brd→…→notebook→completed |
| **7. Sanitizer + summary + prompts admin** | real sanitizer HTTP client, summary endpoint, prompt versioning | service integration, audit/versioning | sanitization view works; summary aggregates all stages |
| **8. Hardening + Docker (+ optional)** | error handling, agent_run audit logging, tests, docker-compose; *optional:* LangGraph checkpointer/interrupts | observability, containerization, advanced LangGraph | `docker compose up` runs mongo+backend; tests green |

---

## 8. Configuration (`.env`)

```bash
# Server
PORT=3000
# Mongo
MONGODB_URI=mongodb://localhost:27017
DB_NAME=analysisai
# Sanitizer (your service)
SANITIZER_URL=http://localhost:8000/ner
# OpenAI
OPENAI_API_KEY=sk-...
# Per-stage models (sensible current defaults)
BRD_AGENT_MODEL=gpt-4.1
PROMPT_AGENT_MODEL=gpt-4.1
PLANNING_AGENT_MODEL=gpt-4.1
NOTEBOOK_AGENT_MODEL=gpt-4.1
SUMMARY_AGENT_MODEL=gpt-4.1
```
(Model names finalized in Phase 2 against what your OpenAI account has access to.)

---

## 9. Testing strategy

- **Unit:** repositories (mongomock or a test DB), services, graph nodes with a **fake LLM**
  (LangChain's `FakeListChatModel`) so tests don't hit the network or cost money.
- **Integration:** FastAPI `TestClient` against key endpoints with the fake LLM wired in.
- **Manual:** `/docs` Swagger UI for exploratory testing each phase.

---

## 10. Open items to confirm before Phase 0

1. **Frontend contract** — share the frontend files so we match request/response shapes exactly.
2. **Sanitizer response shape** — your service's exact JSON (so we lock the client model).
3. **Auth** — none in the original; add API-key/JWT now or later?
4. **Notebook execution** — original only *generates* `.ipynb`; do we also need to *run* it?
```
