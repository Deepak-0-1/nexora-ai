import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, AsyncGenerator, Any
from backend.app.agents.state import AgentState, AgentPlan, AgentStep, RunStatus, StepStatus, utc_now_iso
from backend.app.agents.planner import Planner
from backend.app.tools.registry import registry
from backend.app.tools.base import ToolResult

logger = logging.getLogger(__name__)

# Active in-memory runs dictionary (can be accessed for inspection / approvals)
RUNS: Dict[str, AgentState] = {}

class Orchestrator:
    def __init__(self, planner: Optional[Planner] = None):
        self.planner = planner or Planner()

    def get_run(self, run_id: str) -> Optional[AgentState]:
        return RUNS.get(run_id)

    async def initialize_run(
        self,
        conversation_id: str,
        user_query: str,
        conversation_history: Optional[list] = None
    ) -> AgentState:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        state = AgentState(
            run_id=run_id,
            conversation_id=conversation_id,
            user_query=user_query,
            status=RunStatus.PLANNING
        )
        RUNS[run_id] = state

        # Generate plan
        plan = await self.planner.plan(user_query, conversation_history)
        state.plan = plan
        state.status = RunStatus.RUNNING if plan.steps else RunStatus.COMPLETED
        state.update_timestamp()
        return state

    async def execute_step(self, state: AgentState, step_index: int) -> ToolResult:
        if not state.plan or step_index >= len(state.plan.steps):
            return ToolResult(success=False, error="Step index out of range")

        step = state.plan.steps[step_index]
        step.status = StepStatus.RUNNING
        step.started_at = utc_now_iso()
        state.status = RunStatus.RUNNING
        state.update_timestamp()

        # Check if step requires approval and isn't approved
        if step.requires_approval and not step.approved:
            step.status = StepStatus.WAITING_APPROVAL
            state.status = RunStatus.WAITING_APPROVAL
            state.update_timestamp()
            return ToolResult(
                success=False,
                error="Action paused waiting for user approval",
                metadata={"waiting_approval": True, "step_id": step.step_id}
            )

        # Execute tool from registry
        tool_res = await registry.execute_tool(
            name=step.tool_name,
            arguments=step.arguments,
            user_approved=step.approved
        )

        step.completed_at = utc_now_iso()
        if tool_res.success:
            step.status = StepStatus.COMPLETED
            step.result = tool_res.data
        else:
            step.status = StepStatus.FAILED
            step.error = tool_res.error

        state.update_timestamp()
        return tool_res

    async def run_until_complete_or_blocked(
        self,
        run_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        state = self.get_run(run_id)
        if not state:
            yield {"type": "error", "message": f"Run {run_id} not found"}
            return

        yield {"type": "run_started", "run_id": run_id, "state": state.model_dump()}

        if not state.plan or not state.plan.steps:
            state.status = RunStatus.COMPLETED
            state.update_timestamp()
            yield {"type": "run_completed", "run_id": run_id, "state": state.model_dump()}
            return

        while state.current_step_index < len(state.plan.steps):
            idx = state.current_step_index
            step = state.plan.steps[idx]

            yield {
                "type": "step_started",
                "run_id": run_id,
                "step_index": idx,
                "step": step.model_dump()
            }

            res = await self.execute_step(state, idx)

            if state.status == RunStatus.WAITING_APPROVAL:
                yield {
                    "type": "waiting_approval",
                    "run_id": run_id,
                    "step_index": idx,
                    "step": step.model_dump()
                }
                return

            if not res.success:
                logger.warning(f"Step {idx} ({step.tool_name}) failed: {res.error}")
                yield {
                    "type": "step_failed",
                    "run_id": run_id,
                    "step_index": idx,
                    "error": res.error,
                    "step": step.model_dump()
                }
                # Check retry or skip policy; for now mark run failed
                state.status = RunStatus.FAILED
                state.error = f"Step {step.step_id} ({step.tool_name}) failed: {res.error}"
                state.update_timestamp()
                return

            yield {
                "type": "step_completed",
                "run_id": run_id,
                "step_index": idx,
                "result": res.data,
                "step": step.model_dump()
            }

            state.current_step_index += 1

        state.status = RunStatus.COMPLETED
        state.update_timestamp()
        yield {"type": "run_completed", "run_id": run_id, "state": state.model_dump()}

    def approve_step(self, run_id: str, step_id: int) -> bool:
        state = self.get_run(run_id)
        if not state or not state.plan:
            return False

        for step in state.plan.steps:
            if step.step_id == step_id:
                step.approved = True
                if step.status == StepStatus.WAITING_APPROVAL:
                    step.status = StepStatus.PENDING
                if state.status == RunStatus.WAITING_APPROVAL:
                    state.status = RunStatus.RUNNING
                state.update_timestamp()
                return True
        return False

    def cancel_run(self, run_id: str) -> bool:
        state = self.get_run(run_id)
        if not state:
            return False
        state.status = RunStatus.CANCELLED
        state.update_timestamp()
        return True

# Default orchestrator singleton
orchestrator = Orchestrator()
