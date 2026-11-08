import os
from pathlib import Path
from typing import Tuple
from backend.app.config import DATA_DIR

def is_safe_local_path(file_path: str, must_exist: bool = True) -> Tuple[bool, str, Path]:
    """
    Validates that a local file path is safe:
    - Resolves relative paths against the project root
    - Prevents arbitrary system folder access outside approved directories
    - Checks existence if must_exist=True
    """
    try:
        p = Path(file_path).resolve()
        project_root = DATA_DIR.parent.resolve()

        # Path traversal guard: must be inside project or approved temp/workspace directories
        # Allow files within project_root or standard user temp directory
        temp_dir = Path(os.environ.get("TEMP", "/tmp")).resolve()

        is_inside_project = project_root in p.parents or p == project_root
        is_inside_temp = temp_dir in p.parents or p == temp_dir

        if not (is_inside_project or is_inside_temp):
            return False, f"Access denied: Path '{file_path}' is outside approved directories.", p

        if must_exist and not p.exists():
            return False, f"File not found: '{file_path}'", p

        return True, "", p
    except Exception as e:
        return False, f"Invalid path '{file_path}': {str(e)}", Path(file_path)

