"""Domain model for turn result."""

from pydantic import BaseModel, Field

from mnemo.models import RecalledFact


class TurnResult(BaseModel):
    reply: str
    session_id: str
    event_id: str
    recalled_fact_ids: list[str] = Field(default_factory=list)
    matched_entity_ids: list[str] = Field(default_factory=list)
    recalled: list[RecalledFact] = Field(default_factory=list)
