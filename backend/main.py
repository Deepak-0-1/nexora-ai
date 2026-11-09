import json
import uuid
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool
from backend.config import CORS_ORIGINS
from backend.db import connect, init_db
from backend.ollama_client import stream_chat, chat_once, check_ollama, OllamaError
from backend.context import build_messages, runtime_settings
from backend.jobs import enqueue_job, start_worker, stop_worker
from backend.memory import (
    create_memory, update_memory, approve_memory, archive_memory,
    delete_memory, list_memories, get_memory_history
)
from backend.schemas import (
    ChatRequest, ConversationCreate, MemoryCreate, MemoryUpdate,
    ProfileUpdate, SettingsUpdate
)

from backend.app.tools.registry import registry
from backend.app.agents.orchestrator import orchestrator
from backend.app.agents.state import RunStatus

app = FastAPI(title="Personal AI Assistant API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()
    start_worker()

@app.on_event("shutdown")
def shutdown():
    stop_worker()

@app.get("/health")
def health():
    try:
        check_ollama()
        ollama = "connected"
    except OllamaError as exc:
        ollama = str(exc)
    with connect() as c:
        pending = c.execute("SELECT COUNT(*) FROM memory_jobs WHERE status='pending'").fetchone()[0]
    return {"status": "ok" if ollama == "connected" else "degraded",
            "ollama": ollama, "pending_background_jobs": pending}

@app.get("/api/conversations")
def conversations(search: str | None = Query(default=None, max_length=200)):
    with connect() as c:
        if search:
            rows = c.execute(
                """SELECT DISTINCT c.id,c.title,c.created_at,c.updated_at
                   FROM conversations c LEFT JOIN messages m ON m.conversation_id=c.id
                   WHERE c.title LIKE ? OR m.content LIKE ?
                   ORDER BY c.updated_at DESC LIMIT 100""",
                (f"%{search}%", f"%{search}%")
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT id,title,created_at,updated_at FROM conversations ORDER BY updated_at DESC LIMIT 100"
            ).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/conversations")
def create_conversation(body: ConversationCreate):
    cid = str(uuid.uuid4())
    with connect() as c:
        c.execute("INSERT INTO conversations(id,title) VALUES(?,?)",
                  (cid, body.title.strip() or "New chat"))
    return {"id": cid, "title": body.title.strip() or "New chat"}

@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    with connect() as c:
        cur = c.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Conversation not found")
    return {"deleted": True}

@app.get("/api/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str):
    with connect() as c:
        if not c.execute("SELECT 1 FROM conversations WHERE id=?", (conversation_id,)).fetchone():
            raise HTTPException(404, "Conversation not found")
        rows = c.execute(
            "SELECT id,role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id",
            (conversation_id,)
        ).fetchall()
    return [dict(r) for r in rows]

@app.patch("/api/messages/{message_id}")
def edit_message(message_id: int, body: dict):
    content = str(body.get("content", "")).strip()
    if not content or len(content) > 12000:
        raise HTTPException(400, "Message must contain 1-12000 characters")
    with connect() as c:
        row = c.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Message not found")
        c.execute("UPDATE messages SET content=? WHERE id=?", (content, message_id))
        c.execute(
            "UPDATE conversations SET updated_at=datetime('now') WHERE id=?",
            (row["conversation_id"],)
        )
    return {"updated": True}

def _save_assistant_message(conversation_id: str, answer: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)",
            (conversation_id, "assistant", answer)
        )
        c.execute(
            "UPDATE conversations SET updated_at=datetime('now') WHERE id=?",
            (conversation_id,)
        )


async def _compose_agent_response(conversation_id: str, user_text: str, state) -> str:
    """Turn structured tool outputs into a grounded assistant response."""
    tool_outputs = []
    if state.plan:
        for step in state.plan.steps:
            tool_outputs.append({
                "tool": step.tool_name,
                "description": step.description,
                "success": step.status.value == "completed",
                "result": step.result if step.status.value == "completed" else step.error
            })

    messages = build_messages(conversation_id, user_text)
    messages[0]["content"] += (
        "\n\nTOOL USE POLICY:\n"
        "Use the tool results below as the source of truth. Do not claim an action "
        "succeeded unless its result says it succeeded. If a result is incomplete, "
        "state the limitation. Never invent missing values. Give a concise answer."
    )
    messages.append({
        "role": "user",
        "content": "The following are results from tools you executed for my request. "
                   "Explain the outcome and answer my request using these results:\n"
                   + json.dumps(tool_outputs, ensure_ascii=False, default=str)[:24000]
    })
    return await run_in_threadpool(
        chat_once,
        messages,
        temperature=float(runtime_settings()["temperature"]),
        num_predict=900
    )


@app.post("/api/chat/stream")
def chat_stream(body: ChatRequest):
    user_text = body.message.strip()
    with connect() as c:
        conv = c.execute("SELECT id,title FROM conversations WHERE id=?",
                         (body.conversation_id,)).fetchone()
        if not conv:
            raise HTTPException(404, "Conversation not found")
        history_rows = c.execute(
            "SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 8",
            (body.conversation_id,)
        ).fetchall()
        history = [{"role": row["role"], "content": row["content"]} for row in reversed(history_rows)]
        cur = c.execute(
            "INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)",
            (body.conversation_id, "user", user_text)
        )
        user_message_id = cur.lastrowid
        count = c.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id=?",
            (body.conversation_id,)
        ).fetchone()[0]
        if count == 1 and conv["title"] == "New chat":
            c.execute(
                "UPDATE conversations SET title=?,updated_at=datetime('now') WHERE id=?",
                (user_text[:60], body.conversation_id)
            )

    async def generate():
        chunks = []
        try:
            yield "data: " + json.dumps({"tool_status": "planning"}, ensure_ascii=False) + "\n\n"
            state = await orchestrator.initialize_run(
                body.conversation_id, user_text, history
            )

            if state.status == RunStatus.FAILED:
                answer = "I couldn't safely plan the requested tool actions: " + (state.error or "Unknown planning error")
                _save_assistant_message(body.conversation_id, answer)
                yield "data: " + json.dumps({"token": answer}, ensure_ascii=False) + "\n\n"
                yield "data: " + json.dumps({"done": True}) + "\n\n"
                return

            if state.plan and state.plan.steps:
                yield "data: " + json.dumps({"agent_status": "executing"}, ensure_ascii=False) + "\n\n"
                async for event in orchestrator.run_until_complete_or_blocked(state.run_id):
                    event_type = event.get("type")
                    if event_type == "step_started":
                        step = event.get("step", {})
                        yield "data: " + json.dumps({
                            "tool_status": "started",
                            "tool_name": step.get("tool_name"),
                            "description": step.get("description")
                        }, ensure_ascii=False) + "\n\n"
                    elif event_type == "step_completed":
                        step = event.get("step", {})
                        yield "data: " + json.dumps({
                            "tool_status": "completed",
                            "tool_name": step.get("tool_name")
                        }, ensure_ascii=False) + "\n\n"
                    elif event_type == "waiting_approval":
                        step = event.get("step", {})
                        yield "data: " + json.dumps({
                            "approval_required": {
                                "run_id": state.run_id,
                                "step_id": step.get("step_id"),
                                "tool_name": step.get("tool_name"),
                                "arguments": step.get("arguments", {})
                            }
                        }, ensure_ascii=False) + "\n\n"
                        return

                if state.status == RunStatus.FAILED:
                    answer = "The requested tool operation failed: " + (state.error or "Unknown tool error")
                else:
                    answer = await _compose_agent_response(body.conversation_id, user_text, state)
                _save_assistant_message(body.conversation_id, answer)
                yield "data: " + json.dumps({"token": answer}, ensure_ascii=False) + "\n\n"
            else:
                messages = build_messages(body.conversation_id, user_text)
                async for token in iterate_in_threadpool(
                    stream_chat(messages, temperature=float(runtime_settings()["temperature"]))
                ):
                    chunks.append(token)
                    yield "data: " + json.dumps({"token": token}, ensure_ascii=False) + "\n\n"
                answer = "".join(chunks).strip()
                _save_assistant_message(body.conversation_id, answer)

            with connect() as c:
                message_count = c.execute(
                    "SELECT COUNT(*) FROM messages WHERE conversation_id=?",
                    (body.conversation_id,)
                ).fetchone()[0]
            enqueue_job("extract_memory", {
                "conversation_id": body.conversation_id,
                "message_id": user_message_id,
                "user_text": user_text
            })
            if message_count >= 20 and message_count % 10 == 0:
                enqueue_job("summarize", {"conversation_id": body.conversation_id})
            yield "data: " + json.dumps({"done": True}) + "\n\n"
        except Exception as exc:
            logger.exception("Chat request failed")
            yield "data: " + json.dumps({"error": str(exc)}, ensure_ascii=False) + "\n\n"

    return StreamingResponse(
        generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.post("/api/chat/agent/{run_id}/approve")
async def approve_chat_agent_step(run_id: str, payload: dict):
    """Approve one gated tool step, resume the run, and return its final answer."""
    step_id = payload.get("step_id")
    if step_id is None:
        raise HTTPException(400, "Missing 'step_id'")
    state = orchestrator.get_run(run_id)
    if not state:
        raise HTTPException(404, "Agent run not found")
    if not orchestrator.approve_step(run_id, int(step_id)):
        raise HTTPException(400, "Unable to approve this agent step")

    waiting = None
    async for event in orchestrator.run_until_complete_or_blocked(run_id):
        if event.get("type") == "waiting_approval":
            waiting = event
            break
    if waiting:
        step = waiting.get("step", {})
        return {"approval_required": {
            "run_id": run_id,
            "step_id": step.get("step_id"),
            "tool_name": step.get("tool_name"),
            "arguments": step.get("arguments", {})
        }}

    if state.status == RunStatus.FAILED:
        answer = "The requested tool operation failed: " + (state.error or "Unknown tool error")
    elif state.status == RunStatus.CANCELLED:
        raise HTTPException(409, "Agent run was cancelled")
    else:
        answer = await _compose_agent_response(state.conversation_id, state.user_query, state)
    _save_assistant_message(state.conversation_id, answer)
    with connect() as c:
        latest_user = c.execute(
            "SELECT id FROM messages WHERE conversation_id=? AND role='user' ORDER BY id DESC LIMIT 1",
            (state.conversation_id,)
        ).fetchone()
        message_count = c.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id=?",
            (state.conversation_id,)
        ).fetchone()[0]
    if latest_user:
        enqueue_job("extract_memory", {
            "conversation_id": state.conversation_id,
            "message_id": latest_user["id"],
            "user_text": state.user_query
        })
    if message_count >= 20 and message_count % 10 == 0:
        enqueue_job("summarize", {"conversation_id": state.conversation_id})
    return {"answer": answer, "status": state.status.value}


