import json
import sqlite3
from datetime import datetime
from pathlib import Path
from backend.config import DATABASE_PATH

def connect():
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn

def _columns(conn, table):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}

def init_db():
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists() and db_path.stat().st_size:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = db_path.with_name(f"{db_path.stem}.pre_v2_{stamp}{db_path.suffix}")
        if not list(db_path.parent.glob(f"{db_path.stem}.pre_v2_*{db_path.suffix}")):
            try:
                # SQLite's backup API includes committed WAL content; copying only the .db
                # file can omit recent transactions when WAL mode is enabled.
                source = sqlite3.connect(str(db_path), timeout=30)
                destination = sqlite3.connect(str(backup), timeout=30)
                try:
                    source.backup(destination)
                finally:
                    destination.close()
                    source.close()
            except sqlite3.Error:
                try:
                    if backup.exists():
                        backup.unlink()
                except OSError:
                    pass

    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'New chat',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            summary TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id,id);
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_type TEXT NOT NULL DEFAULT 'semantic',
            category TEXT NOT NULL DEFAULT 'general',
            content TEXT NOT NULL,
            importance REAL NOT NULL DEFAULT 0.5,
            confidence REAL NOT NULL DEFAULT 0.8,
            embedding TEXT NOT NULL DEFAULT '',
            source_conversation_id TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_memories_active ON memories(active,memory_type,importance);
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY CHECK(id=1),
            profile_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS memory_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id INTEGER,
            action TEXT NOT NULL,
            old_content TEXT,
            new_content TEXT,
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS memory_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_memory_jobs_status ON memory_jobs(status,id);
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        );
        """)
        # Migrate columns added after the original app schema.
        cols = _columns(c, "memories")
        additions = {
            "status": "TEXT NOT NULL DEFAULT 'active'",
            "source_message_id": "INTEGER",
            "user_approved": "INTEGER NOT NULL DEFAULT 1",
            "last_confirmed_at": "TEXT",
            "superseded_by": "INTEGER",
            "conflict_with": "INTEGER",
            "embedding_model": "TEXT NOT NULL DEFAULT ''",
        }
        for name, ddl in additions.items():
            if name not in cols:
                c.execute(f"ALTER TABLE memories ADD COLUMN {name} {ddl}")
        # Preserve old active memories and make their state explicit.
        c.execute("UPDATE memories SET status=CASE WHEN active=1 THEN 'active' ELSE 'deleted' END WHERE status IS NULL OR status='active'")
        c.execute("INSERT OR IGNORE INTO user_profile(id,profile_json) VALUES(1,'{}')")
        c.execute("CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status,category)")
