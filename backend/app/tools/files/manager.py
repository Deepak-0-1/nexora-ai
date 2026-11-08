import shutil
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.tools.base import BaseTool, ToolResult
from backend.app.config import PermissionLevel
from backend.app.security.file_validator import is_safe_local_path

class ListFilesInput(BaseModel):
    directory_path: str = Field(description="Directory path to list files from")
    recursive: bool = Field(default=False, description="Whether to list files recursively")

class ListFilesTool(BaseTool):
    name = "list_files"
    description = "Lists files and subdirectories inside an approved workspace directory."
    input_schema = ListFilesInput
    permission_level = PermissionLevel.READ_ONLY

    async def execute(self, directory_path: str, recursive: bool = False) -> ToolResult:
        safe, err, resolved = is_safe_local_path(directory_path, must_exist=True)
        if not safe:
            return ToolResult(success=False, error=err)

        if not resolved.is_dir():
            return ToolResult(success=False, error=f"Path '{directory_path}' is not a directory.")

        def _scan():
            items = []
            pattern = "**/*" if recursive else "*"
            for p in resolved.glob(pattern):
                items.append({
                    "name": p.name,
                    "path": str(p),
                    "is_dir": p.is_dir(),
                    "size_bytes": p.stat().st_size if p.is_file() else 0
                })
            return items

        try:
            items = await asyncio.to_thread(_scan)
            return ToolResult(
                success=True,
                data={"directory": str(resolved), "count": len(items), "items": items}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class ReadFileInput(BaseModel):
    file_path: str = Field(description="Path to the file to read")
    max_chars: int = Field(default=10000, ge=100, le=100000, description="Max characters to read")

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Reads content from a text, code, JSON, or markdown file within approved project boundaries."
    input_schema = ReadFileInput
    permission_level = PermissionLevel.READ_ONLY

    async def execute(self, file_path: str, max_chars: int = 10000) -> ToolResult:
        safe, err, resolved = is_safe_local_path(file_path, must_exist=True)
        if not safe:
            return ToolResult(success=False, error=err)

        if not resolved.is_file():
            return ToolResult(success=False, error=f"Path '{file_path}' is not a file.")

        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
            truncated = len(content) > max_chars
            if truncated:
                content = content[:max_chars] + f"\n... [Truncated after {max_chars} characters]"
            return ToolResult(
                success=True,
                data={
                    "file_path": str(resolved),
                    "filename": resolved.name,
                    "size_bytes": resolved.stat().st_size,
                    "content": content,
                    "truncated": truncated
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CopyFileInput(BaseModel):
    source_path: str = Field(description="Source file path")
    destination_path: str = Field(description="Destination file path")

class CopyFileTool(BaseTool):
    name = "copy_file"
    description = "Copies a file from an approved source path to an approved destination path."
    input_schema = CopyFileInput
    permission_level = PermissionLevel.MODIFY

    async def execute(self, source_path: str, destination_path: str) -> ToolResult:
        safe_src, err_src, src_resolved = is_safe_local_path(source_path, must_exist=True)
        if not safe_src:
            return ToolResult(success=False, error=err_src)

        safe_dst, err_dst, dst_resolved = is_safe_local_path(destination_path, must_exist=False)
        if not safe_dst:
            return ToolResult(success=False, error=err_dst)

        try:
            dst_resolved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_resolved, dst_resolved)
            return ToolResult(
                success=True,
                data={
                    "source": str(src_resolved),
                    "destination": str(dst_resolved),
                    "message": f"Successfully copied {src_resolved.name} to {dst_resolved.name}"
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

