# Personal AI Assistant v2

Local single-user conversational assistant with:
- React + TypeScript + Tailwind CSS frontend
- FastAPI backend
- Ollama chat model (`phi4-mini:3.8b`)
- Ollama embeddings (`nomic-embed-text`)
- SQLite persistent conversations, messages, profile and memories
- Memory approval, editing, archiving, deletion and conflict review
- Memory provenance, confidence and history
- Semantic + lexical memory retrieval
- Background extraction and conversation summarization
- SSE token streaming
- Conversation search
- Local evaluation tests

## 1. Prerequisites

- Windows 10/11
- Python 3.10+ (3.11 recommended)
- Node.js 20 LTS or newer and npm
- Ollama installed and running

Pull the models:

```powershell
ollama pull phi4-mini:3.8b
ollama pull nomic-embed-text
```

## 2. Important: preserve your existing database

This project is an upgrade of the earlier `local-ai-chatbot` project. It supports the earlier SQLite schema and migrates it in place.

Before starting, copy your existing database into this project's `data` folder:

```powershell
New-Item -ItemType Directory -Force .\data | Out-Null
Copy-Item "C:\path\to\your\old\local-ai-chatbot\data\chatbot.db" ".\data\chatbot.db"
```

Replace the source path with the actual path to your existing database. Stop the old backend before copying. If you want a fresh database, skip this step.

The backend attempts a timestamped SQLite backup before schema initialization. Still keep your own backup; do not rely on an automatic migration backup as your only copy.

## 3. Start backend

Open PowerShell in the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run_backend.ps1
```

Backend: `http://127.0.0.1:8000`
API docs: `http://127.0.0.1:8000/docs`
Health: `http://127.0.0.1:8000/health`

## 4. Start React frontend

Open a second PowerShell window in the project root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run_frontend.ps1
```

Open `http://localhost:5173`.

If `npm` is not recognized, install Node.js 20 LTS or newer and reopen PowerShell.

## 5. Configuration

Edit `.env` in the project root. Restart the backend after changes.

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi4-mini:3.8b
OLLAMA_EMBED_MODEL=nomic-embed-text
DATABASE_PATH=./data/chatbot.db
MAX_RECENT_MESSAGES=12
MAX_CONTEXT_MEMORIES=8
MAX_CONTEXT_CHARS=18000
SUMMARY_TRIGGER_MESSAGES=20
OLLAMA_NUM_CTX=8192
OLLAMA_TEMPERATURE=0.4
```

## 6. Memory behavior

Newly extracted memories enter **Pending review**. Approve them to make them eligible for future retrieval. This reduces the chance that a mistaken extraction silently becomes personalization.

Memory records contain type, category, confidence, importance, source conversation, source message, status, timestamps and optional supersession links. When a new memory appears to conflict with an active memory in the same category, the UI marks it for review. Approving an update archives the older record.

Memory types:
- `semantic`: stable facts, skills, goals and project facts
- `procedural`: response preferences and instructions
- `episodic`: conversation summaries saved as reviewable memories and retrievable across conversations

The retrieval system uses stored embeddings, cosine similarity, lexical overlap, importance and confidence. Inactive, pending, archived and deleted records are not used as active context. Once an episodic summary is approved, it can be retrieved in a different conversation.

Background jobs are stored in SQLite. A lightweight text-cue gate skips memory extraction for ordinary one-off questions. A single worker processes remaining jobs sequentially. Chat inference, embedding calls and background inference share a lock, preventing simultaneous Ollama calls from competing for CPU/RAM. Background jobs can therefore wait until the current chat response finishes.

## 7. Evaluation

With the backend environment activated:

```powershell
python -m pytest
```

Tests cover memory scoring, conflict candidate selection, profile validation and context limits. They do not test real model quality; run the application against your Ollama models for end-to-end evaluation.

## 8. Data and privacy

All application data is stored in `data/chatbot.db`. Ollama runs locally by default. The API binds to `127.0.0.1`; do not expose it to your network without adding authentication and appropriate security controls.

Back up the database regularly. To restore, stop the backend and replace the database file with your backup.

## 9. Current limitations

- Single-user local application; no authentication or account isolation.
- Memory extraction is probabilistic; pending approval is the safeguard.
- Conflict detection is a review aid, not a guarantee of logical contradiction detection.
- Semantic retrieval quality depends on the embedding model.
- Background extraction and summarization share the same Ollama model and can add delay to background processing.
- No document RAG, voice, web search or external tool execution in this version.