@app.get("/api/memories")
def memories(status: str | None = None):
    if status and status not in {"pending", "active", "archived", "deleted"}:
        raise HTTPException(400, "Invalid memory status")
    return list_memories(status)

@app.post("/api/memories")
def add_memory(body: MemoryCreate):
    try:
        result = create_memory(
            body.memory_type, body.category, body.content, body.importance,
            body.confidence, status="active", user_approved=True
        )
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@app.patch("/api/memories/{memory_id}")
def patch_memory(memory_id: int, body: MemoryUpdate):
    changes = body.model_dump(exclude_none=True)
    result = update_memory(memory_id, changes)
    if result is None:
        raise HTTPException(404, "Memory not found")
    return result

@app.post("/api/memories/{memory_id}/approve")
def approve(memory_id: int, body: dict | None = None):
    result = approve_memory(memory_id, replace_conflict=bool((body or {}).get("replace_conflict", False)))
    if result is None:
        raise HTTPException(404, "Memory not found")
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result

@app.post("/api/memories/{memory_id}/archive")
def archive(memory_id: int):
    if not archive_memory(memory_id):
        raise HTTPException(404, "Memory not found")
    return {"archived": True}

@app.delete("/api/memories/{memory_id}")
def remove_memory(memory_id: int):
    if not delete_memory(memory_id):
        raise HTTPException(404, "Memory not found")
    return {"deleted": True}

