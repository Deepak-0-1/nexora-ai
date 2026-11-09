# Personal AI Assistant V3

A locally hosted, autonomous personal AI assistant and agent platform that combines conversational intelligence, long-term memory, modular tool execution, internet research, SQL query analysis, Excel/CSV manipulation, document RAG, sandboxed Python computation, report generation, and automated task scheduling.

---

## 1. Core Architecture Overview

Personal AI Assistant V3 is structured as a multi-tier, modular agent system:

```text
                                USER
                                  │
                                  ▼
                         React + TypeScript UI
                                  │
                                  ▼
                         FastAPI API Layer
                                  │
                                  ▼
                         Agent Orchestrator
                       ┌──────────┴──────────┐
                       ▼                     ▼
                 Task Planner         Memory Manager
                       └──────────┬──────────┘
                                  ▼
                        Unified Tool Registry
     ┌───────────────┬────────────┴───────────┬───────────────┐
     ▼               ▼                        ▼               ▼
 Web Search     SQL Assistant            Excel/CSV      Document RAG
& Extraction  (Read-Only Safe)            Analytics     (PDF/DOCX/MD)
     │               │                        │               │
     ▼               ▼                        ▼               ▼
Python Sandbox  File Management         Report Gen     Task Scheduler
(Subprocess)    (Boundary Safe)        (DOCX/PDF/XLSX)  & Reminders
```

---

## 2. Capabilities & Tools Implemented

### 🧠 1. Long-Term Memory & Personalization (Phase 1 & 2)
- **Memory Categories**: Semantic (facts/skills), Procedural (user preferences/workflow habits), and Episodic (cross-conversation summaries).
- **Approval Workflow**: Extracted candidates are gated in `pending` review to prevent false personalization.
- **Hybrid Retrieval**: Combines cosine similarity from local embeddings (`nomic-embed-text`) with lexical keyword overlap.
- **Conflict Review**: Automatic conflict detection and supersession tracking.

### ⚙️ 2. Tool Registry & Agent Orchestration (Phase 3)
- **Standardized Tool Contract**: Defined using Pydantic schemas, validation, execution timeouts, and auto-generated LLM metadata.
- **Permission Level Hierarchy**:
  - `read_only` (e.g., search, file reading)
  - `analysis` (e.g., SQL SELECT, CSV profiling)
  - `generate` (e.g., Word, PDF, Excel report creation)
  - `modify` (e.g., file copy, schedule creation)
  - `external_write` (e.g., send email — **requires approval**)
  - `destructive` (e.g., file removal, database changes — **requires confirmation**)
  - `execute_code` (e.g., Python execution — **requires approval**)
- **Agent Orchestrator & Planner**: Multi-step plan generation with pause/resume execution and human-in-the-loop checkpoints.

### 🌐 3. Web Search & Deep Research (Phase 4)
- **SSRF & Security Shield**: Rejects loopback (`127.0.0.1`, `localhost`), link-local, and RFC1918 private subnets (`10.x`, `172.16-31.x`, `192.168.x`).
- **Clean HTML Extractor**: Strips scripts, styles, and tags while preserving paragraphs and unescaping entities.
- **Pluggable Search Providers**: Configurable support for Tavily (`TAVILY_API_KEY`), Brave (`BRAVE_SEARCH_API_KEY`), SerpAPI (`SERPAPI_API_KEY`), or a zero-dependency DuckDuckGo HTML fallback.
- **Tools**:
  - `web_search`: Perform searches with titles, URLs, and snippets.
  - `open_url`: Fetch web pages with size-limit guards (5 MB max) and extract clean readable text.

