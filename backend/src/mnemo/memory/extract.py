"""LLM-assisted extraction and strict post-validation cleanup."""

# this file is responsible for extracting durable entities and facts from a single user message.
# it uses a Gemini model to perform the extraction, but also performs strict post-validation
# and cleanup of the model's output to ensure that only valid entities and facts are returned.

import json
import logging
import re
from collections.abc import Sequence

from pydantic import ValidationError

from mnemo.config import get_settings, load_prompt
from mnemo.llm.client import generate_json
from mnemo.memory.normalize import normalize_name
from mnemo.models import ExtractionResult

logger = logging.getLogger(__name__)
ALLOWED_ENTITY_TYPES = frozenset(
    {"Project", "Tool", "Person", "Decision", "Preference"}
)
_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def _parse_response(raw_response: str) -> ExtractionResult:
    cleaned = _JSON_FENCE.sub("", raw_response.strip()).strip()
    payload = json.loads(cleaned)
    return ExtractionResult.model_validate(payload)


def _clean_result(result: ExtractionResult) -> ExtractionResult:
    entities_by_key = {}
    for entity in result.entities:
        name = entity.name.strip()
        name_key = normalize_name(name)
        if not name or not name_key or entity.type not in ALLOWED_ENTITY_TYPES:
            continue
        entities_by_key.setdefault(
            name_key,
            entity.model_copy(update={"name": name}),
        )

    valid_names = set(entities_by_key)
    facts = []
    for fact in result.facts:
        text = fact.text.strip()
        if not text:
            continue
        about_keys = dict.fromkeys(
            normalize_name(name.strip())
            for name in fact.about
            if name.strip() and normalize_name(name.strip()) in valid_names
        )
        if not about_keys:
            continue
        facts.append(
            fact.model_copy(
                update={
                    "text": text,
                    "about": [
                        entities_by_key[key].name for key in about_keys
                    ],
                }
            )
        )

    return ExtractionResult(
        entities=list(entities_by_key.values()),
        facts=facts,
    )


def extract(message: str, recent: Sequence[str]) -> ExtractionResult:
    """Extract durable entities and facts from a single user message."""
    recent_text = "\n".join(f"- {item}" for item in recent) or "(none)"
    user_content = f"RECENT:\n{recent_text}\nMESSAGE: {message}"
    settings = get_settings()

    for attempt in range(2):
        raw_response = generate_json(
            settings.extraction_model,
            load_prompt("extract"),
            user_content,
        )
        try:
            return _clean_result(_parse_response(raw_response))
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            logger.warning(
                "Invalid extraction response (%d/2): %s",
                attempt + 1,
                error,
            )
    logger.error("Extraction failed validation twice; returning an empty result")
    return ExtractionResult()
