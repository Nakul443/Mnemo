"""Memory recall logic for agent context generation."""

# this file is responsible for recalling relevant facts from the graph memory based on a user message.
# in simple words, it detects entities mentioned in the message, retrieves facts related to those entities
# as well as user preferences and recent facts, and formats them into a context block for the LLM system prompt.
# it also includes utility functions for detecting entities, formatting timestamps,
# and limiting the number of recalled facts to avoid overwhelming the LLM.

import re
import time
from collections.abc import Sequence

from mnemo.memory import read
from mnemo.memory.normalize import normalize_name
from mnemo.models import RecalledFact, RecallResult

MAX_RECALLED_FACTS = 15
MAX_PREFERENCES = 5
FALLBACK_RECENT = 5


def detect_entities(
    message: str, entities: Sequence[dict[str, str]]
) -> list[dict[str, str]]:
    """Detect entity mentions in message using regex and short-name rules."""
    normalized_msg = normalize_name(message)
    matched: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for entity in entities:
        ent_id = entity["id"]
        if ent_id in seen_ids:
            continue
        name_key = entity.get("name_key", "").strip()
        display_name = entity.get("name", "").strip()

        if not name_key:
            continue

        # Short-name rule: len <= 3 requires case-sensitive exact match against display_name in original message
        if len(name_key) <= 3:
            if not display_name:
                continue
            pattern = rf"(?<!\w){re.escape(display_name)}(?!\w)"
            if re.search(pattern, message):
                matched.append(dict(entity))
                seen_ids.add(ent_id)
        else:
            pattern = rf"(?<!\w){re.escape(name_key)}(?!\w)"
            if re.search(pattern, normalized_msg):
                matched.append(dict(entity))
                seen_ids.add(ent_id)

    return matched


def humanize_age(ts_ms: int, now_ms: int) -> str:
    """Format timestamp age into a human-readable relative duration string."""
    diff_sec = max(0, (now_ms - ts_ms) // 1000)
    if diff_sec < 60:
        return "just now"
    minutes = diff_sec // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} h ago"
    days = hours // 24
    if days < 30:
        return f"{days} days ago"
    weeks = days // 7
    return f"{weeks} weeks ago"


def format_context_block(facts: Sequence[RecalledFact], now_ms: int) -> str:
    """Format a list of recalled facts into a text block for the LLM system prompt."""
    if not facts:
        return "(nothing stored yet)"
    lines = [
        f"- {fact.text} ({humanize_age(fact.created_at, now_ms)})" for fact in facts
    ]
    return "\n".join(lines)


def recall(
    agent_id: str,
    message: str,
    now_ms: int | None = None,
) -> RecallResult:
    """Recall relevant facts for a user message, expanding one hop and including preferences."""
    if now_ms is None:
        now_ms = time.time_ns() // 1_000_000

    all_entities = read.get_all_entities(agent_id)
    matched_entities = detect_entities(message, all_entities)
    matched_ids = [e["id"] for e in matched_entities]

    # Source 1: Preferences
    pref_facts_raw = read.get_preference_facts(agent_id, limit=MAX_PREFERENCES)

    direct_facts_raw: list[dict[str, object]] = []
    related_facts_raw: list[dict[str, object]] = []
    recent_facts_raw: list[dict[str, object]] = []

    if matched_ids:
        direct_facts_raw = read.get_current_facts_for_entities(agent_id, matched_ids)
        neighbor_ids = read.get_neighbor_entity_ids(agent_id, matched_ids)
        if neighbor_ids:
            related_facts_raw = read.get_current_facts_for_entities(
                agent_id, neighbor_ids
            )
    else:
        recent_facts_raw = read.get_recent_current_facts(
            agent_id, limit=FALLBACK_RECENT
        )

    # Priority merging: pref -> direct -> related -> recent
    seen_fact_ids: set[str] = set()
    recalled_facts: list[RecalledFact] = []

    def _add_facts(raw_list: Sequence[dict[str, object]], source: str) -> None:
        for item in raw_list:
            if len(recalled_facts) >= MAX_RECALLED_FACTS:
                break
            f_id = str(item["id"])
            if f_id in seen_fact_ids:
                continue
            seen_fact_ids.add(f_id)
            ts_val = item["created_at"]
            created_at = int(ts_val) if isinstance(ts_val, (int, str)) else 0
            recalled_facts.append(
                RecalledFact(
                    id=f_id,
                    text=str(item["text"]),
                    created_at=created_at,
                    source=source,
                )
            )

    _add_facts(pref_facts_raw, "preference")
    _add_facts(direct_facts_raw, "direct")
    _add_facts(related_facts_raw, "related")
    _add_facts(recent_facts_raw, "recent")

    context_block = format_context_block(recalled_facts, now_ms)

    return RecallResult(
        facts=recalled_facts,
        matched_entity_ids=matched_ids,
        context_block=context_block,
    )