@app.get("/api/memories/{memory_id}/history")
def memory_history(memory_id: int):
    return get_memory_history(memory_id)

@app.get("/api/profile")
def get_profile():
    with connect() as c:
        row = c.execute("SELECT profile_json,updated_at FROM user_profile WHERE id=1").fetchone()
    return {"profile": json.loads(row["profile_json"]), "updated_at": row["updated_at"]}

@app.patch("/api/profile")
def patch_profile(body: ProfileUpdate):
    with connect() as c:
        row = c.execute("SELECT profile_json FROM user_profile WHERE id=1").fetchone()
        profile = json.loads(row["profile_json"]) if row else {}
        updates = body.model_dump(exclude_unset=True)
        profile.update(updates)
        c.execute(
            """INSERT INTO user_profile(id,profile_json,updated_at) VALUES(1,?,datetime('now'))
               ON CONFLICT(id) DO UPDATE SET profile_json=excluded.profile_json,updated_at=datetime('now')""",
            (json.dumps(profile, ensure_ascii=False),)
        )
    return {"profile": profile}

@app.get("/api/settings")
def get_settings():
    with connect() as c:
        rows = c.execute("SELECT key,value_json FROM app_settings").fetchall()
    return {r["key"]: json.loads(r["value_json"]) for r in rows}

