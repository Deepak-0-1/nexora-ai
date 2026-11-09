from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field
from backend.app.config import PermissionLevel, DEFAULT_TOOL_TIMEOUT

class ToolResult(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_summary(self) -> str:
        if not self.success:
            return f"Error: {self.error}"
        if isinstance(self.data, str):
            return self.data
        import json
        try:
            return json.dumps(self.data, default=str)
        except Exception:
            return str(self.data)

class BaseTool(ABC):
    name: str
    description: str
    input_schema: Type[BaseModel]
    permission_level: PermissionLevel = PermissionLevel.READ_ONLY
    timeout_seconds: int = DEFAULT_TOOL_TIMEOUT
    requires_approval: bool = False

    def __init__(self):
        if not hasattr(self, "name") or not self.name:
            raise ValueError(f"Tool {self.__class__.__name__} must define 'name'")
        if not hasattr(self, "description") or not self.description:
            raise ValueError(f"Tool {self.__class__.__name__} must define 'description'")
        if not hasattr(self, "input_schema"):
            raise ValueError(f"Tool {self.__class__.__name__} must define 'input_schema'")

    def validate_args(self, args: Dict[str, Any]) -> BaseModel:
        return self.input_schema(**args)

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Executes the tool with validated kwargs and returns ToolResult."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Returns JSON schema definition of the tool for Ollama / Agent planning."""
        schema = self.input_schema.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "parameters": schema,
            "permission_level": self.permission_level.value,
            "requires_approval": self.requires_approval or (
                self.permission_level in (
                    PermissionLevel.EXTERNAL_WRITE,
                    PermissionLevel.DESTRUCTIVE,
                    PermissionLevel.EXECUTE_CODE
                )
            ),
            "timeout_seconds": self.timeout_seconds
        }

