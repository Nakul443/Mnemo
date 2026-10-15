"""Unit tests for recall logic and entity detection."""

import pytest
from falkordb.graph import Graph

from mnemo.memory import read, write
from mnemo.memory.recall import (
    detect_entities,
    format_context_block,
    humanize_age,
    recall,
)
from mnemo.models import RecalledFact


def test_detect_entities_rules() -> None:
    entities = [
        {"id": "e1", "name": "Project X", "name_key": "project x", "type": "Project"},
        {"id": "e2", "name": "Go", "name_key": "go", "type": "Tool"},
        {"id": "e3", "name": "C++", "name_key": "c++", "type": "Tool"},
        {"id": "e4", "name": "Node.js", "name_key": "node.js", "type": "Tool"},
    ]

    # Whole-phrase only: Project XY should not match Project X
    assert detect_entities("I like Project XY", entities) == []

    # Case insensitive phrase match
    matched = detect_entities("Building project x now", entities)
    assert [e["id"] for e in matched] == ["e1"]

    # Short name rule: "let's go" does not match "Go", but "I write Go" does
    assert detect_entities("Let's go ahead", entities) == []
    assert [e["id"] for e in detect_entities("I write Go code", entities)] == ["e2"]

    # Punctuation support
    assert [e["id"] for e in detect_entities("We use C++ for speed", entities)] == [
        "e3"
    ]
    assert [e["id"] for e in detect_entities("Backend in Node.js!", entities)] == ["e4"]


def test_humanize_age() -> None:
    now = 1_000_000_000_000
    assert humanize_age(now - 30_000, now) == "just now"
    assert humanize_age(now - 300_000, now) == "5 min ago"
    assert humanize_age(now - 7_200_000, now) == "2 h ago"
    assert humanize_age(now - 259_200_000, now) == "3 days ago"
    assert humanize_age(now - 3_024_000_000, now) == "5 weeks ago"


def test_format_context_block() -> None:
    now = 1_000_000_000_000
    assert format_context_block([], now) == "(nothing stored yet)"

    facts = [
        RecalledFact(
            id="f1", text="Project X uses Go", created_at=now - 300_000, source="direct"
        ),
        RecalledFact(
            id="f2",
            text="Prefers concise answers",
            created_at=now - 7_200_000,
            source="preference",
        ),
    ]
    block = format_context_block(facts, now)
    assert "- Project X uses Go (5 min ago)" in block
    assert "- Prefers concise answers (2 h ago)" in block


def test_recall_flow_with_graph(
    isolated_graph: Graph, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(write, "get_graph", lambda: isolated_graph)
    monkeypatch.setattr(read, "get_graph", lambda: isolated_graph)

    agent_id = "agent_test"
    write.ensure_agent(agent_id, "Test Agent")
    session_id = write.create_session(agent_id)
    ev = write.add_event(agent_id, session_id, "Initial setup")

    # Seed entities
    proj = write.upsert_entity(agent_id, "Project X", "Project")
    py = write.upsert_entity(agent_id, "Python", "Tool")
    pref = write.upsert_entity(agent_id, "Answer style", "Preference")

    # Seed facts
    pref_fact = write.add_fact(
        agent_id, "Prefers concise answers", [str(pref["id"])], str(ev["id"])
    )
    direct_fact = write.add_fact(
        agent_id,
        "Project X uses Python",
        [str(proj["id"]), str(py["id"])],
        str(ev["id"]),
    )
    old_fact = write.add_fact(
        agent_id, "Project X uses Java", [str(proj["id"])], str(ev["id"])
    )
    write.replace_facts(agent_id, str(direct_fact["id"]), [str(old_fact["id"])], 12345)

    # 1. Recall matching Project X
    res = recall(agent_id, "What is Project X?", now_ms=2_000_000_000_000)
    assert res.matched_entity_ids == [str(proj["id"])]
    fact_ids = [f.id for f in res.facts]
    assert str(pref_fact["id"]) in fact_ids
    assert str(direct_fact["id"]) in fact_ids
    assert str(old_fact["id"]) not in fact_ids  # Replaced facts never recalled

    # 2. Recall matching no entities -> returns preferences + fallback recent
    res_no_match = recall(agent_id, "Hello world", now_ms=2_000_000_000_000)
    assert res_no_match.matched_entity_ids == []
    no_match_ids = [f.id for f in res_no_match.facts]
    assert str(pref_fact["id"]) in no_match_ids
    assert str(direct_fact["id"]) in no_match_ids
