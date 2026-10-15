"""Unit tests for Day 2 graph read operations."""

import pytest
from falkordb.graph import Graph

from mnemo.memory import read, write


def test_read_day2_queries(
    isolated_graph: Graph, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(write, "get_graph", lambda: isolated_graph)
    monkeypatch.setattr(read, "get_graph", lambda: isolated_graph)

    agent_id = "agent_read_test"
    write.ensure_agent(agent_id, "Read Agent")

    session_id = write.create_session(agent_id)
    assert read.session_exists(agent_id, session_id) is True
    assert read.session_exists(agent_id, "nonexistent-session") is False

    # Store events with user and assistant roles
    write.add_event(agent_id, session_id, "Hello assistant", role="user")
    write.add_event(agent_id, session_id, "Hello user", role="assistant")
    ev3 = write.add_event(agent_id, session_id, "I use Go", role="user")

    # Messages query
    msgs = read.get_session_messages(agent_id, session_id, limit=10)
    assert len(msgs) == 3
    assert msgs[0]["role"] == "user"
    assert msgs[0]["text"] == "Hello assistant"
    assert msgs[1]["role"] == "assistant"
    assert msgs[2]["role"] == "user"

    seq_3 = int(ev3["seq"])  # type: ignore[arg-type]
    msgs_before = read.get_session_messages(
        agent_id, session_id, limit=10, before_seq=seq_3
    )
    assert len(msgs_before) == 2
    assert msgs_before[-1]["text"] == "Hello user"

    # Entities and facts
    proj = write.upsert_entity(agent_id, "Project X", "Project")
    go = write.upsert_entity(agent_id, "Go", "Tool")
    pref = write.upsert_entity(agent_id, "Tone", "Preference")

    all_ents = read.get_all_entities(agent_id)
    assert len(all_ents) == 3

    write.add_fact(
        agent_id, "Project X uses Go", [str(proj["id"]), str(go["id"])], str(ev3["id"])
    )
    fact_pref = write.add_fact(
        agent_id, "Prefers concise tone", [str(pref["id"])], str(ev3["id"])
    )

    # Neighbor entities query (from proj -> go via shared fact_go)
    neighbors = read.get_neighbor_entity_ids(agent_id, [str(proj["id"])])
    assert neighbors == [str(go["id"])]

    # Preference facts query
    prefs = read.get_preference_facts(agent_id, limit=5)
    assert len(prefs) == 1
    assert prefs[0]["id"] == str(fact_pref["id"])

    # Recent current facts
    recent_facts = read.get_recent_current_facts(agent_id, limit=5)
    assert len(recent_facts) == 2

    # Graph snapshot query
    snapshot = read.get_graph_snapshot(agent_id)
    assert "nodes" in snapshot
    assert "edges" in snapshot
    assert "stats" in snapshot
    assert "updated_at" in snapshot
    stats = snapshot["stats"]
    assert isinstance(stats, dict)
    assert stats["entities"] == 3
    assert stats["current_facts"] == 2
    assert stats["replaced_facts"] == 0
    edges = snapshot["edges"]
    assert isinstance(edges, list)
    assert len(edges) == 3  # 2 for fact_go (proj, go) + 1 for fact_pref (pref)
