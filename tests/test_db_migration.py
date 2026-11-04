import sqlite3

from backend import db


def test_legacy_database_migrates_and_preserves_data(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
    CREATE TABLE conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL DEFAULT 'New chat',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        summary TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role TEXT NOT NULL CHECK(role IN ('user','assistant')),
        content TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE TABLE memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_type TEXT NOT NULL CHECK(memory_type IN ('semantic','episodic','procedural')),
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
    INSERT INTO conversations(id,title) VALUES('c1','Old conversation');
    INSERT INTO messages(conversation_id,role,content) VALUES('c1','user','Old message');
    INSERT INTO memories(memory_type,category,content,active)
        VALUES('semantic','skills','Uses Python',1);
    """)
    conn.commit()
    conn.close()

    monkeypatch.setattr(db, "DATABASE_PATH", str(db_path))
    db.init_db()

    with db.connect() as migrated:
        assert migrated.execute("SELECT title FROM conversations WHERE id='c1'").fetchone()[0] == "Old conversation"
        assert migrated.execute("SELECT content FROM messages WHERE conversation_id='c1'").fetchone()[0] == "Old message"
        memory = migrated.execute("SELECT content,status,user_approved FROM memories").fetchone()
        assert memory["content"] == "Uses Python"
        assert memory["status"] == "active"
        assert memory["user_approved"] == 1
        assert migrated.execute("SELECT COUNT(*) FROM memory_jobs").fetchone()[0] == 0
    assert list(tmp_path.glob("legacy.pre_v2_*.db"))
