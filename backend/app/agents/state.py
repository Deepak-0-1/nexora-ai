import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class RunStatus(str, Enum):
    INITIALIZING = "initializing"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentStep(BaseModel):
    step_id: int
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    requires_approval: bool = False
    approved: bool = False
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class AgentPlan(BaseModel):
    goal: str
    steps: List[AgentStep] = Field(default_factory=list)
    final_thought: str = ""

class AgentState(BaseModel):
    run_id: str
    conversation_id: str
    user_query: str
    status: RunStatus = RunStatus.INITIALIZING
    plan: Optional[AgentPlan] = None
    current_step_index: int = 0
    final_response: Optional[str] = None
    error: Optional[str] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def update_timestamp(self):
        self.updated_at = utc_now_iso()
