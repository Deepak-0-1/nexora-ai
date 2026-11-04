from backend import db, memory


def test_episodic_summary_is_upserted_and_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "episodic.db"))
    monkeypatch.setattr(memory, "embed_text", lambda _text: None)
    db.init_db()

    memory.upsert_episodic_summary("conversation-a", "Summary version one")
    memory.upsert_episodic_summary("conversation-a", "Summary version two")

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT content,status,memory_type FROM memories WHERE source_conversation_id='conversation-a'"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["content"] == "Summary version two"
    assert rows[0]["status"] == "pending"
    assert rows[0]["memory_type"] == "episodic"
