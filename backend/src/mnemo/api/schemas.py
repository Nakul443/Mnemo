"""API request and response Pydantic schemas."""

from pydantic import BaseModel, Field

from mnemo.models import RecalledFact


class HealthResponse(BaseModel):
    status: str
    graph: str
    agent_id: str


class CreateSessionResponse(BaseModel):
    session_id: str


class MessageItem(BaseModel):
    role: str
    text: str
    seq: int
    ts: int


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: list[MessageItem] = Field(default_factory=list)


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    event_id: str
    recalled_fact_ids: list[str] = Field(default_factory=list)
    matched_entity_ids: list[str] = Field(default_factory=list)
    recalled: list[RecalledFact] = Field(default_factory=list)
    extraction_pending: int


class GraphSnapshotResponse(BaseModel):
    nodes: list[dict[str, object]] = Field(default_factory=list)
    edges: list[dict[str, str]] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)
    updated_at: int
    extraction_pending: int
