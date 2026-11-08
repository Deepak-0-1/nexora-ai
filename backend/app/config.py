import os
from enum import Enum
from pathlib import Path
from backend.config import *

# Base storage paths
DATA_DIR = Path(DATABASE_PATH).parent
UPLOADS_DIR = resolve_path(os.getenv("UPLOADS_DIR", "./data/uploads"))
GENERATED_DIR = resolve_path(os.getenv("GENERATED_DIR", "./data/generated"))
DOC_INDEX_DIR = resolve_path(os.getenv("DOC_INDEX_DIR", "./data/document_index"))
BACKUPS_DIR = resolve_path(os.getenv("BACKUPS_DIR", "./data/backups"))

# Ensure directories exist
for _p in [UPLOADS_DIR, GENERATED_DIR, DOC_INDEX_DIR, BACKUPS_DIR]:
    Path(_p).mkdir(parents=True, exist_ok=True)

class PermissionLevel(str, Enum):
    READ_ONLY = "read_only"
    ANALYSIS = "analysis"
    GENERATE = "generate"
    MODIFY = "modify"
    EXTERNAL_WRITE = "external_write"
    DESTRUCTIVE = "destructive"
    EXECUTE_CODE = "execute_code"

# Tools execution timeout default (seconds)
DEFAULT_TOOL_TIMEOUT = int(os.getenv("DEFAULT_TOOL_TIMEOUT", "30"))

