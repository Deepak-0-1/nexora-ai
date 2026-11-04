from typing import Any, Literal
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1, max_length=12000)

class ConversationCreate(BaseModel):
    title: str = Field(default="New chat", max_length=100)

class MemoryCreate(BaseModel):
    memory_type: Literal["semantic", "procedural", "episodic"] = "semantic"
    category: str = Field(default="general", max_length=50)
    content: str = Field(min_length=1, max_length=1000)
    importance: float = Field(default=0.6, ge=0, le=1)
    confidence: float = Field(default=1.0, ge=0, le=1)

class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=1000)
    category: str | None = Field(default=None, max_length=50)
    importance: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)

class ProfileUpdate(BaseModel):
    profession: str | None = Field(default=None, max_length=200)
    interests: list[str] | None = None
    goals: list[str] | None = None
    response_preferences: list[str] | None = None
    additional_context: str | None = Field(default=None, max_length=2000)

class SettingsUpdate(BaseModel):
    values: dict[str, Any]
