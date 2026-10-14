"""Conservative fact conflict decisions."""

# this file is responsible for classifying a new fact as add, replace, or skip
# based on existing facts in memory. It uses a Gemini model to make the classification,
# but prefilters some cases to avoid unnecessary calls to the model. It also validates
# the model's output and defaults to "add" if the output is invalid or unrecognized

import json
import logging
import re
from collections.abc import Mapping, Sequence

from pydantic import ValidationError

from mnemo.config import get_settings, load_prompt
from mnemo.llm.client import generate_json
from mnemo.models import ConflictDecision

logger = logging.getLogger(__name__)


def _normalize_fact(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).casefold()


def _parse_decision(raw_response: str) -> ConflictDecision:
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(
            r"^```(?:json)?\s*|\s*```\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
    return ConflictDecision.model_validate(json.loads(cleaned.strip()))


def _add_decision() -> ConflictDecision:
    return ConflictDecision(action="add", replaces=[])


def check_conflict(
    new_fact_text: str,
    existing_facts: Sequence[Mapping[str, object]],
) -> ConflictDecision:
    """Classify a new fact as add, replace, or skip."""
    if not existing_facts:
        return _add_decision()

    normalized_new = _normalize_fact(new_fact_text)
    if normalized_new and any(
        _normalize_fact(str(fact.get("text", ""))) == normalized_new
        for fact in existing_facts
    ):
        return ConflictDecision(action="skip", replaces=[])

    existing_with_ids = [
        (fact, str(fact["id"]))
        for fact in existing_facts
        if fact.get("id") is not None
    ]
    existing_ids = [fact_id for _, fact_id in existing_with_ids]
    existing_lines = "\n".join(
        f"- [id: {fact_id}] {fact.get('text', '')}"
        for fact, fact_id in existing_with_ids
    ) or "(none)"
    user_content = f"NEW: {new_fact_text}\nEXISTING:\n{existing_lines}"
    settings = get_settings()

    for attempt in range(2):
        raw_response = generate_json(
            settings.conflict_model,
            load_prompt("conflict"),
            user_content,
        )
        try:
            decision = _parse_decision(raw_response)
            break
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            logger.warning(
                "Invalid conflict response (%d/2): %s",
                attempt + 1,
                error,
            )
    else:
        logger.error("Conflict response failed validation twice; defaulting to add")
        return _add_decision()

    if decision.action not in {"add", "replace", "skip"}:
        logger.warning("Unknown conflict action %r; defaulting to add", decision.action)
        return _add_decision()
    if decision.action != "replace":
        return ConflictDecision(action=decision.action, replaces=[])

    valid_ids = list(dict.fromkeys(
        fact_id for fact_id in decision.replaces if fact_id in existing_ids
    ))
    if not valid_ids:
        logger.warning("Replacement decision contained no valid existing fact IDs")
        return _add_decision()
    return ConflictDecision(action="replace", replaces=valid_ids)
