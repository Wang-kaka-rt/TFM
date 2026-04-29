from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SessionState(str, Enum):
    idle = "idle"
    recording = "recording"
    processing = "processing"
    stopped = "stopped"
    failed = "failed"


class StartSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)


class StopSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)


class ReloadSessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)


class SessionInfo(BaseModel):
    session_id: str
    state: SessionState
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_event: str = "created"
    workspace_dir: str | None = None
    raw_dir: str | None = None
    words_dir: str | None = None
    phrases_dir: str | None = None
    sentences_dir: str | None = None
    chunk_count: int = 0
    word_count: int = 0
    phrase_count: int = 0
    sentence_count: int = 0
    metadata_path: str | None = None
    samples_path: str | None = None
    strudel_script_path: str | None = None
    last_error: str | None = None


class ApiMessage(BaseModel):
    ok: bool = True
    message: str


class SessionResponse(ApiMessage):
    session: SessionInfo


class StatusResponse(ApiMessage):
    active_session: SessionInfo | None = None
    sessions: list[SessionInfo] = Field(default_factory=list)
