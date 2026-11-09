import asyncio
import logging
from typing import Dict, List, Optional, Any
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.config import PermissionLevel

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        if tool.name in self._tools:
            logger.warning(f"Overwriting tool registration for '{tool.name}'")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} (level={tool.permission_level.value})")

    def unregister(self, name: str):
        if name in self._tools:
            del self._tools[name]

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        return [tool.get_metadata() for tool in self._tools.values()]

    async def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        user_approved: bool = False
    ) -> ToolResult:
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found in registry."
            )

        meta = tool.get_metadata()
        if meta["requires_approval"] and not user_approved:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' requires explicit user approval before execution.",
                metadata={"requires_approval": True, "tool_name": name, "arguments": arguments}
            )

        # Validate arguments using input_schema
        try:
            validated = tool.validate_args(arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Invalid arguments for tool '{name}': {str(e)}",
                metadata={"arguments": arguments}
            )

        # Execute with timeout
        try:
            coro = tool.execute(**validated.model_dump())
            result = await asyncio.wait_for(coro, timeout=tool.timeout_seconds)
            return result
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' execution timed out after {tool.timeout_seconds} seconds."
            )
        except Exception as e:
            logger.exception(f"Error executing tool '{name}'")
            return ToolResult(
                success=False,
                error=f"Tool '{name}' failed with error: {str(e)}"
            )

# Global Tool Registry instance
registry = ToolRegistry()

