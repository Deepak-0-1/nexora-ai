import json
import threading
import time
from backend.db import connect
from backend.config import BACKGROUND_POLL_SECONDS, SUMMARY_TRIGGER_MESSAGES
from backend.memory import extract_memory_records, should_extract_memory, upsert_episodic_summary
from backend.ollama_client import chat_once

_STOP = threading.Event()
_THREAD = None

def enqueue_job(job_type, payload):
    with connect() as c:
        cur = c.execute(
            "INSERT INTO memory_jobs(job_type,payload_json) VALUES(?,?)",
            (job_type, json.dumps(payload, ensure_ascii=False))
        )
        return cur.lastrowid

def _summarize(conversation_id):
    with connect() as c:
        count = c.execute(
            "SELECT COUNT(*) FROM messages WHERE conversation_id=?", (conversation_id,)
        ).fetchone()[0]
        if count < SUMMARY_TRIGGER_MESSAGES or count % 10 != 0:
            return
        rows = c.execute(
            "SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 30",
            (conversation_id,)
        ).fetchall()
        conv = c.execute(
            "SELECT summary FROM conversations WHERE id=?", (conversation_id,)
        ).fetchone()
    transcript = "\n".join(f"{r['role']}: {r['content']}" for r in reversed(rows))
    instruction = """Update a concise factual conversation summary for future context.
Preserve decisions, project facts, constraints and unresolved questions. Do not invent facts.
Maximum 1200 characters. Return only the summary."""
    summary = chat_once([
        {"role": "system", "content": instruction},
        {"role": "user", "content": "Existing summary:\n" + (conv["summary"] or "") +
         "\n\nRecent transcript:\n" + transcript}
    ], temperature=0.1, num_predict=400)
    with connect() as c:
        c.execute(
            "UPDATE conversations SET summary=?,updated_at=datetime('now') WHERE id=?",
            (summary[:4000], conversation_id)
        )
    upsert_episodic_summary(conversation_id, summary[:1200])

def _process(job):
    payload = json.loads(job["payload_json"])
    if job["job_type"] == "extract_memory":
        if should_extract_memory(payload["user_text"]):
            extract_memory_records(
                payload["conversation_id"], payload["message_id"], payload["user_text"]
            )
    elif job["job_type"] == "summarize":
        _summarize(payload["conversation_id"])

def _worker_loop():
    while not _STOP.is_set():
        job = None
        with connect() as c:
            job = c.execute(
                "SELECT * FROM memory_jobs WHERE status='pending' ORDER BY id LIMIT 1"
            ).fetchone()
            if job:
                c.execute(
                    "UPDATE memory_jobs SET status='processing',attempts=attempts+1,updated_at=datetime('now') WHERE id=?",
                    (job["id"],)
                )
        if not job:
            _STOP.wait(BACKGROUND_POLL_SECONDS)
            continue
        try:
            _process(job)
            with connect() as c:
                c.execute(
                    "UPDATE memory_jobs SET status='completed',updated_at=datetime('now') WHERE id=?",
                    (job["id"],)
                )
        except Exception as exc:
            with connect() as c:
                attempts = c.execute("SELECT attempts FROM memory_jobs WHERE id=?", (job["id"],)).fetchone()
                if attempts and attempts["attempts"] < 3:
                    c.execute(
                        "UPDATE memory_jobs SET status='pending',error=?,updated_at=datetime('now') WHERE id=?",
                        (str(exc)[:1000], job["id"])
                    )
                else:
                    c.execute(
                        "UPDATE memory_jobs SET status='failed',error=?,updated_at=datetime('now') WHERE id=?",
                        (str(exc)[:1000], job["id"])
                    )

def start_worker():
    global _THREAD
    if _THREAD and _THREAD.is_alive():
        return
    # Re-queue work that was in progress when the previous process stopped.
    with connect() as c:
        c.execute(
            "UPDATE memory_jobs SET status='pending',updated_at=datetime('now') WHERE status='processing'"
        )
    _STOP.clear()
    _THREAD = threading.Thread(target=_worker_loop, daemon=True, name="memory-worker")
    _THREAD.start()

def stop_worker():
    _STOP.set()
