"""Pipeline for processing incoming messages into durable memory facts."""

# this file is responsible for processing incoming messages
# into durable memory facts in the Mnemo memory module.
# in simple words,
# it takes a message, extracts entities and facts from it,
# and stores them in the database while preserving the history of changes and replacements.

import logging
import time

from mnemo.memory import read, write
from mnemo.memory.conflicts import check_conflict
from mnemo.memory.extract import extract
from mnemo.memory.normalize import normalize_name
from mnemo.models import ExtractionResult, FactDecision, ProcessResult

logger = logging.getLogger(__name__)


def process_message(
    agent_id: str,
    session_id: str,
    text: str,
) -> ProcessResult:
    """Process a single user message into event, entities, and facts."""
    recent = read.get_recent_events(agent_id, session_id, n=3)
    event = write.add_event(agent_id, session_id, text)
    event_id = str(event["id"])

    try:
        extraction = extract(text, recent)
    except Exception as error:  # noqa: BLE001
        logger.error("Extraction failed for message %r: %s", text, error)
        extraction = ExtractionResult()

    entity_map: dict[str, str] = {}
    for entity in extraction.entities:
        ent = write.upsert_entity(agent_id, entity.name, entity.type)
        ent_id = str(ent["id"])
        write.link_event_mentions(agent_id, event_id, ent_id)
        entity_map[normalize_name(entity.name)] = ent_id

    fact_decisions: list[FactDecision] = []
    for fact in extraction.facts:
        entity_ids = [
            entity_map[normalize_name(name)]
            for name in fact.about
            if normalize_name(name) in entity_map
        ]
        if not entity_ids:
            logger.warning("Fact %r has no valid entity IDs; skipping", fact.text)
            continue

        existing = read.get_current_facts_for_entities(agent_id, entity_ids)
        try:
            decision = check_conflict(fact.text, existing)
        except Exception as error:  # noqa: BLE001
            logger.error(
                "Conflict check failed for fact %r: %s; defaulting to add",
                fact.text,
                error,
            )
            decision = check_conflict(fact.text, [])

        if decision.action == "skip":
            fact_decisions.append(
                FactDecision(text=fact.text, action="skip", replaces=[])
            )
            continue

        new_fact = write.add_fact(agent_id, fact.text, entity_ids, event_id)
        new_fact_id = str(new_fact["id"])

        if decision.action == "replace" and decision.replaces:
            now_ms = time.time_ns() // 1_000_000
            write.replace_facts(agent_id, new_fact_id, decision.replaces, now_ms)
            fact_decisions.append(
                FactDecision(
                    text=fact.text,
                    action="replace",
                    replaces=decision.replaces,
                )
            )
        else:
            fact_decisions.append(
                FactDecision(text=fact.text, action="add", replaces=[])
            )

    seq_val = event["seq"]
    seq_num = int(seq_val) if isinstance(seq_val, (int, str)) else 0

    return ProcessResult(
        event_id=event_id,
        session_id=session_id,
        seq=seq_num,
        text=text,
        entities=extraction.entities,
        fact_decisions=fact_decisions,
    )
