import json
import math
import re
from backend.db import connect
from backend.ollama_client import chat_once, embed_text
from backend.config import MAX_CONTEXT_MEMORIES, OLLAMA_EMBED_MODEL


DURABLE_CUES = (
    "i am ", "i'm ", "i work ", "i use ", "i prefer ", "i like ",
    "i want ", "my goal", "my project", "our project", "we decided",
    "we use ", "from now on", "going forward", "remember that",
    "currently building", "i have started", "i am learning",
    "i've learned", "my profession", "my role is", "my name is",
    "i work as", "keep answers", "please be concise", "use concise",
    "always give", "from this point", "answer in bullet points"
)

def should_extract_memory(text):
    lowered = " " + text.lower().strip()
    return any(cue in lowered for cue in DURABLE_CUES)

EXTRACTION_PROMPT = """Extract durable information explicitly stated by the user in the message.
Do not infer sensitive traits. Never save credentials, secrets, medical details, or transient questions.
Return JSON only:
{"memories":[{"type":"semantic|procedural","category":"profile|skills|goals|projects|preferences|general","content":"one concise factual memory","importance":0.1,"confidence":0.9}]}
Use procedural for response preferences. Use semantic for stable facts, skills, goals and project facts.
Maximum 3 memories. If no durable information, return {"memories":[]}."""

def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return dot / (na*nb) if na and nb else 0.0

def lexical_similarity(a, b):
    wa = set(re.findall(r"\w+", a.lower()))
    wb = set(re.findall(r"\w+", b.lower()))
    return len(wa & wb) / max(1, len(wa | wb))

def log_history(conn, memory_id, action, old_content=None, new_content=None, details=None):
    conn.execute(
        """INSERT INTO memory_history(memory_id,action,old_content,new_content,details_json)
           VALUES(?,?,?,?,?)""",
        (memory_id, action, old_content, new_content, json.dumps(details or {}, ensure_ascii=False))
    )

def _find_conflict(conn, category, content, embedding):
    rows = conn.execute(
        """SELECT id,content,embedding FROM memories
           WHERE status='active' AND category=? ORDER BY updated_at DESC LIMIT 100""",
        (category,)
    ).fetchall()
    best = (0.0, None)
    for row in rows:
        try:
            old_vec = json.loads(row["embedding"]) if row["embedding"] else None
        except Exception:
            old_vec = None
        sem = cosine(embedding, old_vec) if embedding and old_vec else 0.0
        lex = lexical_similarity(content, row["content"])
        score = max(sem, lex)
        if score > best[0]:
            best = (score, row)
    return best[1] if best[0] >= 0.42 else None