### 🗄️ 4. SQL Assistant & Database Connectivity (Phase 5)
- **Security & Injection Shield**: Comment stripping (`--` and `/* */`), stacked query rejection, and strict blocking of write/DDL keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `PRAGMA`).
- **Read-Only Connections**: Connects in read-only mode (`mode=ro`).
- **Tools**:
  - `list_database_connections`: Enumerate configured databases.
  - `list_database_tables`: Inspect schema tables and views.
  - `describe_database_table`: Retrieve column types, nullability, and primary keys.
  - `execute_sql_query`: Safely execute validated queries with row limits (up to 500 rows).

### 📊 5. Excel & CSV Analytics (Phase 6)
- **File Boundary Guard**: Restricts operations to approved project directories and temp paths.
- **Data Profiling**: Computes row/column counts, missing value percentages, distinct counts, numeric distributions (mean, std, min, max, median), and duplicate row detection.
- **Tools**:
  - `list_excel_sheets`: Enumerate sheets in `.xlsx` workbooks.
  - `preview_data_file`: Preview first N rows of CSV or Excel files.
  - `profile_data_file`: Comprehensive statistical and data quality profiling.
  - `create_excel_report`: Generate formatted multi-sheet Excel workbooks (*Executive Summary* and *Detailed Data* sheets with styling and column auto-fitting).

### 📄 6. Document Assistant & RAG (Phase 7)
- **Multi-Format Ingestion**: Supports PDF (`pypdf`), Word (`python-docx`), Markdown (`.md`), and plain text (`.txt`).
- **Sliding-Window Chunking**: Splits content into configurable overlapping chunks while retaining document and page numbers.
- **Hybrid Retrieval**: Ranks chunks based on lexical matching and cosine vector similarity using local Ollama embeddings (`nomic-embed-text`).
- **Tools**:
  - `index_document`: Ingest documents into SQLite `documents` and `document_chunks` tables.
  - `search_documents`: Retrieve cited answers with document names and page references (e.g. `report.pdf (p. 3)`).

### 🐍 7. Python Sandbox & File Management (Phase 8)
- **Static AST Analysis**: Blocks dangerous OS primitives (`os.system`, `subprocess`, `ctypes`, `winreg`, `shutil.rmtree`, etc.).
- **Subprocess Isolation**: Executes Python scripts in a separate process in `./sandbox/` with timeouts and stdout/stderr capture.
- **Tools**:
  - `execute_python`: Run Python computations and return execution output.
  - `list_files`: Safely list directories with recursive exploration.
  - `read_file`: Read source code or text files with truncation controls.
  - `copy_file`: Copy files within approved project boundaries.

### 📑 8. Multi-Format Report Generation & Integrations (Phase 9)
- **Document Generation**:
  - `generate_docx_report`: Generate formatted Microsoft Word documents (`.docx`) with headings and bullet points.
  - `generate_pdf_report`: Generate clean PDF documents (`.pdf`) via ReportLab.
- **Artifact Tracking**: Generated reports are saved to `data/generated/` and registered in the `generated_artifacts` database table.
- **External Communications**:
  - `draft_email`: Prepare drafts with recipient, subject, and body.
  - `send_email`: Send emails (`PermissionLevel.EXTERNAL_WRITE`, requires approval).

### ⏰ 9. Voice & Automation Scheduler (Phase 10)
- **Task Scheduling**: Manage one-time reminders and recurring workflows with status tracking (`active`, `paused`, `completed`).
- **Execution History**: Audit logs for automation triggers stored in `automation_runs`.
- **Tools**:
  - `create_reminder`: Schedule a reminder for a specific date and time.
  - `create_schedule`: Register recurring automated tasks (requires approval).
  - `list_schedules`: View active and paused schedules.

---

## 3. Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Tailwind CSS, Vite |
| **Backend** | Python 3.10+ (tested on Python 3.13), FastAPI, Uvicorn |
| **Database** | SQLite (WAL mode, busy timeout, foreign keys) |
| **LLM Runtime** | Ollama (`phi4-mini:3.8b` for chat, `nomic-embed-text` for embeddings) |
| **Document Processing** | PyMuPDF / pypdf, python-docx |
| **Excel & Data** | pandas, openpyxl |
| **Report Generation** | reportlab, python-docx, openpyxl |
| **Testing** | pytest, anyio, starlette testclient, httpx |

