"""Validated domain and LLM output models."""

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    name: str
    type: str


class ExtractedFact(BaseModel):
    text: str
    about: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    facts: list[ExtractedFact] = Field(default_factory=list)


class ConflictDecision(BaseModel):
    action: str
    replaces: list[str] = Field(default_factory=list)