def create_memory(memory_type, category, content, importance=0.6, confidence=0.8,
                  source_conversation_id=None, source_message_id=None, status="pending",
                  user_approved=False):
    content = content.strip()
    if not content:
        raise ValueError("Memory content cannot be empty")
    vector = embed_text(content)
    with connect() as c:
        conflict = _find_conflict(c, category, content, vector)
        conflict_id = conflict["id"] if conflict else None
        cur = c.execute(
            """INSERT INTO memories
               (memory_type,category,content,importance,confidence,embedding,source_conversation_id,
                active,status,source_message_id,user_approved,last_confirmed_at,conflict_with,embedding_model)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (memory_type, category, content, float(importance), float(confidence),
             json.dumps(vector) if vector else "", source_conversation_id,
             1 if status == "active" else 0, status, source_message_id,
             1 if user_approved else 0, None, conflict_id, OLLAMA_EMBED_MODEL if vector else "")
        )
        mid = cur.lastrowid
        log_history(c, mid, "created", None, content, {"status": status, "conflict_with": conflict_id})
        return {"id": mid, "status": status, "conflict_with": conflict_id}

def update_memory(memory_id, changes):
    with connect() as c:
        row = c.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            return None
        old = row["content"]
        content = changes.get("content", old)
        category = changes.get("category", row["category"])
        vector = embed_text(content) if content != old else (json.loads(row["embedding"]) if row["embedding"] else None)
        c.execute(
            """UPDATE memories SET content=?,category=?,importance=?,confidence=?,embedding=?,
               conflict_with=NULL,updated_at=datetime('now') WHERE id=?""",
            (content, category, changes.get("importance", row["importance"]),
             changes.get("confidence", row["confidence"]),
             json.dumps(vector) if vector else "", memory_id)
        )
        log_history(c, memory_id, "edited", old, content, changes)
        return dict(c.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone())

def approve_memory(memory_id, replace_conflict=False):
    with connect() as c:
        row = c.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            return None
        if row["status"] == "deleted":
            return {"error": "Deleted memories cannot be approved"}
        conflict_id = row["conflict_with"]
        if conflict_id and replace_conflict:
            old = c.execute("SELECT * FROM memories WHERE id=? AND status='active'", (conflict_id,)).fetchone()
            if old:
                c.execute(
                    """UPDATE memories SET status='archived',active=0,superseded_by=?,
                       updated_at=datetime('now') WHERE id=?""", (memory_id, conflict_id)
                )
                log_history(c, conflict_id, "superseded", old["content"], old["content"],
                            {"superseded_by": memory_id})
        c.execute(
            """UPDATE memories SET status='active',active=1,user_approved=1,
               last_confirmed_at=datetime('now'),updated_at=datetime('now') WHERE id=?""",
            (memory_id,)
        )
        log_history(c, memory_id, "approved", row["content"], row["content"],
                    {"superseded_memory_id": conflict_id if replace_conflict else None})
        return {"id": memory_id, "status": "active",
                "superseded_memory_id": conflict_id if replace_conflict else None,
                "possible_conflict_id": conflict_id}

def archive_memory(memory_id):
    with connect() as c:
        row = c.execute("SELECT content FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            return False
        c.execute(
            "UPDATE memories SET status='archived',active=0,updated_at=datetime('now') WHERE id=?",
            (memory_id,)
        )
        log_history(c, memory_id, "archived", row["content"], row["content"])
        return True

def delete_memory(memory_id):
    with connect() as c:
        row = c.execute("SELECT content FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            return False
        c.execute(
            "UPDATE memories SET status='deleted',active=0,updated_at=datetime('now') WHERE id=?",
            (memory_id,)
        )
        log_history(c, memory_id, "deleted", row["content"], None)
        return True

def list_memories(status=None):
    with connect() as c:
        if status:
            rows = c.execute(
                """SELECT id,memory_type,category,content,importance,confidence,status,
                   source_conversation_id,source_message_id,user_approved,created_at,updated_at,conflict_with
                   FROM memories WHERE status=? ORDER BY importance DESC,updated_at DESC""", (status,)
            ).fetchall()
        else:
            rows = c.execute(
                """SELECT id,memory_type,category,content,importance,confidence,status,
                   source_conversation_id,source_message_id,user_approved,created_at,updated_at,conflict_with
                   FROM memories WHERE status!='deleted' ORDER BY updated_at DESC"""
            ).fetchall()
    return [dict(r) for r in rows]

def retrieve_memories(query, limit=MAX_CONTEXT_MEMORIES):
    qvec = embed_text(query)
    with connect() as c:
        rows = c.execute(
            """SELECT id,memory_type,category,content,importance,confidence,embedding
               FROM memories WHERE status='active' AND active=1
               ORDER BY importance DESC,updated_at DESC LIMIT 300"""
        ).fetchall()
    scored = []
    for row in rows:
        try:
            vec = json.loads(row["embedding"]) if row["embedding"] else None
        except Exception:
            vec = None
        semantic = cosine(qvec, vec) if qvec and vec else 0.0
        lexical = lexical_similarity(query, row["content"])
        confidence = float(row["confidence"])
        importance = float(row["importance"])
        score = 0.55 * semantic + 0.25 * lexical + 0.12 * importance + 0.08 * confidence
        scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [dict(row) for score, row in scored[:limit] if score >= 0.06]

def extract_memory_records(conversation_id, message_id, user_text):
    raw = chat_once([
        {"role": "system", "content": EXTRACTION_PROMPT},
        {"role": "user", "content": user_text}
    ], temperature=0.0, num_predict=400, json_mode=True)
    data = json.loads(raw)
    created = []
    allowed_categories = {"profile", "skills", "goals", "projects", "preferences", "general"}
    for item in data.get("memories", [])[:3]:
        kind = item.get("type")
        if kind not in {"semantic", "procedural"}:
            continue
        content = str(item.get("content", "")).strip()
        confidence = max(0.1, min(1.0, float(item.get("confidence", 0.8))))
        if not content or len(content) > 500 or confidence < 0.55:
            continue
        category = str(item.get("category", "general")).lower()
        if category not in allowed_categories:
            category = "general"
        created.append(create_memory(
            kind, category, content,
            max(0.1, min(1.0, float(item.get("importance", 0.6)))),
            confidence,
            conversation_id, message_id, "pending", False
        ))
    return created


def upsert_episodic_summary(conversation_id, summary):
    summary = summary.strip()
    if not summary:
        return
    vector = embed_text(summary)
    with connect() as c:
        row = c.execute(
            """SELECT id,content,status FROM memories
               WHERE memory_type='episodic' AND source_conversation_id=?
               ORDER BY id DESC LIMIT 1""",
            (conversation_id,)
        ).fetchone()
        if row:
            c.execute(
                """UPDATE memories SET content=?,embedding=?,embedding_model=?,
                   updated_at=datetime('now') WHERE id=?""",
                (summary, json.dumps(vector) if vector else "",
                 OLLAMA_EMBED_MODEL if vector else "", row["id"])
            )
            log_history(c, row["id"], "summary_updated", row["content"], summary,
                        {"conversation_id": conversation_id})
        else:
            cur = c.execute(
                """INSERT INTO memories
                   (memory_type,category,content,importance,confidence,embedding,
                    source_conversation_id,active,status,user_approved,embedding_model)
                   VALUES('episodic','general',?,?,0.7,?,?,0,'pending',0,?)""",
                (summary, 0.7, json.dumps(vector) if vector else "",
                 conversation_id, OLLAMA_EMBED_MODEL if vector else "")
            )
            log_history(c, cur.lastrowid, "summary_created", None, summary,
                        {"conversation_id": conversation_id, "status": "pending"})

def get_memory_history(memory_id):
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM memory_history WHERE memory_id=? ORDER BY id DESC", (memory_id,)
        ).fetchall()
    return [dict(r) for r in rows]
