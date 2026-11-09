import pytest
from pathlib import Path
from backend.app.tools.python.executor import ExecutePythonTool
from backend.app.tools.files.manager import ListFilesTool, ReadFileTool, CopyFileTool

@pytest.mark.anyio
async def test_python_executor_success():
    tool = ExecutePythonTool()
    code = """
import math
print(f"PI: {round(math.pi, 4)}")
for i in range(3):
    print(f"Num: {i}")
"""
    res = await tool.execute(code=code)
    assert res.success is True
    assert "PI: 3.1416" in res.data["stdout"]
    assert "Num: 2" in res.data["stdout"]

@pytest.mark.anyio
async def test_python_executor_blocks_forbidden_patterns():
    tool = ExecutePythonTool()
    dangerous_code = "import os; os.system('echo dangerous')"
    res = await tool.execute(code=dangerous_code)
    assert res.success is False
    assert "security validation failed" in res.error.lower()

@pytest.mark.anyio
async def test_file_management_tools(tmp_path):
    # 1. Create a directory structure in tmp_path
    work_dir = tmp_path / "my_workspace"
    work_dir.mkdir()
    f1 = work_dir / "note.txt"
    f1.write_text("Hello personal assistant V3", encoding="utf-8")

    # 2. ListFilesTool
    list_tool = ListFilesTool()
    res_list = await list_tool.execute(directory_path=str(work_dir))
    assert res_list.success is True
    assert res_list.data["count"] == 1
    assert res_list.data["items"][0]["name"] == "note.txt"

    # 3. ReadFileTool
    read_tool = ReadFileTool()
    res_read = await read_tool.execute(file_path=str(f1))
    assert res_read.success is True
    assert "Hello personal assistant V3" in res_read.data["content"]

    # 4. CopyFileTool
    dest_file = work_dir / "copied_note.txt"
    copy_tool = CopyFileTool()
    res_copy = await copy_tool.execute(source_path=str(f1), destination_path=str(dest_file))
    assert res_copy.success is True
    assert dest_file.exists()
    assert dest_file.read_text(encoding="utf-8") == "Hello personal assistant V3"

