"""
Debug log data models. Feature 011-observer-ai-commentary.
"""
from enum import Enum
from pydantic import BaseModel


class DebugEntryType(str, Enum):
    prompt_response = "prompt_response"
    commentary = "commentary"


class DebugEntry(BaseModel):
    entry_id: str
    entry_type: DebugEntryType
    source: str
    turn: int
    phase: str
    step: str
    timestamp: float
    prompt: str
    response: str
    is_complete: bool
    rating: str | None = None
    explanation: str | None = None
    alternative: str | None = None
    thinking: str = ""  # Extended thinking tokens (collapsible in UI)


class DebugEntryPatch(BaseModel):
    response_chunk: str
    is_complete: bool
    # Optional structured fields set on the final completion patch (observer commentary)
    rating: str | None = None
    explanation: str | None = None
    alternative: str | None = None
    thinking_chunk: str = ""  # Appended to the thinking field


class DebugLog(BaseModel):
    game_id: str
    entries: list[DebugEntry]
