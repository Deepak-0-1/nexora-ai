import sys
import uuid
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.config import PermissionLevel
from backend.app.security.sandbox import validate_python_code

SANDBOX_DIR = Path(__file__).resolve().parent.parent.parent.parent / "sandbox"

class ExecutePythonInput(BaseModel):
    code: str = Field(description="Self-contained Python script to execute for analysis, calculations, or plotting")
    timeout_seconds: int = Field(default=15, ge=1, le=60, description="Maximum execution time in seconds")

class ExecutePythonTool(BaseTool):
    name = "execute_python"
    description = "Executes Python code in an isolated subprocess with stdout/stderr capture, timeout controls, and security static analysis."
    input_schema = ExecutePythonInput
    permission_level = PermissionLevel.EXECUTE_CODE
    timeout_seconds = 20
    requires_approval = True  # Always requires approval or policy check for arbitrary code

    async def execute(self, code: str, timeout_seconds: int = 15) -> ToolResult:
        # 1. Static validation
        valid, reason = validate_python_code(code)
        if not valid:
            return ToolResult(
                success=False,
                error=f"Python security validation failed: {reason}"
            )

        # 2. Write code to sandbox script
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
        script_file = SANDBOX_DIR / f"run_{uuid.uuid4().hex[:8]}.py"
        script_file.write_text(code, encoding="utf-8")

        def _run_subprocess():
            try:
                proc = subprocess.run(
                    [sys.executable, str(script_file)],
                    cwd=str(SANDBOX_DIR),
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds
                )
                return {
                    "returncode": proc.returncode,
                    "stdout": proc.stdout.strip(),
                    "stderr": proc.stderr.strip()
                }
            finally:
                if script_file.exists():
                    try:
                        script_file.unlink()
                    except Exception:
                        pass

        try:
            res = await asyncio.to_thread(_run_subprocess)
            is_success = res["returncode"] == 0
            return ToolResult(
                success=is_success,
                data=res,
                error=res["stderr"] if not is_success else None,
                metadata={"returncode": res["returncode"]}
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"Execution timed out after {timeout_seconds} seconds."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Subprocess execution error: {str(e)}"
            )

