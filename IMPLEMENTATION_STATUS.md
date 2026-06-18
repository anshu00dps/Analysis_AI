# Implementation Status — Phases 2-7 Complete

## Completed

### ✅ Phase 2 — LLM Layer (`app/agents/`)

- **`outputs.py`** — `StageResult` Pydantic schema (content, create_document, message_to_user)
- **`llm.py`** — `get_chat_model(stage)` factory that reads per-stage model config and returns `ChatOpenAI` instance
- **`prompts.py`** — `load_active_prompt(stage)` and `seed_prompts_from_json()` for prompt versioning

### ✅ Phase 3 — LangGraph (`app/graph/`)

- **`state.py`** — `StageState` TypedDict with fields: stage, analysis_id, system_prompt, prior_context, dictionary_text, current_draft, messages, result
- **`tools.py`** — `@tool lookup_dictionary(table_name)` stub (returns empty; wired up in Phase 5)
- **`stage_graph.py`** — Compiled LangGraph with four nodes:
  - `build_input` — assembles SystemMessage + context + HumanMessage
  - `call_model` — calls LLM with bound tools
  - `run_tool` — executes tool calls, appends ToolMessage results
  - `finalize` — parses structured output as StageResult
  - Edges: START→build_input→call_model→[conditional]→run_tool/finalize; run_tool loops back to call_model

### ✅ Phase 4 — Schemas & DTOs (`app/schemas/`)

- **`common.py`** — BaseSchema with camelCase aliasing, ListResponse envelope
- **`analysis.py`** — CreateAnalysisRequest, AnalysisResponse, ListAnalysesResponse, AnalysisFileView
- **`stage.py`** — PostStageRequest, StageResponse, ChatMessageView, StageDocumentView
- **`sanitization.py`** — SanitizationResponse, UpdateSanitizationRequest

**Features:**
- All DTOs use camelCase aliases (e.g., `analysisInfo`, `newChat`) via `alias_generator=to_camel`
- `populate_by_name=True` allows both camelCase and snake_case in requests
- File uploads encoded as base64 in JSON body

### ✅ Phase 4 — Repositories

- **`stage_documents_repo.py`** — `latest_for_stage()`, `list_for_stage()`
- **`stage_chat_repo.py`** — `list_for_stage()`
- **`agent_prompt_repo.py`** — `get_active()`, `deactivate_all()`, `list_for_agent()`
- **`agent_run_repo.py`** — `list_for_analysis()`
- **`dictionary_repo.py`** — `CuratedDictionaryRepo`, `VendorDictionaryRepo` with table/vendor lookups

### ✅ Phase 4 — Core Services

- **`file_extractor.py`** — Extract text from .txt, .pdf, .docx files
- **`analysis_service.py`** — create/list/get/start analysis; handles file extraction + sanitization
- **`dictionary_service.py`** — `build_context_text(analysis)` → formatted dictionary context per type
- **`pipeline_service.py`** — `run_stage()` — orchestrates LangGraph invocation, logs agent_runs, persists docs + chat
- **`summary_service.py`** — `build_summary()` — aggregates all stage docs

### ✅ Phase 4 — REST API (`app/api/`)

**`analyses.py`:**
- `POST /analyses` — create analysis with files (base64)
- `GET /analyses` — list with cursor pagination, filters
- `GET /analyses/{id}` — metadata
- `POST /analyses/{id}/start` — sanitization → running
- `POST /analyses/{id}/next` — advance stage

**`stages.py`:**
- `GET /analyses/{id}/stages/{stage}` — doc + chat history
- `POST /analyses/{id}/stages/{stage}` — run via chat or manual edit

**`sanitization.py`:**
- `GET /analyses/{id}/sanitization` — file view
- `POST /analyses/{id}/sanitization` — update sanitised_text

**`summary.py`:**
- `GET /analyses/{id}/summary` — all stages + metadata

