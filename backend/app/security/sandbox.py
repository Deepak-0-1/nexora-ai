import re
from typing import Tuple

BLOCKED_PYTHON_PATTERNS = [
    r"\bimport\s+shutil\b",
    r"\bshutil\.rmtree\b",
    r"\bos\.system\b",
    r"\bsubprocess\b",
    r"\bctypes\b",
    r"\bwinreg\b",
    r"\b_winapi\b",
    r"\bbuiltins\.__import__\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bopen\s*\(\s*['\"]\/etc",
    r"\bopen\s*\(\s*['\"][a-zA-Z]:\\Windows"
]

def validate_python_code(code: str) -> Tuple[bool, str]:
    """
    Validates Python code before execution to block dangerous OS modifications,
    arbitrary subprocess spawning, and unauthorized registry access.
    """
    if not code or not code.strip():
        return False, "Code string cannot be empty."

    for pattern in BLOCKED_PYTHON_PATTERNS:
        if re.search(pattern, code, flags=re.IGNORECASE):
            return False, f"Security violation: Prohibited pattern detected in code ({pattern})"

    return True, ""

