"""Validated domain and LLM output models."""

# this file is responsible for defining the data models used in Mnemo,
# including the structure of extracted entities and facts, as well as conflict decisions.
# These models are validated using Pydantic to ensure that the data conforms to the expected schema.

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