@app.patch("/api/settings")
def patch_settings(body: SettingsUpdate):
    allowed = {"temperature", "max_recent_messages", "max_context_memories", "max_context_chars", "personalization_enabled"}
    invalid = set(body.values) - allowed
    if invalid:
        raise HTTPException(400, f"Unsupported settings: {', '.join(sorted(invalid))}")
    ranges = {
        "temperature": (0.0, 1.0),
        "max_recent_messages": (2, 30),
        "max_context_memories": (1, 30),
        "max_context_chars": (4000, 50000),
    }
    for key, value in body.values.items():
        if key == "personalization_enabled":
            if not isinstance(value, bool):
                raise HTTPException(400, "personalization_enabled must be true or false")
            continue
        low, high = ranges[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not low <= value <= high:
            raise HTTPException(400, f"{key} must be between {low} and {high}")
    with connect() as c:
        for key, value in body.values.items():
            c.execute(
                """INSERT INTO app_settings(key,value_json) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json""",
                (key, json.dumps(value))
            )
    return get_settings()

@app.get("/api/jobs")
def background_jobs():
    with connect() as c:
        rows = c.execute(
            "SELECT id,job_type,status,attempts,error,created_at,updated_at FROM memory_jobs ORDER BY id DESC LIMIT 50"
        ).fetchall()
    return [dict(r) for r in rows]

# --- V3 Agent, Tools & Artifact APIs ---

@app.get("/api/tools")
def list_available_tools():
    """Lists all registered tools and their schema definitions."""
    return registry.get_schemas()

@app.post("/api/agent/runs")
async def create_agent_run(payload: dict):
    """Initializes an agent execution run with planning for a user request."""
    conversation_id = payload.get("conversation_id", "default")
    user_query = payload.get("query", "")
    if not user_query:
        raise HTTPException(400, "Query cannot be empty")

    state = await orchestrator.initialize_run(conversation_id, user_query)
    return state.model_dump()

@app.get("/api/agent/runs/{run_id}")
def get_agent_run(run_id: str):
    """Retrieves current state of an agent execution run."""
    state = orchestrator.get_run(run_id)
    if not state:
        raise HTTPException(404, f"Agent run '{run_id}' not found")
    return state.model_dump()

@app.post("/api/agent/runs/{run_id}/approve")
def approve_agent_step(run_id: str, payload: dict):
    """Approves a blocked high-impact step (e.g. email sending, code execution)."""
    step_id = payload.get("step_id")
    if step_id is None:
        raise HTTPException(400, "Missing 'step_id'")
    success = orchestrator.approve_step(run_id, int(step_id))
    if not success:
        raise HTTPException(400, f"Unable to approve step {step_id} on run '{run_id}'")
    return {"status": "approved", "run_id": run_id, "step_id": step_id}

@app.post("/api/agent/runs/{run_id}/cancel")
def cancel_agent_run(run_id: str):
    """Cancels an active agent run."""
    success = orchestrator.cancel_run(run_id)
    if not success:
        raise HTTPException(404, f"Agent run '{run_id}' not found")
    return {"status": "cancelled", "run_id": run_id}

@app.get("/api/agent/runs/{run_id}/stream")
async def stream_agent_run(run_id: str):
    """SSE stream of step executions, results, and approval checkpoints for a run."""
    async def event_generator():
        async for event in orchestrator.run_until_complete_or_blocked(run_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/artifacts")
def list_artifacts():
    """Lists all generated reports (Excel, Word, PDF)."""
    with connect() as c:
        rows = c.execute("SELECT * FROM generated_artifacts ORDER BY created_at DESC LIMIT 50").fetchall()
        return [dict(r) for r in rows]

