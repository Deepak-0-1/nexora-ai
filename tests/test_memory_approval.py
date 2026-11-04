from backend import db
from backend.memory import approve_memory


def test_approve_memory_can_supersede_conflict(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "memory.db"))
    db.init_db()
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO memories(memory_type,category,content,active,status,user_approved)
               VALUES('semantic','profile','User is learning Python',1,'active',1)"""
        )
        old_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """INSERT INTO memories(memory_type,category,content,active,status,user_approved,conflict_with)
               VALUES('semantic','profile','User is proficient in Python',0,'pending',0,?)""",
            (old_id,)
        )
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    result = approve_memory(new_id, replace_conflict=True)
    assert result["status"] == "active"
    with db.connect() as conn:
        old = conn.execute("SELECT status,active,superseded_by FROM memories WHERE id=?", (old_id,)).fetchone()
        new = conn.execute("SELECT status,active,user_approved FROM memories WHERE id=?", (new_id,)).fetchone()
    assert old["status"] == "archived"
    assert old["active"] == 0
    assert old["superseded_by"] == new_id
    assert new["status"] == "active"
    assert new["active"] == 1
    assert new["user_approved"] == 1
