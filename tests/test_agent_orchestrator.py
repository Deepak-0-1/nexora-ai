import pytest
from pydantic import BaseModel
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.tools.registry import registry
from backend.app.config import PermissionLevel
from backend.app.agents.state import AgentPlan, AgentStep, RunStatus, StepStatus
from backend.app.agents.planner import Planner
from backend.app.agents.orchestrator import Orchestrator

class MockCalcInput(BaseModel):
    a: int
    b: int

class MockCalcTool(BaseTool):
    name = "mock_calc"
    description = "Add two numbers"
    input_schema = MockCalcInput
    permission_level = PermissionLevel.ANALYSIS

    async def execute(self, a: int, b: int) -> ToolResult:
        return ToolResult(success=True, data={"sum": a + b})

class MockDestructiveInput(BaseModel):
    target: str

class MockDestructiveTool(BaseTool):
    name = "mock_delete"
    description = "Delete something"
    input_schema = MockDestructiveInput
    permission_level = PermissionLevel.DESTRUCTIVE

    async def execute(self, target: str) -> ToolResult:
        return ToolResult(success=True, data={"deleted": target})

class MockPlanner(Planner):
    def __init__(self, plan_to_return: AgentPlan):
        self._plan = plan_to_return

    async def plan(self, user_query: str, conversation_history=None) -> AgentPlan:
        return self._plan

@pytest.mark.anyio
async def test_orchestrator_multi_step_execution():
    registry.register(MockCalcTool())

    plan = AgentPlan(
        goal="Calculate sum twice",
        steps=[
            AgentStep(step_id=1, tool_name="mock_calc", arguments={"a": 2, "b": 3}),
            AgentStep(step_id=2, tool_name="mock_calc", arguments={"a": 10, "b": 20})
        ]
    )
    orch = Orchestrator(planner=MockPlanner(plan))

    state = await orch.initialize_run("conv_1", "Calculate 2+3 and 10+20")
    events = []
    async for event in orch.run_until_complete_or_blocked(state.run_id):
        events.append(event)

    assert state.status == RunStatus.COMPLETED
    assert state.plan.steps[0].status == StepStatus.COMPLETED
    assert state.plan.steps[0].result == {"sum": 5}
    assert state.plan.steps[1].status == StepStatus.COMPLETED
    assert state.plan.steps[1].result == {"sum": 30}
    assert any(e["type"] == "run_completed" for e in events)

@pytest.mark.anyio
async def test_orchestrator_approval_checkpoint():
    registry.register(MockDestructiveTool())

    plan = AgentPlan(
        goal="Delete table",
        steps=[
            AgentStep(step_id=1, tool_name="mock_delete", arguments={"target": "temp_table"}, requires_approval=True)
        ]
    )
    orch = Orchestrator(planner=MockPlanner(plan))

    state = await orch.initialize_run("conv_2", "Delete temp_table")

    # First run without approval
    events_1 = []
    async for ev in orch.run_until_complete_or_blocked(state.run_id):
        events_1.append(ev)

    assert state.status == RunStatus.WAITING_APPROVAL
    assert state.plan.steps[0].status == StepStatus.WAITING_APPROVAL
    assert any(e["type"] == "waiting_approval" for e in events_1)

    # Now approve step
    approved = orch.approve_step(state.run_id, 1)
    assert approved is True
    assert state.plan.steps[0].approved is True

    # Resume run
    events_2 = []
    async for ev in orch.run_until_complete_or_blocked(state.run_id):
        events_2.append(ev)

    assert state.status == RunStatus.COMPLETED
    assert state.plan.steps[0].status == StepStatus.COMPLETED
    assert state.plan.steps[0].result == {"deleted": "temp_table"}

