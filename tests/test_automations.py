import pytest
from backend.db import init_db, connect
from backend.app.tools.automations.scheduler import automation_manager
from backend.app.tools.automations.tools import (
    CreateReminderTool,
    CreateScheduleTool,
    ListSchedulesTool
)

@pytest.mark.anyio
async def test_automation_tools():
    init_db()

    # 1. Create one-time reminder
    reminder_tool = CreateReminderTool()
    res_rem = await reminder_tool.execute(
        reminder_text="Review quarterly financial statement with team",
        remind_at="2026-11-10T10:00:00Z"
    )
    assert res_rem.success is True
    assert "automation_id" in res_rem.data
    auto_id_1 = res_rem.data["automation_id"]

    # 2. Create recurring schedule (requires approval check)
    schedule_tool = CreateScheduleTool()
    assert schedule_tool.requires_approval is True
    res_sched = await schedule_tool.execute(
        task_name="Daily Market Summary",
        schedule_interval="0 8 * * *",
        action_type="web_research",
        action_payload={"topic": "AI hardware advances"}
    )
    assert res_sched.success is True
    auto_id_2 = res_sched.data["automation_id"]

    # 3. List schedules
    list_tool = ListSchedulesTool()
    res_list = await list_tool.execute()
    assert res_list.success is True
    schedules = res_list.data["schedules"]
    assert len(schedules) >= 2
    ids = [s["id"] for s in schedules]
    assert auto_id_1 in ids
    assert auto_id_2 in ids

    # 4. Pause, record execution run, and delete
    assert automation_manager.pause_automation(auto_id_2) is True
    paused_sched = next(s for s in automation_manager.list_automations() if s["id"] == auto_id_2)
    assert paused_sched["status"] == "paused"

    automation_manager.record_run(auto_id_2, status="success", result={"articles_found": 4})
    with connect() as c:
        runs = c.execute("SELECT * FROM automation_runs WHERE automation_id = ?", (auto_id_2,)).fetchall()
        assert len(runs) == 1
        assert runs[0]["status"] == "success"

    assert automation_manager.delete_automation(auto_id_1) is True
    remaining_ids = [s["id"] for s in automation_manager.list_automations()]
    assert auto_id_1 not in remaining_ids