---

## 4. Directory Structure

```text
local-ai-chatbot-v2/
│
├── backend/
│   ├── app/
│   │   ├── config.py                 # Tool configuration & PermissionLevel enum
│   │   │
│   │   ├── agents/                   # Agent intelligence layer
│   │   │   ├── state.py              # AgentState, AgentPlan, AgentStep schemas
│   │   │   ├── planner.py            # LLM planning and JSON plan parser
│   │   │   └── orchestrator.py       # Multi-step orchestrator & approval checkpoints
│   │   │
│   │   ├── tools/                    # Modular tool implementations
│   │   │   ├── base.py               # BaseTool contract & ToolResult
│   │   │   ├── registry.py           # Centralized ToolRegistry
│   │   │   ├── web/                  # web_search, open_url, HTML extractor
│   │   │   ├── sql/                  # execute_sql, list_tables, describe_table
│   │   │   ├── excel/                # preview, profile, create_excel_report
│   │   │   ├── documents/            # index_document, search_documents (RAG)
│   │   │   ├── python/               # execute_python (sandboxed)
│   │   │   ├── files/                # list_files, read_file, copy_file
│   │   │   ├── reports/              # generate_docx, generate_pdf, email tools
│   │   │   └── automations/          # create_reminder, create_schedule, list_schedules
│   │   │
│   │   ├── security/                 # System security guards
│   │   │   ├── path_validator.py     # SSRF and private IP blocking
│   │   │   ├── sql_validator.py      # Strict read-only SQL validation
│   │   │   ├── file_validator.py     # File traversal guards
│   │   │   └── sandbox.py            # Python static code analyzer
│   │   │
│   │   └── integrations/             # External service connectors
│   │       ├── search_provider.py    # Multi-provider web search
│   │       ├── database_connectors.py# SQLite & relational DB connector
│   │       └── external_services.py  # Integrations manager (email, etc.)
│   │
│   ├── config.py                     # Environment configuration
│   ├── db.py                         # Internal SQLite database schema & migrations
│   ├── main.py                       # FastAPI application & V3 endpoints
│   ├── memory.py                     # Long-term memory extraction & retrieval
│   ├── ollama_client.py              # Ollama chat, embeddings, and connection pooling
│   └── jobs.py                       # Background task processing queue
│
├── frontend/                         # React + TypeScript single-page app
│   ├── src/
│   │   ├── components/               # ChatPage, MemoryPage, SettingsPage, Sidebar
│   │   ├── services/                 # API client
│   │   └── types.ts                  # TypeScript interface definitions
│   └── package.json
│
├── data/                             # Persistent storage
│   ├── chatbot.db                    # Internal application database
│   ├── uploads/                      # Uploaded files
│   ├── generated/                    # Generated Excel, Word, and PDF reports
│   ├── document_index/               # Document index files
│   └── backups/                      # Automatic migration backups
│
├── sandbox/                          # Isolated execution workspace for Python tools
├── tests/                            # Automated test suite (35+ unit & integration tests)
├── .env.example                      # Configuration template
├── run_backend.ps1                   # Backend startup script
├── run_frontend.ps1                  # Frontend startup script
└── README.md                         # Documentation
```

---

## 5. Prerequisites & Getting Started

### 1. Prerequisites
- **OS**: Windows 10/11, macOS, or Linux
- **Python**: 3.10+ (Python 3.11–3.13 supported)
- **Node.js**: 20 LTS or newer
- **Ollama**: Installed and running locally

Pull required Ollama models:
```powershell
ollama pull phi4-mini:3.8b
ollama pull nomic-embed-text
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and adjust settings as needed:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi4-mini:3.8b
OLLAMA_EMBED_MODEL=nomic-embed-text
DATABASE_PATH=./data/chatbot.db

# Optional Web Search Providers (falls back to DuckDuckGo if omitted):
# TAVILY_API_KEY=your_key_here
# BRAVE_SEARCH_API_KEY=your_key_here
# SERPAPI_API_KEY=your_key_here
```

