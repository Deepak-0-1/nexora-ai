import os
import json
import logging
from typing import Dict, Any, List, Optional
from backend.db import connect as connect_app_db

logger = logging.getLogger(__name__)

class IntegrationManager:
    """Manages external service connections and authentication settings (e.g. Email, GitHub, Slack)."""

    def list_integrations(self) -> List[Dict[str, Any]]:
        with connect_app_db() as c:
            # Check or create table if not already present
            c.execute("""
            CREATE TABLE IF NOT EXISTS integrations (
                id TEXT PRIMARY KEY,
                service_type TEXT NOT NULL,
                name TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                config_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """)
            rows = c.execute("SELECT id, service_type, name, enabled, created_at FROM integrations").fetchall()
            return [dict(r) for r in rows]

    def save_integration(self, integration_id: str, service_type: str, name: str, config: Dict[str, Any]) -> None:
        with connect_app_db() as c:
            c.execute(
                """
                INSERT INTO integrations (id, service_type, name, config_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    service_type=excluded.service_type,
                    name=excluded.name,
                    config_json=excluded.config_json
                """,
                (integration_id, service_type, name, json.dumps(config))
            )

    def get_integration(self, integration_id: str) -> Optional[Dict[str, Any]]:
        with connect_app_db() as c:
            row = c.execute("SELECT * FROM integrations WHERE id = ?", (integration_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            data["config"] = json.loads(data["config_json"])
            return data

integration_manager = IntegrationManager()

