"""Integration tests for FastAPI endpoints."""

from collections.abc import Iterator
from typing import Any

import pytest
from falkordb.graph import Graph
from fastapi.testclient import TestClient

import mnemo.agent.nodes as nodes_module
import mnemo.memory.pipeline as pipeline_module
from mnemo.api.main import app
from mnemo.memory import read, worker, write
from mnemo.models import (
    ConflictDecision,
    ExtractedEntity,
    ExtractedFact,
    ExtractionResult,
)


@pytest.fixture
def client(
    isolated_graph: Graph, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setattr(write, "get_graph", lambda: isolated_graph)
    monkeypatch.setattr(read, "get_graph", lambda: isolated_graph)

    with TestClient(app) as c:
        yield c


def test_health_endpoint(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "graph" in data
    assert "agent_id" in data


def test_sessions_and_messages_endpoints(client: TestClient) -> None:
    # 1. Unknown session messages -> 404
    res_404 = client.get("/sessions/unknown-session-id/messages")
    assert res_404.status_code == 404

    # 2. Create session -> 201
    res = client.post("/sessions")
    assert res.status_code == 201
    session_id = res.json()["session_id"]
    assert session_id is not None

    # 3. Get session messages -> empty initially
    res_msgs = client.get(f"/sessions/{session_id}/messages")
    assert res_msgs.status_code == 200
    assert res_msgs.json()["messages"] == []


def test_chat_validation_and_errors(client: TestClient) -> None:
    # Create valid session
    s_id = client.post("/sessions").json()["session_id"]

    # 1. Unknown session -> 404
    res_404 = client.post("/chat", json={"session_id": "bad-id", "message": "hello"})
    assert res_404.status_code == 404

    # 2. Empty message -> 422
    res_422 = client.post("/chat", json={"session_id": s_id, "message": "   "})
    assert res_422.status_code == 422

    # 3. LLM failure -> 502
    def mock_fail(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError("Gemini API error")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(nodes_module, "generate_text", mock_fail)
        res_502 = client.post("/chat", json={"session_id": s_id, "message": "hello"})
        assert res_502.status_code == 502
        assert res_502.json()["detail"] == "language model unavailable"


def test_cross_session_persistence_and_graph_snapshot(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    system_prompts_seen: list[str] = []

    def mock_generate_text(
        model: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.6,
    ) -> str:
        system_prompts_seen.append(system_prompt)
        return f"Response to: {messages[-1]['content']}"

    monkeypatch.setattr(nodes_module, "generate_text", mock_generate_text)

    def mock_check_conflict(
        new_fact_text: str,
        existing_facts: Any,
    ) -> ConflictDecision:
        existing_ids = [
            str(f["id"]) for f in existing_facts if isinstance(f, dict) and f.get("id") is not None
        ]
        if existing_ids:
            return ConflictDecision(action="replace", replaces=existing_ids)
        return ConflictDecision(action="add", replaces=[])

    monkeypatch.setattr(pipeline_module, "check_conflict", mock_check_conflict)

    # Session 1: User says building Project X in Python
    def mock_extract_s1(message: str, recent: Any) -> ExtractionResult:
        return ExtractionResult(
            entities=[
                ExtractedEntity(name="Project X", type="Project"),
                ExtractedEntity(name="Python", type="Tool"),
            ],
            facts=[
                ExtractedFact(
                    text="Project X uses Python", about=["Project X", "Python"]
                )
            ],
        )

    monkeypatch.setattr(pipeline_module, "extract", mock_extract_s1)

    s1_id = client.post("/sessions").json()["session_id"]
    res1 = client.post(
        "/chat",
        json={"session_id": s1_id, "message": "I am building Project X in Python."},
    )
    assert res1.status_code == 200
    assert res1.json()["reply"] == "Response to: I am building Project X in Python."

    # Wait for background extraction job to write fact to graph DB
    assert worker.wait_for_idle(timeout=2.0) is True

    # Session 2: New session asks about Project X
    def mock_extract_question(message: str, recent: Any) -> ExtractionResult:
        return ExtractionResult(entities=[], facts=[])

    monkeypatch.setattr(pipeline_module, "extract", mock_extract_question)

    s2_id = client.post("/sessions").json()["session_id"]
    res2 = client.post(
        "/chat",
        json={"session_id": s2_id, "message": "What do you know about Project X?"},
    )
    assert res2.status_code == 200
    assert worker.wait_for_idle(timeout=2.0) is True

    # Cross-session assertion: Session 2 system prompt contained the fact from Session 1!
    last_system_prompt = system_prompts_seen[-1]
    assert "MEMORY:" in last_system_prompt
    assert "Project X uses Python" in last_system_prompt

    # Session 2 update: Switch Project X from Python to Go
    def mock_extract_s2(message: str, recent: Any) -> ExtractionResult:
        return ExtractionResult(
            entities=[
                ExtractedEntity(name="Project X", type="Project"),
                ExtractedEntity(name="Go", type="Tool"),
            ],
            facts=[ExtractedFact(text="Project X uses Go", about=["Project X", "Go"])],
        )

    monkeypatch.setattr(pipeline_module, "extract", mock_extract_s2)

    res3 = client.post(
        "/chat",
        json={"session_id": s2_id, "message": "Actually I switched Project X to Go."},
    )
    assert res3.status_code == 200
    assert worker.wait_for_idle(timeout=2.0) is True

    # Check GET /graph snapshot
    graph_res = client.get("/graph")
    assert graph_res.status_code == 200
    graph_data = graph_res.json()

    nodes = graph_data["nodes"]
    edges = graph_data["edges"]
    stats = graph_data["stats"]

    assert stats["entities"] == 3  # Project X, Python, Go
    assert stats["current_facts"] == 1  # Project X uses Go
    assert stats["replaced_facts"] == 1  # Project X uses Python

    fact_nodes = [n for n in nodes if n["kind"] == "fact"]
    statuses = {f["label"]: f["status"] for f in fact_nodes}
    assert statuses["Project X uses Go"] == "current"
    assert statuses["Project X uses Python"] == "replaced"

    replaces_edges = [e for e in edges if e["type"] == "REPLACES"]
    assert len(replaces_edges) == 1


def test_cors_headers(client: TestClient) -> None:
    res = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
