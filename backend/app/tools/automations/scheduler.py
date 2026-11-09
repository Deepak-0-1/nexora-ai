import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from backend.db import connect as connect_app_db

logger = logging.getLogger(__name__)

class AutomationManager:
    """Handles persistence, scheduling, and tracking for recurring workflows and reminders."""

    def create_automation(
        self,
        task_name: str,
        trigger_type: str,
        schedule_expr: str,
        action_type: str,
        action_payload: Dict[str, Any]
    ) -> str:
        auto_id = f"auto_{uuid.uuid4().hex[:10]}"
        with connect_app_db() as c:
            c.execute(
                """
                INSERT INTO automations (id, task_name, trigger_type, schedule_expr, action_type, action_payload_json, status, next_run_at)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
                """,
                (auto_id, task_name, trigger_type, schedule_expr, action_type, json.dumps(action_payload), schedule_expr)
            )
        return auto_id

    def list_automations(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with connect_app_db() as c:
            sql = "SELECT * FROM automations"
            params = []
            if status:
                sql += " WHERE status = ?"
                params.append(status)
            sql += " ORDER BY created_at DESC"
            rows = c.execute(sql, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    def pause_automation(self, automation_id: str) -> bool:
        with connect_app_db() as c:
            cur = c.execute("UPDATE automations SET status = 'paused' WHERE id = ?", (automation_id,))
            return cur.rowcount > 0

    def resume_automation(self, automation_id: str) -> bool:
        with connect_app_db() as c:
            cur = c.execute("UPDATE automations SET status = 'active' WHERE id = ?", (automation_id,))
            return cur.rowcount > 0

    def delete_automation(self, automation_id: str) -> bool:
        with connect_app_db() as c:
            cur = c.execute("DELETE FROM automations WHERE id = ?", (automation_id,))
            return cur.rowcount > 0

    def record_run(self, automation_id: str, status: str, result: Dict[str, Any], error: str = "") -> None:
        with connect_app_db() as c:
            now_str = datetime.now(timezone.utc).isoformat()
            c.execute(
                """
                INSERT INTO automation_runs (automation_id, status, result_json, error, executed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (automation_id, status, json.dumps(result), error, now_str)
            )
            c.execute(
                "UPDATE automations SET last_run_at = ? WHERE id = ?",
                (now_str, automation_id)
            )

automation_manager = AutomationManager()

