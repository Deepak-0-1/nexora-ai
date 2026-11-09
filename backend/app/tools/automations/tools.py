import asyncio
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.config import PermissionLevel
from backend.app.tools.automations.scheduler import automation_manager

class CreateReminderInput(BaseModel):
    reminder_text: str = Field(description="Content of the reminder or task")
    remind_at: str = Field(description="ISO timestamp or description when to remind the user (e.g. '2026-11-09T09:00:00Z')")

class CreateReminderTool(BaseTool):
    name = "create_reminder"
    description = "Schedules a one-time reminder or alert for a specific date and time."
    input_schema = CreateReminderInput
    permission_level = PermissionLevel.GENERATE

    async def execute(self, reminder_text: str, remind_at: str) -> ToolResult:
        try:
            auto_id = await asyncio.to_thread(
                automation_manager.create_automation,
                task_name=f"Reminder: {reminder_text[:30]}",
                trigger_type="once",
                schedule_expr=remind_at,
                action_type="reminder",
                action_payload={"text": reminder_text}
            )
            return ToolResult(
                success=True,
                data={
                    "automation_id": auto_id,
                    "reminder_text": reminder_text,
                    "remind_at": remind_at,
                    "message": f"Reminder successfully scheduled for {remind_at}"
                },
                metadata={"automation_id": auto_id}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CreateScheduleInput(BaseModel):
    task_name: str = Field(description="Name of the scheduled workflow (e.g. 'Weekly Sales Summary')")
    schedule_interval: str = Field(description="Interval or cron expression (e.g. 'every Monday 9am' or '0 9 * * 1')")
    action_type: str = Field(description="Type of task to perform, e.g. 'database_query', 'web_research', or 'report_generation'")
    action_payload: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the task")

class CreateScheduleTool(BaseTool):
    name = "create_schedule"
    description = "Schedules a recurring automated workflow (e.g. weekly reports or daily web research). Requires user approval."
    input_schema = CreateScheduleInput
    permission_level = PermissionLevel.MODIFY
    requires_approval = True  # Modifying standing automation schedules requires confirmation

    async def execute(
        self,
        task_name: str,
        schedule_interval: str,
        action_type: str,
        action_payload: Dict[str, Any]
    ) -> ToolResult:
        try:
            auto_id = await asyncio.to_thread(
                automation_manager.create_automation,
                task_name=task_name,
                trigger_type="recurring",
                schedule_expr=schedule_interval,
                action_type=action_type,
                action_payload=action_payload
            )
            return ToolResult(
                success=True,
                data={
                    "automation_id": auto_id,
                    "task_name": task_name,
                    "schedule": schedule_interval,
                    "action_type": action_type,
                    "message": f"Recurring schedule '{task_name}' successfully created."
                },
                metadata={"automation_id": auto_id}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class ListSchedulesInput(BaseModel):
    pass

class ListSchedulesTool(BaseTool):
    name = "list_schedules"
    description = "Lists all scheduled automations, recurring tasks, and reminders."
    input_schema = ListSchedulesInput
    permission_level = PermissionLevel.READ_ONLY

    async def execute(self) -> ToolResult:
        try:
            tasks = await asyncio.to_thread(automation_manager.list_automations)
            return ToolResult(
                success=True,
                data={"schedules": tasks, "count": len(tasks)}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

