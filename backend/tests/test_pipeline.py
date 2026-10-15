"""Tests for the memory pipeline using an isolated FalkorDB graph."""

# this file is responsible for testing the memory pipeline in the Mnemo memory module.
# in simple words, it checks that the process_message function correctly processes messages,
# extracts entities and facts, and stores them in the database while preserving the history of changes.

import pytest
from falkordb.graph import Graph

import mnemo.memory.pipeline as pipeline_module
from mnemo.memory import read, write
from mnemo.models import ExtractedEntity, ExtractedFact, ExtractionResult


def test_pipeline_process_message_stores_event_and_facts(
    isolated_graph: Graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(write, "get_graph", lambda: isolated_graph)
    monkeypatch.setattr(read, "get_graph", lambda: isolated_graph)

    agent_id = "test_agent"
    write.ensure_agent(agent_id, "Test Agent")
    session_id = write.create_session(agent_id)

    # Mock extract to return known result
    monkeypatch.setattr(
        pipeline_module,
        "extract",
        lambda text, recent: ExtractionResult(
            entities=[
                ExtractedEntity(name="Project X", type="Project"),
                ExtractedEntity(name="Python", type="Tool"),
            ],
            facts=[
                ExtractedFact(
                    text="Project X uses Python", about=["Project X", "Python"]
                )
            ],
        ),
    )

    res = pipeline_module.process_message(
        agent_id, session_id, "I'm building Project X in Python."
    )

    assert res.seq == 1
    assert len(res.entities) == 2
    assert len(res.fact_decisions) == 1
    assert res.fact_decisions[0].action == "add"

    memory = read.dump_memory(agent_id)
    assert len(memory["entities"]) == 2
    assert len(memory["current_facts"]) == 1
    assert memory["current_facts"][0]["text"] == "Project X uses Python"
