import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.db import connect as connect_app_db

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages registered database connections and handles schema discovery and execution."""

    def list_connections(self) -> List[Dict[str, Any]]:
        with connect_app_db() as c:
            rows = c.execute("SELECT id, name, dialect, read_only, allowed_schemas, created_at FROM database_connections").fetchall()
            return [dict(r) for r in rows]

    def get_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        with connect_app_db() as c:
            row = c.execute("SELECT * FROM database_connections WHERE id = ?", (connection_id,)).fetchone()
            return dict(row) if row else None

    def register_connection(self, conn_id: str, name: str, dialect: str, connection_uri: str, read_only: bool = True, allowed_schemas: str = "main,public") -> None:
        with connect_app_db() as c:
            c.execute(
                """
                INSERT INTO database_connections (id, name, dialect, connection_uri, read_only, allowed_schemas)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    dialect=excluded.dialect,
                    connection_uri=excluded.connection_uri,
                    read_only=excluded.read_only,
                    allowed_schemas=excluded.allowed_schemas
                """,
                (conn_id, name, dialect, connection_uri, 1 if read_only else 0, allowed_schemas)
            )

    def get_sqlite_conn(self, path: str):
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"SQLite database file not found: {path}")
        conn = sqlite3.connect(f"file:{p.resolve()}?mode=ro", uri=True, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def list_tables(self, connection_id: str) -> List[Dict[str, Any]]:
        conn_meta = self.get_connection(connection_id)
        if not conn_meta:
            raise ValueError(f"Database connection '{connection_id}' not found.")

        dialect = conn_meta["dialect"].lower()
        if dialect == "sqlite":
            with self.get_sqlite_conn(conn_meta["connection_uri"]) as c:
                rows = c.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'").fetchall()
                return [{"table_name": r["name"], "type": r["type"]} for r in rows]
        else:
            raise NotImplementedError(f"Dialect '{dialect}' not configured for local direct inspection.")

    def describe_table(self, connection_id: str, table_name: str) -> List[Dict[str, Any]]:
        conn_meta = self.get_connection(connection_id)
        if not conn_meta:
            raise ValueError(f"Database connection '{connection_id}' not found.")

        # Sanitize table_name against alphanumeric and underscore
        if not table_name.replace("_", "").isalnum():
            raise ValueError(f"Invalid table name format: '{table_name}'")

        dialect = conn_meta["dialect"].lower()
        if dialect == "sqlite":
            with self.get_sqlite_conn(conn_meta["connection_uri"]) as c:
                rows = c.execute(f"PRAGMA table_info('{table_name}')").fetchall()
                return [
                    {
                        "cid": r["cid"],
                        "name": r["name"],
                        "type": r["type"],
                        "notnull": bool(r["notnull"]),
                        "default_value": r["dflt_value"],
                        "primary_key": bool(r["pk"])
                    }
                    for r in rows
                ]
        else:
            raise NotImplementedError(f"Dialect '{dialect}' not configured for local direct inspection.")

    def execute_read_query(self, connection_id: str, query: str, max_rows: int = 100) -> Dict[str, Any]:
        conn_meta = self.get_connection(connection_id)
        if not conn_meta:
            raise ValueError(f"Database connection '{connection_id}' not found.")

        dialect = conn_meta["dialect"].lower()
        if dialect == "sqlite":
            with self.get_sqlite_conn(conn_meta["connection_uri"]) as c:
                cursor = c.execute(query)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchmany(max_rows)
                data = [dict(zip(columns, r)) for r in rows]
                return {
                    "connection_id": connection_id,
                    "columns": columns,
                    "row_count": len(data),
                    "rows": data,
                    "limited": len(data) == max_rows
                }
        else:
            raise NotImplementedError(f"Dialect '{dialect}' not configured.")

db_manager = DatabaseManager()