**`prompts.py`:**
- `GET /prompts` — list all
- `GET /prompts/{stage}` — list for stage
- `POST /prompts/{stage}` — create (inactive)
- `POST /prompts/{stage}/activate/{id}` — activate + deactivate others
- `POST /prompts/seed` — seed from JSON file

**Status codes:** 201 (created), 200 (ok), 400 (validation), 404 (not found), 409 (conflict), 500 (server error)

### ✅ App Bootstrap

- Updated `app/main.py` to register all 5 new routers

## Still To Do

### Phase 5 — Tool Loop Activation

The `lookup_dictionary` tool in `app/graph/tools.py` is a stub. Wire it to:
1. Receive `table_name` string from LLM
2. Query `CuratedDictionaryRepo` or `VendorDictionaryRepo` based on analysis type
3. Format and return field list

**File to update:** `app/graph/tools.py` — implement real lookup with dependency injection

### Phase 8 — Hardening & Tests

**Missing:**
- `tests/test_file_extractor.py` — unit tests for extraction logic
- `tests/test_pipeline_service.py` — integration tests with `FakeListChatModel` (no real LLM calls)
- Better error handling: HTTP exceptions for validation, 422 for request parsing
- Analysis status guard in `run_stage` (currently basic)
- Agent audit logging (AgentRun creation could be more detailed)

## API Contract Summary

### File Upload Format (Base64 JSON)

```json
{
  "analysisInfo": {"name": "...", "description": "..."},
  "analysisGoals": {"primary": "..."},
  "analysisType": "curated",
  "vendorDetails": [],
  "curatedTables": [],
  "files": [
    {
      "filename": "transcript.txt",
      "content": "base64-encoded-bytes"
    }
  ]
}
```

### Stage Chat/Edit

```json
{
  "newChat": "What are the key themes?"
}
// or
{
  "newText": "# Custom BRD\n..."
}
```

### Responses (CamelCase)

```json
{
  "id": "...",
  "analysisInfo": {...},
  "analysisGoals": {...},
  "analysisType": "curated",
  "status": "running",
  "stage": "brd",
  "createdAt": "2026-06-18T..."
}
```

## Key Design Decisions

1. **Graph is synchronous** — `stage_graph.invoke()` not `ainvoke()`. LangGraph handles message list updates internally; we call it from async context but don't await graph internals.

2. **Manual edits skip the graph** — `new_text` → skip LLM, insert doc with `created_by=manual_edit`, log chat

3. **Prior context is hierarchical** — BRD has none; Prompt includes BRD; Planning includes BRD+Prompt; Notebook includes all

4. **Dictionary context assembled at run time** — not preloaded; built from analysis type + curated_tables/vendor_details each call

5. **Prompt activation is exclusive** — activating a prompt deactivates all others for that agent (one active per stage at a time)

6. **Agent runs logged after document creation** — audit trail tracks model, input, output tokens (filled later when token counting is added)

7. **No notebook execution** — `.ipynb` is generated as JSON string but not executed (as per original spec)

## Testing the Implementation

1. **With MongoDB + Sanitizer:**
   ```bash
   docker-compose up -d
   uvicorn app.main:app --reload --port 3000
   open http://localhost:3000/docs
   ```

2. **Create analysis, start, run BRD, advance:**
   - POST /analyses (with base64 files)
   - POST /analyses/{id}/start
   - POST /analyses/{id}/stages/brd (with newChat)
   - POST /analyses/{id}/next → moves to prompt
   - GET /analyses/{id}/summary

3. **With OpenAI API key in .env**, the LLM calls will work.

## Next Steps

1. **Wire `lookup_dictionary` tool** — connect to repos in Phase 5
2. **Test with real data** — upload transcript, run BRD agent
3. **Add tests** — pytest with fake LLM
4. **Monitor token usage** — populate AgentRun input/output_tokens
5. **Error handling polish** — Pydantic validation, 422 responses
