"""Unit tests for agent graph and run_turn service."""

import pytest
from falkordb.graph import Graph

from mnemo.agent import service
from mnemo.llm import client as llm_client
from mnemo.memory import read, worker, write


def test_run_turn_orchestration(
    isolated_graph: Graph, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(write, "get_graph", lambda: isolated_graph)
    monkeypatch.setattr(read, "get_graph", lambda: isolated_graph)

    agent_id = "agent_test_turn"
    write.ensure_agent(agent_id, "Turn Agent")
    session_id = write.create_session(agent_id)

    # Mock LLM calls
    def mock_generate_text(
        model: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.6,
    ) -> str:
        assert "MEMORY:" in system_prompt
        assert messages[-1]["content"] == "Hello agent"
        return "Hello user, I remember you!"

    monkeypatch.setattr(llm_client, "generate_text", mock_generate_text)

    # Run turn
    res = service.run_turn(agent_id, session_id, "Hello agent")

    assert res.reply == "Hello user, I remember you!"
    assert res.session_id == session_id
    assert res.event_id is not None

    # Verify events in graph
    msgs = read.get_session_messages(agent_id, session_id)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["text"] == "Hello agent"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["text"] == "Hello user, I remember you!"

    # Wait for background extraction
    worker.wait_for_idle(timeout=2.0)