### 3. Start Backend
```powershell
# In PowerShell:
Set-ExecutionPolicy -Scope Process Bypass
.\run_backend.ps1
```
- API Base: `http://127.0.0.1:8000`
- Swagger Docs: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

### 4. Start React Frontend
In a separate terminal:
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run_frontend.ps1
```
Open `http://localhost:5173` in your browser.

---

## 6. V3 API Endpoints Reference

### Agent Orchestration & Tools
- `GET /api/tools`: List all registered tools with their descriptions and JSON argument schemas.
- `POST /api/agent/runs`: Initiate an agent run with automatic plan generation for a natural language request.
- `GET /api/agent/runs/{id}`: Inspect the status, current step, and plan of an agent run.
- `GET /api/agent/runs/{id}/stream`: Real-time Server-Sent Events (SSE) streaming step results, execution logs, and approval checkpoints.
- `POST /api/agent/runs/{id}/approve`: Approve an action currently paused at a human approval checkpoint.
- `POST /api/agent/runs/{id}/cancel`: Cancel an active agent run.

### Artifacts & Reports
- `GET /api/artifacts`: List all generated artifacts (Excel workbooks, Word docs, PDF reports) with file sizes, timestamps, and download paths.

### Conversations & Chat
- `GET /api/conversations`: List all conversation threads.
- `POST /api/conversations`: Create a new conversation.
- `POST /api/chat`: Send a message with SSE streaming response.

### Memories
- `GET /api/memories`: Filter memories by status (`active`, `pending`, `archived`).
- `POST /api/memories/{id}/approve`: Approve a pending memory.
- `DELETE /api/memories/{id}`: Delete a memory record.

---

## 7. Running Tests

The test suite covers unit tests, security validators, document parsing, tool execution, and the agent orchestrator.

Run all tests:
```powershell
.venv\Scripts\python.exe -m pytest
```

Run test suite with detailed output:
```powershell
.venv\Scripts\python.exe -m pytest -v
```

All 35 automated tests verify:
- Safe URL & SSRF filtering
- Read-only SQL query validation and comment stripping
- Subprocess Python sandbox execution and pattern blocking
- File traversal protection
- PDF, Word, and Excel generation and data profiling
- Document RAG indexing and cited search
- Multi-step agent planning and human approval checkpoints

---

## 8. Security & Privacy

1. **Local Isolation**: All chat inference, memory indexing, and document retrieval operate locally via Ollama and SQLite.
2. **Approval Enforcement**: Destructive operations, arbitrary code execution, and external communications (e.g. sending emails) cannot be executed without explicit user confirmation.
3. **Database Safeguards**: Database connections are read-only by default, and queries are checked against strict AST and regex rules.
4. **Local Network Protection**: Web tools block connections to internal/private IP ranges and localhost to eliminate SSRF vulnerabilities.

---

## 9. Current Limitations & Scope

- **Single-User Local Application**: Designed for single-user local deployment; does not implement multi-tenant authentication or user account isolation.
- **Probabilistic Memory Extraction**: Extraction uses an LLM gate; the pending approval workflow serves as the primary safeguard before memories affect future context.
- **Hardware & Inference Concurrency**: Chat, tool planning, and embedding inference share Ollama resources sequentially to avoid CPU/RAM thrashing on consumer hardware.
- **External Write Safeguards**: Real external communication tools (like SMTP email sending) default to dry-run simulation mode until live credentials are explicitly registered.
- **UI Tool Integration**: All tools and multi-step agent orchestration are fully implemented, tested, and exposed via FastAPI (`/api/tools`, `/api/agent/runs`); advanced visual stepper cards in the React frontend can be further customized.

