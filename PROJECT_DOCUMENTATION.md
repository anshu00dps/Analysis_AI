# Analysis AI - Complete Project Documentation

**Last Updated:** 2026-06-15

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Backend Details](#backend-details)
5. [Frontend Details](#frontend-details)
6. [Database Schema](#database-schema)
7. [Agent System](#agent-system)
8. [AI Models](#ai-models)
9. [Sanitization Service](#sanitization-service)
10. [Docker Setup](#docker-setup)
11. [API Routes](#api-routes)
12. [Workflow Pipeline](#workflow-pipeline)
13. [Environment Configuration](#environment-configuration)

---

## Project Overview

**Analysis AI** is a full-stack, LLM-powered document analysis platform that:

- Accepts uploaded documents (transcripts, emails, etc.)
- Sanitizes PII (Personally Identifiable Information) using NER (Named Entity Recognition)
- Processes content through an agentic pipeline with AI agents
- Generates structured outputs at each stage (BRD, Prompt, Planning, Notebook)
- Produces a summary view with all stage outputs

**Purpose:** Enable users to upload business documents and receive AI-generated analysis artifacts through a multi-stage workflow, with business dictionary context (curated or vendor-specific).

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Analysis AI Platform                     │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
   ┌─────────┐         ┌──────────┐       ┌──────────┐
   │ Frontend│         │ Backend  │       │Sanitizer │
   │ React   │         │ NestJS   │       │ Python   │
   │ Vite    │         │ Node.js  │       │ NER/spaCy│
   └────┬────┘         └────┬─────┘       └────┬─────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    ┌───────▼────────┐
                    │    MongoDB     │
                    │   (Persistent) │
                    └────────────────┘
```

### Key Components

1. **Frontend (React/Vite)** - User interface for document upload, editing, and viewing results
2. **Backend (NestJS)** - API server, agent orchestration, database management
3. **Sanitizer (Python)** - PII detection and anonymization service
4. **Database (MongoDB)** - Persistent storage for analyses, documents, dictionaries
5. **Agents (OpenAI)** - LLM-based agents for each pipeline stage

---

## Technology Stack

### Backend
- **Framework:** NestJS 10.x (Node.js)
- **Database ORM:** Mongoose 8.x (MongoDB)
- **API Documentation:** Swagger/OpenAPI
- **Agent SDK:** @openai/agents (OpenAI/Azure OpenAI)
- **File Processing:** 
  - `pdf-parse` - PDF extraction
  - `mammoth` - DOCX extraction
- **Utilities:** class-validator, class-transformer, uuid, RxJS

### Frontend
- **Framework:** React 18+ (with TypeScript)
- **Build Tool:** Vite
- **State Management:** Redux Toolkit
- **Styling:** Tailwind CSS
- **HTTP Client:** Axios
- **Server:** Nginx (in Docker)

### Infrastructure
- **Container:** Docker & Docker Compose
- **Database:** MongoDB 7
- **Sanitization:** Python (spaCy NER)
- **AI Provider:** OpenAI / Azure OpenAI

---

## Backend Details

### Architecture

```
Analysis-Service/
├── src/
│   ├── main.ts                 # Entry point
│   ├── app.module.ts           # NestJS module configuration
│   ├── ui.controller.ts        # Single controller with all routes
│   ├── agents/                 # Agent services
│   │   ├── brd-agent.service.ts
│   │   ├── prompt-agent.service.ts
│   │   ├── planning-agent.service.ts
│   │   ├── notebook-agent.service.ts
│   │   ├── agent.builder.js    # Agent construction logic
│   │   └── agent-run.repo.ts
│   ├── services/               # Business logic
│   │   ├── stages.service.ts   # Stage pipeline orchestration
│   │   └── summary.service.ts
│   ├── repos/                  # Data access layer
│   │   ├── analyses.repo.ts
│   │   ├── stage-documents.repo.ts
│   │   ├── stage-chat.repo.ts
│   │   ├── agent-run.repo.ts
│   │   ├── analysis-files.repo.ts
│   │   ├── vendor-business-dictionary.repo.ts
│   │   ├── curated-business-dictionary.repo.ts
│   │   └── agent-prompts.repo.ts
│   ├── schemas/                # MongoDB schemas
│   │   ├── analysis.schema.ts
│   │   ├── analysis-file.schema.ts
│   │   ├── stage-document.schema.ts
│   │   ├── stage-chat-message.schema.ts
│   │   ├── agent-prompt.schema.ts
│   │   ├── agent-run.schema.ts
│   │   ├── curated-business-dictionary.schema.ts
│   │   ├── vendor-business-dictionary.schema.ts
│   │   ├── enums.ts            # Stage, AnalysisStatus, etc.
│   │   └── summary.schema.ts
│   ├── dtos/                   # Request/Response DTOs
│   │   ├── requests.dto.ts
│   │   ├── analysis.dto.ts
│   │   ├── sanitization.dto.ts
│   │   ├── stage.dto.ts
│   │   ├── summary.dto.ts
│   │   └── prompt.dto.ts
│   └── common/                 # Utilities
│       └── notebook-validation.ts
├── Dockerfile
├── docker-compose.yml
├── package.json
└── tsconfig.json
```

### Key Services

#### 1. **StagesService** (`src/services/stages.service.ts`)
Orchestrates the entire agentic pipeline:
- Routes requests to appropriate agent handlers (BRD, Prompt, Planning, Notebook)
- Fetches vendor/curated dictionary data based on analysis type
- Prepares message context for agents
- Manages stage transitions
- Logs agent runs for audit trail

**Key Methods:**
- `postStage()` - Handle user chat or manual edits
- `handleBrdStage()` - Business Requirements Document
- `handlePromptStage()` - Query/prompt generation
- `handlePlanningStage()` - Planning document
- `handleNotebookStage()` - Jupyter notebook generation
- `addMetadata()` - Injects dictionary data into agent context

#### 2. **Agent Services** (BRD, Prompt, Planning, Notebook)
Each stage has a dedicated agent service that:
- Initializes the agent with model, instructions, and tools
- Executes agent.chat() with input messages
- Logs execution for auditing
- Returns content + metadata

**Example - BrdAgentService:**
```typescript
async chat(input: AgentInputItem[], analysisId?: Types.ObjectId) {
  const agent = await this.agentPromise;
  const result = await AgentBuilder.run(agent, input);
  await this.agentRunLog.create({ analysisId, agent: Stage.BRD, ... });
  return result;
}
```

#### 3. **Repository Pattern**
All data access is abstracted through repositories:
- **AnalysesRepo** - Analysis CRUD operations
- **StageDocumentsRepo** - Stage document versions
- **StageChatRepo** - Chat history
- **VendorBusinessDictionaryRepo** - Vendor dictionary lookups
- **CuratedBusinessDictionaryRepo** - Curated table lookups
- **AgentPromptsRepo** - Prompt versioning and activation

---

## Frontend Details

### Architecture

```
Analysis-Frontend/
├── src/
│   ├── main.tsx                # Entry point
│   ├── App.tsx                 # Root component
│   ├── pages/                  # Page components
│   │   ├── HomePage.tsx        # List of analyses
│   │   ├── CreateAnalysis.tsx  # Upload & settings
│   │   ├── Sanitization.tsx    # PII review & editing
│   │   ├── Stage.tsx           # BRD/Prompt/Planning/Notebook stages
│   │   └── Summary.tsx         # Final summary view
│   ├── components/             # Reusable components
│   │   ├── FileUpload.tsx
│   │   ├── MarkdownEditor.tsx
│   │   ├── ChatPanel.tsx
│   │   ├── StageDocument.tsx
│   │   └── DocumentCards.tsx
│   ├── services/               # API clients
│   │   └── api.ts              # Axios-based HTTP client
│   ├── store/                  # Redux state management
│   │   ├── store.ts
│   │   ├── slices/
│   │   │   ├── analysisSlice.ts
│   │   │   ├── stageSlice.ts
│   │   │   └── uiSlice.ts
│   ├── types/                  # TypeScript interfaces
│   │   └── index.ts
│   ├── styles/                 # Tailwind CSS config
│   │   └── globals.css
│   └── hooks/                  # Custom React hooks
│       └── useAnalysis.ts
├── Dockerfile
├── vite.config.ts
├── tailwind.config.js
└── package.json
```

### Key Pages

#### 1. **HomePage**
- Lists all analyses with status and stage
- Pagination with cursor-based navigation
- Quick filters (status, stage)
- Resume/view actions

#### 2. **CreateAnalysis**
- Name and description input
- Goals definition (primary, secondary, additional)
- File upload (supports .txt, .pdf, .docx)
- Vendor/Curated dictionary selection
- Submits to `POST /analyses`

#### 3. **Sanitization Page**
- Shows uploaded files with original + sanitized text
- Highlights PII detected by sanitizer
- Edit interface for manual correction
- Can only edit when status = "sanitization"
- POST to `POST /analyses/:id/sanitization`

#### 4. **Stage Pages (BRD/Prompt/Planning/Notebook)**
- Displays latest stage document (full-screen editor for brd/prompt/planning)
- Chat panel for agent interaction
- Manual edit toggle
- Document preview
- Next/Previous navigation

#### 5. **Summary Page**
- Overview of all stages
- Download cards for artifacts
- Metadata about the analysis
- Model/prompt versions used

### State Management (Redux)

```typescript
// analysisSlice
{
  analyses: Analysis[],
  currentAnalysis: Analysis | null,
  loading: boolean,
  error: string | null
}

// stageSlice
{
  currentStage: Stage | null,
  documents: StageDocument[],
  chat: StageChatMessage[],
  loading: boolean
}

// uiSlice
{
  editMode: boolean,
  selectedFile: string | null,
  sidebarOpen: boolean
}
```

---

## Database Schema

### Collections

#### 1. **analyses**
Core analysis document
```typescript
{
  _id: ObjectId,
  analysisInfo: { name: string, description: string },
  analysisGoals: { primary: string, secondary?: string, additional?: string },
  analysisType: 'curated' | 'vendor',
  status: 'created' | 'sanitization' | 'running' | 'completed' | 'failed',
  stage: 'brd' | 'prompt' | 'planning' | 'notebook' | null,
  
  // Dictionary context
  vendorDetails?: [{ vendorName: string, layout: string[] }],
  curatedTables?: string[],
  
  // Generated summary
  analysisSummary?: string | null,
  
  // Timestamps
  createdAt: Date,
  updatedAt: Date
}
```

#### 2. **analysis_files**
Uploaded and sanitized files
```typescript
{
  _id: ObjectId,
  analysisId: ObjectId,
  filename: string,
  originalText: string,
  sanitisedText: string,
  issuesCount: number,
  createdAt: Date
}
```

#### 3. **stage_documents**
Versioned stage outputs
```typescript
{
  _id: ObjectId,
  analysisId: ObjectId,
  stage: 'brd' | 'prompt' | 'planning' | 'notebook',
  content: string (markdown or ipynb JSON),
  createdBy: 'agent' | 'manual_edit',
  notebookStatus?: 'draft' | 'final' | 'running' | 'error',
  dictionaryContext?: {
    curated?: { tables: string[], version?: string },
    vendor?: { vendors: [{ name: string, layouts: string[] }] }
  },
  createdAt: Date
}
```

#### 4. **stage_chat_messages**
Chat history per stage
```typescript
{
  _id: ObjectId,
  analysisId: ObjectId,
  stage: 'brd' | 'prompt' | 'planning' | 'notebook',
  chat: { role: 'user' | 'system' | 'agent', content: AgentInputItem[] },
  action: 'chat' | 'manual_edit',
  documentId?: ObjectId,
  createdAt: Date
}
```

#### 5. **agent_prompts**
System prompts for each stage
```typescript
{
  _id: ObjectId,
  agent: 'brd' | 'prompt' | 'planning' | 'notebook' | 'summary',
  systemPrompt: string,
  userPrompt?: string,
  active: boolean,
  createdAt: Date
}
```

#### 6. **agent_runs**
Audit log for agent executions
```typescript
{
  _id: ObjectId,
  analysisId: ObjectId,
  agent: 'brd' | 'prompt' | 'planning' | 'notebook',
  input: AgentInputItem[],
  output: string,
  inputTokens: number,
  outputTokens: number,
  createdAt: Date
}
```

#### 7. **curated_business_dictionary**
Curated data dictionary (static reference)
```typescript
{
  _id: ObjectId,
  tableName: string,
  fieldName: string,
  businessFriendlyName: string,
  dataType: string,
  nullableFlag: string,
  businessDescription: string,
  sampleValues: string,
  category: string,
  orderNum: number
}
```

#### 8. **vendor_business_dictionary**
Vendor-specific data dictionary
```typescript
{
  _id: ObjectId,
  vendorName: string,
  fileCategory: string,
  fieldName: string,
  businessFriendlyName: string,
  dataType: string,
  businessDescription: string,
  category: string,
  nullableFlag: string,
  protectedDataFlag: string,
  usageTags: string,
  glossaryTags: string,
  sampleValues: string,
  eddTag: string,
  filteringCondition: string
}
```

---

## Agent System

### Agent Architecture

Each stage has a dedicated agent service that:
1. Initializes the agent at service startup
2. Receives input messages from the orchestration layer
3. Executes the agent's chat function
4. Logs execution for auditing
5. Returns structured response

### How Agents Work

```
User Input (text/chat)
    ↓
StagesService.postStage()
    ↓
Prepare messages context:
  - System prompt (from DB)
  - User prompt (optional, from DB)
  - Previous stage content
  - Dictionary context (vendor/curated)
  - Current draft (if any)
  - New user message
    ↓
Call Agent (e.g., promptAgent.chat(messages))
    ↓
Agent processes with LLM:
  - Reads instructions
  - Analyzes context
  - Makes decisions
  - Generates output
    ↓
Returns { content, createDocument?, history }
    ↓
Backend stores:
  - Chat message (always)
  - Stage document (if createDocument=true)
    ↓
Response sent to frontend
```

### Agent Builder

Location: `src/agents/agent.builder.js`

```typescript
await AgentBuilder.create({
  name: 'BRD Agent',
  model: process.env.BRD_AGENT_MODEL || 'gpt-5.3-codex',
  instructions: 'You are a Senior Data Analyst...',
  enableMetadataTool: false,
  maxOutputTokens: 16000,
  reasoningEffort: "medium",
  verbosity: "medium"
})
```

### Stage-Specific Agent Flows

#### **BRD Agent**
- **Input:** Uploaded file transcripts
- **Task:** Create Business Requirements Document
- **Output:** Structured BRD with requirements, stakeholders, success criteria
- **Model:** `BRD_AGENT_MODEL` (default: gpt-5.3-codex)

#### **Prompt Agent**
- **Input:** BRD + Dictionary context (vendor/curated)
- **Task:** Generate structured data extraction queries/prompts
- **Output:** Query templates and extraction criteria
- **Model:** `PROMPT_AGENT_MODEL`

#### **Planning Agent**
- **Input:** BRD + Prompt + Previous planning docs
- **Task:** Create project planning/analysis plan
- **Output:** Timeline, milestones, resource allocation
- **Model:** `PLANNING_AGENT_MODEL`

#### **Notebook Agent**
- **Input:** All previous stages + Dictionary context
- **Task:** Generate Jupyter notebook with analysis code
- **Output:** ipynb JSON with code cells, markdown, visualizations
- **Model:** `NOTEBOOK_AGENT_MODEL`

---

## AI Models

### Model Configuration

Each stage has a configurable model via environment variables:

```bash
# Backend environment variables
BRD_AGENT_MODEL=gpt-5.3-codex              # Business Requirements
PROMPT_AGENT_MODEL=gpt-4-turbo              # Query/Prompt generation
PLANNING_AGENT_MODEL=gpt-4-turbo            # Planning documents
NOTEBOOK_AGENT_MODEL=gpt-4-turbo-vision     # Notebook generation
SUMMARY_AGENT_MODEL=gpt-4-turbo             # Summary generation
```

### Current Models

| Stage | Default Model | Purpose |
|-------|---------------|---------|
| BRD | gpt-5.3-codex | Requirements extraction |
| PROMPT | gpt-4-turbo | Query generation |
| PLANNING | gpt-4-turbo | Planning & scheduling |
| NOTEBOOK | gpt-4-turbo-vision | Code generation |
| SUMMARY | gpt-4-turbo | Content summarization |

### Model Audit

- Each stage document can store which model was used (`modelAudit` field)
- Agent runs log `inputTokens` and `outputTokens` for cost tracking
- Prompt versions are tracked in `agent_prompts` collection

### Provider Configuration

**OpenAI:**
```bash
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
```

**Azure OpenAI:**
```bash
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_BASE_URL=https://<instance>.openai.azure.com/
```

---

## Sanitization Service

### Purpose
Detect and anonymize Personally Identifiable Information (PII) in uploaded documents.

### Architecture

```
Frontend (file upload)
    ↓
Backend receives base64 text
    ↓
POST to Sanitizer service (Python)
    ↓
NER (Named Entity Recognition) processing
    ↓
Returns:
  - Detected entities (names, locations, etc.)
  - Anonymized text (with replacements)
  - Mapping of original → anonymized values
    ↓
Backend stores:
  - originalText (raw user input)
  - sanitisedText (anonymized)
  - issuesCount (entity count)
```

### Sanitizer Request/Response

**Request:**
```json
{
  "text": "John Doe works at Google in Mountain View"
}
```

**Response:**
```json
{
  "entities": [
    {
      "entity": "PERSON",
      "text": "John Doe",
      "start": 0,
      "end": 8,
      "confidence": 0.98
    },
    {
      "entity": "ORG",
      "text": "Google",
      "start": 18,
      "end": 24,
      "confidence": 0.95
    }
  ],
  "original_highlighted": "**John Doe** works at **Google** in **Mountain View**",
  "anonymized_highlighted": "**PERSON_1** works at **ORG_1** in **LOC_1**",
  "person_map": { "John Doe": "PERSON_1" }
}
```

### How Sanitization Works

1. **Text Extraction:** Backend extracts base64 uploaded file content
2. **NER Processing:** Python service uses spaCy/similar to detect:
   - PERSON names
   - ORG organizations
   - LOC locations
   - GPE geopolitical entities
   - DATE dates/times
   - Other sensitive patterns
3. **Anonymization:** Creates replacements (PERSON_1, ORG_2, etc.)
4. **Storage:** Both original and sanitized texts stored in MongoDB
5. **UI Display:** Frontend shows both versions side-by-side
6. **Editing:** User can manually correct before analysis starts
7. **Lock:** Once analysis starts (`POST /start`), sanitization is locked

### Sanitizer Technology

- **Framework:** Python with Flask/FastAPI
- **NLP:** spaCy (efficient, accurate NER)
- **Models:** Pre-trained spaCy models (en_core_web_sm or larger)
- **Container:** Docker (Python 3.9+)
- **Port:** 8000 (default)

### API Endpoint

```
POST http://localhost:8000/ner
Content-Type: application/json

{ "text": "..." }
```

### Configuration

```yaml
# docker-compose.yml
sanitise:
  build:
    context: ../Sanitisation%20Service
    dockerfile: Dockerfile
  ports:
    - "8000:8000"
  volumes:
    - hf_cache:/cache/huggingface  # Hugging Face cache
  networks:
    - analysisai-network
```

---

## Docker Setup

### Full Stack Docker Compose

**File:** `docker-compose.yml`

Orchestrates 4 services + 3 volumes:

#### **Services:**

1. **mongo** (Database)
   - Image: mongo:7
   - Port: 27017
   - Health check: mongosh ping
   - Volumes: mongo_data, mongo_config

2. **sanitise** (PII Detection)
   - Build: `../Sanitisation Service`
   - Port: 8000
   - Volumes: hf_cache (Hugging Face models)

3. **analysisai** (Backend API)
   - Build: current directory (Analysis-Service)
   - Port: 3000 (configurable via PORT env var)
   - Depends on: mongo, sanitise
   - Environment: All config variables

4. **frontend** (UI)
   - Build: `../Analysis-Frontend`
   - Port: 5173
   - Serves: Nginx (compiled React/Vite)
   - Depends on: analysisai

#### **Volumes:**
- `mongo_data`: MongoDB persistent data
- `mongo_config`: MongoDB configuration
- `hf_cache`: Hugging Face model cache

#### **Network:**
- Bridge network: `analysisai-network`
- All services communicate via service names (e.g., `mongo:27017`)

### Running Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f analysisai

# Stop all services
docker-compose down

# Remove volumes (cleanup)
docker-compose down -v
```

### Environment File (.env)

```bash
# Database
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=password

PORT=3000
MONGODB_URI=mongodb://admin:password@mongo:27017/analysisai?authSource=admin
DB_NAME=analysisai

# Sanitizer
SANITIZER_URL=http://sanitise:8000/ner

# AI Models
BRD_AGENT_MODEL=gpt-4-turbo
PROMPT_AGENT_MODEL=gpt-4-turbo
PLANNING_AGENT_MODEL=gpt-4-turbo
NOTEBOOK_AGENT_MODEL=gpt-4-turbo

# Azure OpenAI (or OpenAI)
AZURE_OPENAI_BASE_URL=https://your-instance.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
```

### Local Development

Without Docker:
```bash
# Install MongoDB locally
# Install Python dependencies (Sanitiser)
# Terminal 1: Start Sanitizer
cd "Sanitisation Service" && python app.py

# Terminal 2: Start Backend
cd Analysis-Service && npm run start:dev

# Terminal 3: Start Frontend
cd Analysis-Frontend && npm run dev
```

---

## API Routes

### Analysis Management

#### **POST /analyses** — Create Analysis
Creates analysis and uploads files

**Request:**
```json
{
  "analysisInfo": { "name": "Q4 Sales Analysis", "description": "..." },
  "analysisGoals": { "primary": "...", "secondary": "..." },
  "files": [
    { "filename": "transcript.txt", "content": "base64..." }
  ],
  "analysisType": "curated" | "vendor",
  "vendorDetails": [{ "vendorName": "Vendor A", "layout": ["table1", "table2"] }],
  "curatedTables": ["medical", "pharmacy"]
}
```

**Response:**
```json
{
  "analysisId": "507f1f77bcf86cd799439011",
  "status": "sanitization",
  "files": [
    { "fileId": "...", "filename": "...", "issuesCount": 5 }
  ]
}
```

#### **GET /analyses** — List Analyses
Paginated list of all analyses

**Query Params:**
- `limit?: number` (default 20)
- `cursor?: string` (for pagination)
- `status?: AnalysisStatus`
- `stage?: Stage`

**Response:**
```json
{
  "analyses": [
    {
      "analysisId": "...",
      "analysisInfo": { "name": "...", "description": "..." },
      "status": "running",
      "stage": "prompt",
      "createdAt": "2026-06-15T10:00:00Z"
    }
  ],
  "nextCursor": "..."
}
```

#### **GET /analyses/:analysisId** — Get Analysis Metadata
Returns analysis details for resume

#### **POST /analyses/:analysisId/start** — Start Analysis
Locks sanitization and moves to BRD stage

**Body:**
```json
{}
```

**Response:**
```json
{
  "status": "running",
  "stage": "brd"
}
```

---

### Sanitization

#### **GET /analyses/:analysisId/sanitization** — Get Sanitization View
Returns original + sanitized text per file

**Response:**
```json
{
  "files": [
    {
      "fileId": "...",
      "filename": "...",
      "originalText": "...",
      "sanitisedText": "...",
      "issuesCount": 5
    }
  ]
}
```

#### **POST /analyses/:analysisId/sanitization** — Update Sanitization
Overwrite sanitized text (only when status=sanitization)

**Request:**
```json
{
  "fileId": "...",
  "sanitisedText": "..."
}
```

---

### Stages (BRD / Prompt / Planning / Notebook)

#### **GET /analyses/:analysisId/stages/:stage** — Get Stage View
Returns latest document + chat history

**Response:**
```json
{
  "analysis": { ... },
  "latest": {
    "documentId": "...",
    "stage": "brd",
    "content": "# Business Requirements Document\n...",
    "createdAt": "2026-06-15T10:00:00Z"
  },
  "chat": [
    {
      "role": "user",
      "content": "Add a risks section",
      "createdAt": "2026-06-15T10:05:00Z"
    },
    {
      "role": "agent",
      "content": "# Updated BRD\n...",
      "documentId": "...",
      "createdAt": "2026-06-15T10:06:00Z"
    }
  ]
}
```

#### **POST /analyses/:analysisId/stages/:stage** — Update Stage
Either manual edit or agent chat

**Manual Edit:**
```json
{
  "newText": "# New content..."
}
```

**Chat:**
```json
{
  "newChat": "Please add a timeline section"
}
```

**Response:**
```json
{
  "chatMessage": { "id": "...", "role": "user", "content": "..." },
  "updatedDoc": { "id": "...", "content": "..." }
}
```

#### **POST /analyses/:analysisId/next** — Move to Next Stage
Advances: brd → prompt → planning → notebook → completed

**Request:**
```json
{
  "fromStage": "brd"
}
```

---

### Summary

#### **GET /analyses/:analysisId/summary** — Summary View
Returns all stage outputs combined

**Response:**
```json
{
  "analysisId": "...",
  "analysisInfo": { "name": "...", "description": "..." },
  "analysisGoals": { ... },
  "source": [{ "fileId": "...", "filename": "..." }],
  "latest": {
    "brd": { "content": "...", "createdAt": "..." },
    "prompt": { "content": "...", "createdAt": "..." },
    "planning": { "content": "...", "createdAt": "..." },
    "notebook": {
      "content": "...",
      "notebookStatus": "final",
      "createdAt": "..."
    }
  },
  "status": "completed",
  "stage": null
}
```

---

### Prompts (Admin)

#### **GET /prompts** — List All Prompts
Returns prompts for all stages

#### **GET /prompts/:stage** — Get Active Prompt
Returns currently active system+user prompts for a stage

#### **POST /prompts/:stage** — Create Prompt
Creates and optionally activates a prompt

**Request:**
```json
{
  "systemPrompt": "You are a BRD expert...",
  "userPrompt": "Consider tone and branding",
  "active": true
}
```

#### **POST /prompts/:stage/activate/:promptId** — Activate Prompt
Activates an existing prompt (deactivates others)

---

## Workflow Pipeline

### End-to-End Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. CREATE ANALYSIS                                      │
├─────────────────────────────────────────────────────────┤
│ User uploads files (txt, pdf, docx)                     │
│ Sets: name, goals, analysis type (curated/vendor)       │
│ POST /analyses                                          │
│ Status: "created" → "sanitization"                      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 2. SANITIZATION                                         │
├─────────────────────────────────────────────────────────┤
│ User reviews PII detected by NER service                │
│ Can manually edit or approve                            │
│ GET /analyses/:id/sanitization                          │
│ POST /analyses/:id/sanitization (optional edits)        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 3. START ANALYSIS                                       │
├─────────────────────────────────────────────────────────┤
│ POST /analyses/:id/start                                │
│ Status: "running", Stage: "brd"                         │
│ Sanitization locked                                     │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 4. BRD STAGE                                            │
├─────────────────────────────────────────────────────────┤
│ Agent Input:                                            │
│ - System prompt (from DB)                               │
│ - File transcripts                                      │
│ - User chat                                             │
│                                                         │
│ Agent Output: BRD document                              │
│ POST /analyses/:id/stages/brd (newChat)                 │
│ May ask clarifying questions (createDocument=false)     │
│ Or generate BRD (createDocument=true)                   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 5. NEXT TO PROMPT STAGE                                 │
├─────────────────────────────────────────────────────────┤
│ POST /analyses/:id/next                                 │
│ Stage: "prompt"                                         │
│ Previous BRD approved                                   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 6. PROMPT STAGE                                         │
├─────────────────────────────────────────────────────────┤
│ Agent Input:                                            │
│ - BRD content                                           │
│ - Dictionary context (vendor/curated tables)            │
│ - User chat                                             │
│                                                         │
│ Agent Output: Query/prompt templates                    │
│ POST /analyses/:id/stages/prompt (newChat)              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 7. NEXT TO PLANNING STAGE                               │
├─────────────────────────────────────────────────────────┤
│ POST /analyses/:id/next                                 │
│ Stage: "planning"                                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 8. PLANNING STAGE                                       │
├─────────────────────────────────────────────────────────┤
│ Agent Input:                                            │
│ - BRD + Prompt content                                  │
│ - Planning instructions                                 │
│ - User chat                                             │
│                                                         │
│ Agent Output: Project plan                              │
│ POST /analyses/:id/stages/planning (newChat)            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 9. NEXT TO NOTEBOOK STAGE                               │
├─────────────────────────────────────────────────────────┤
│ POST /analyses/:id/next                                 │
│ Stage: "notebook"                                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 10. NOTEBOOK STAGE                                      │
├─────────────────────────────────────────────────────────┤
│ Agent Input:                                            │
│ - All previous stages (BRD, Prompt, Planning)           │
│ - Dictionary context (vendor/curated)                   │
│ - Notebook generation instructions                      │
│ - User chat                                             │
│                                                         │
│ Agent Output: Jupyter notebook (ipynb JSON)             │
│ POST /analyses/:id/stages/notebook (newChat)            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 11. COMPLETION                                          │
├─────────────────────────────────────────────────────────┤
│ POST /analyses/:id/next                                 │
│ Status: "completed", Stage: null                        │
│ All artifacts frozen                                    │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 12. SUMMARY VIEW                                        │
├─────────────────────────────────────────────────────────┤
│ GET /analyses/:id/summary                               │
│ Shows all stage outputs                                 │
│ Download/export options                                 │
└─────────────────────────────────────────────────────────┘
```

### Detailed Stage Flow - PROMPT Example

```
┌──────────────────────────────────────────┐
│ User Types Chat: "Add query templates"   │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Frontend: POST /stages/prompt             │
│ { newChat: "Add query templates" }        │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Backend: handlePromptStage()              │
│ 1. Get analysis record                    │
│ 2. Get active system prompt               │
│ 3. Get BRD document                       │
│ 4. Call addMetadata():                    │
│    - Check analysis.analysisType          │
│    - If CURATED: fetch curated tables     │
│    - If VENDOR: fetch vendor layouts      │
│    - Format as markdown                   │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Build Message Array:                     │
│ [                                        │
│   { role: 'system', content: 'You are...'}
│   { role: 'user', content: 'BRD: ...'},  │
│   { role: 'user', content:                │
│     'Dictionary for tables medical...'}   │
│   { role: 'user', content:                │
│     'Add query templates' }               │
│ ]                                        │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Call Agent:                              │
│ promptAgent.chat(messages, analysisId)   │
│ LLM processes and generates response     │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Agent Response:                          │
│ {                                        │
│   content: "# Query Templates\n...",      │
│   createDocument: true,                  │
│   history: [...],                        │
│   usage: { inputTokens: 500, ... }       │
│ }                                        │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Backend Actions:                         │
│ 1. Create StageDocument (content)        │
│ 2. Store chat message (user)             │
│ 3. Store chat message (agent)            │
│ 4. Link chat to document via documentId  │
│ 5. Log agent run (audit)                 │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Response to Frontend:                    │
│ {                                        │
│   chatMessage: { id, role, content },    │
│   updatedDoc: {                          │
│     id, stage, content, createdAt        │
│   }                                      │
│ }                                        │
└──────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────┐
│ Frontend Updates:                        │
│ - Add user chat to chat panel            │
│ - Add agent response to chat panel       │
│ - Update document content                │
│ - Show "Next" button to advance stage    │
└──────────────────────────────────────────┘
```

---

## Environment Configuration

### Backend (.env)

```bash
# Server
PORT=3000

# Database
MONGODB_URI=mongodb://admin:password@mongo:27017/analysisai?authSource=admin
DB_NAME=analysisai

# Sanitizer Service
SANITIZER_URL=http://sanitise:8000/ner

# AI Models (per stage)
BRD_AGENT_MODEL=gpt-4-turbo
PROMPT_AGENT_MODEL=gpt-4-turbo
PLANNING_AGENT_MODEL=gpt-4-turbo
NOTEBOOK_AGENT_MODEL=gpt-4-turbo
SUMMARY_AGENT_MODEL=gpt-4-turbo

# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# OR Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_BASE_URL=https://<instance>.openai.azure.com/

# MCP Server (optional)
MCP_SERVER_URL=http://localhost:8001
MCP_USERNAME=admin
MCP_PASSWORD=password
```

### Frontend (.env)

```bash
# API Backend URL
VITE_API_URL=http://localhost:3000

# Optional: Environment
VITE_ENV=development
```

### Docker Compose (.env)

```bash
# MongoDB
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=password

# Application
PORT=3000
DB_NAME=analysisai
SANITIZER_URL=http://sanitise:8000/ner

# Models
BRD_AGENT_MODEL=gpt-4-turbo
PROMPT_AGENT_MODEL=gpt-4-turbo
PLANNING_AGENT_MODEL=gpt-4-turbo
NOTEBOOK_AGENT_MODEL=gpt-4-turbo

# Azure OpenAI
AZURE_OPENAI_BASE_URL=https://your-instance.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
```

---

## Key Features Summary

### ✅ Implemented
- Multi-stage agentic pipeline (BRD → Prompt → Planning → Notebook)
- PII sanitization with NER
- Vendor/Curated business dictionary integration
- Chat-based agent interaction
- Manual document editing
- Prompt versioning and activation
- Agent execution logging/audit trail
- Full API with Swagger documentation
- Responsive React UI with Redux state management
- Docker containerization for all services

### 🔄 Architecture Highlights
- **Agent per Stage:** Each pipeline stage has a dedicated LLM agent
- **Dictionary Context:** Agents receive business dictionary data as context
- **Flexible Models:** Model selection per stage via environment variables
- **Audit Trail:** All agent executions logged for compliance
- **Modular Design:** Repository pattern for data access, service layer for logic
- **Type Safety:** Full TypeScript for frontend and backend

---

## Getting Started (Local Development)

### 1. Clone Repository
```bash
git clone <repo-url>
cd Analysis_AI
```

### 2. Setup Backend
```bash
cd Analysis-Service
cp .env.example .env
npm install
npm run start:dev
```

### 3. Setup Sanitizer
```bash
cd ../Sanitisation\ Service
pip install -r requirements.txt
python app.py
```

### 4. Setup Frontend
```bash
cd ../Analysis-Frontend
npm install
npm run dev
```

### 5. Access Application
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:3000
- **API Docs:** http://localhost:3000/docs
- **Sanitizer:** http://localhost:8000

---

## Production Deployment

### Using Docker Compose
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Environment Setup
Ensure all `.env` variables are set before deployment:
- Database credentials
- API keys (OpenAI/Azure)
- Model names
- URLs

### Database Backup
```bash
# Backup MongoDB
docker-compose exec mongo mongodump --out /backup

# Restore MongoDB
docker-compose exec mongo mongorestore /backup
```

---

## Troubleshooting

### Agent not responding
- Check `AZURE_OPENAI_API_KEY` or `OPENAI_API_KEY`
- Verify model names are correct in environment
- Check agent logs: `docker-compose logs analysisai`

### Sanitizer failing
- Verify `SANITIZER_URL` is correct
- Check HF cache volume: `docker-compose logs sanitise`
- Ensure spaCy models are downloaded

### MongoDB connection errors
- Check MongoDB is running: `docker-compose logs mongo`
- Verify credentials in `.env`
- Check network connectivity

### Frontend not communicating
- Verify backend URL in frontend `.env`
- Check CORS is enabled (it is by default)
- Browser console for API errors

---

## Conclusion

Analysis AI is a comprehensive, production-ready AI-powered document analysis platform with:
- Robust multi-stage pipeline architecture
- Enterprise-grade security (PII sanitization)
- Flexible LLM integration
- Full auditability and compliance logging
- Modern tech stack (React, NestJS, MongoDB)
- Complete containerization

For questions or contributions, refer to the project repository and existing documentation files.
