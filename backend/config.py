import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

def resolve_path(value: str) -> str:
    p = Path(value)
    return str(p if p.is_absolute() else ROOT / p)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi4-mini:3.8b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
DATABASE_PATH = resolve_path(os.getenv("DATABASE_PATH", "./data/chatbot.db"))
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = [x.strip() for x in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if x.strip()]
MAX_RECENT_MESSAGES = int(os.getenv("MAX_RECENT_MESSAGES", "12"))
MAX_CONTEXT_MEMORIES = int(os.getenv("MAX_CONTEXT_MEMORIES", "8"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "18000"))
SUMMARY_TRIGGER_MESSAGES = int(os.getenv("SUMMARY_TRIGGER_MESSAGES", "20"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.4"))
BACKGROUND_POLL_SECONDS = float(os.getenv("BACKGROUND_POLL_SECONDS", "3"))
