import pytest
import anyio
import asyncio
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.tools.registry import ToolRegistry
from backend.app.config import PermissionLevel

class EchoInput(BaseModel):
    message: str = Field(description="Message to echo")

class EchoTool(BaseTool):
    name = "echo_tool"
    description = "A simple tool that echoes input"
    input_schema = EchoInput
    permission_level = PermissionLevel.READ_ONLY
    timeout_seconds = 2

    async def execute(self, message: str) -> ToolResult:
        return ToolResult(success=True, data=f"Echo: {message}")

class DangerousInput(BaseModel):
    command: str

class DangerousTool(BaseTool):
    name = "dangerous_tool"
    description = "A tool requiring approval"
    input_schema = DangerousInput
    permission_level = PermissionLevel.DESTRUCTIVE
    timeout_seconds = 2

    async def execute(self, command: str) -> ToolResult:
        return ToolResult(success=True, data=f"Executed: {command}")

class SlowTool(BaseTool):
    name = "slow_tool"
    description = "A tool that times out"
    input_schema = EchoInput
    permission_level = PermissionLevel.READ_ONLY
    timeout_seconds = 1

    async def execute(self, message: str) -> ToolResult:
        await asyncio.sleep(2)
        return ToolResult(success=True, data="Too late")

def test_tool_registration_and_execution():
    reg = ToolRegistry()
    tool = EchoTool()
    reg.register(tool)

    assert reg.get_tool("echo_tool") is tool
    assert len(reg.list_tools()) == 1

    # Valid execution
    res = anyio.run(reg.execute_tool, "echo_tool", {"message": "Hello V3"})
    assert res.success is True
    assert res.data == "Echo: Hello V3"

    # Invalid arguments
    res_bad = anyio.run(reg.execute_tool, "echo_tool", {})
    assert res_bad.success is False
    assert "Invalid arguments" in res_bad.error

def test_permission_approval_check():
    reg = ToolRegistry()
    reg.register(DangerousTool())

    # Should fail without approval
    res = anyio.run(reg.execute_tool, "dangerous_tool", {"command": "format c:"}, False)
    assert res.success is False
    assert "requires explicit user approval" in res.error
    assert res.metadata["requires_approval"] is True

    # Should succeed with user_approved=True
    res_approved = anyio.run(reg.execute_tool, "dangerous_tool", {"command": "format c:"}, True)
    assert res_approved.success is True
    assert res_approved.data == "Executed: format c:"

def test_tool_timeout():
    reg = ToolRegistry()
    reg.register(SlowTool())

    res = anyio.run(reg.execute_tool, "slow_tool", {"message": "wait"})
    assert res.success is False
    assert "timed out" in res.error


