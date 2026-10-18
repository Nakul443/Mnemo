"""FastAPI application for Mnemo graph memory agent API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from mnemo.agent.service import run_turn
from mnemo.api.schemas import (
    ChatRequest,
    ChatResponse,
    CreateSessionResponse,
    GraphSnapshotResponse,
    HealthResponse,
    MessageItem,
    SessionMessagesResponse,
)
from mnemo.config import get_settings
from mnemo.memory import client, read, schema, worker, write

logger = logging.getLogger(__name__)


# this function is a context manager that handles the startup and shutdown of the FastAPI application.
# context manager is used to define a lifespan for the application,
# which includes initializing the graph and ensuring the agent is set up on startup,
# and shutting down the worker on application shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup initialization and shutdown cleanup."""
    settings = get_settings()
    try:
        schema.init_schema()
        write.ensure_agent(settings.agent_id, settings.agent_name)
        logger.info("FastAPI app initialized graph '%s'", settings.falkordb_graph)
    except Exception as error:  # noqa: BLE001
        logger.error("Failed to initialize graph on startup: %s", error)
    yield
    worker.shutdown(wait=True)


app = FastAPI(
    title="Mnemo API",
    description="Graph memory API for AI agents powered by FalkorDB",
    version="0.2.0",
    lifespan=lifespan,
)

settings = get_settings()
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Health check verifying FalkorDB connectivity."""
    settings = get_settings()
    try:
        graph = client.get_graph()
        graph.query("RETURN 1")
    except Exception as error:
        logger.error("FalkorDB health check failed: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="memory store unavailable",
        ) from error

    return HealthResponse(
        status="ok",
        graph=settings.falkordb_graph,
        agent_id=settings.agent_id,
    )


@app.post(
    "/sessions",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session() -> CreateSessionResponse:
    """Create a new chat session."""
    settings = get_settings()
    try:
        session_id = write.create_session(settings.agent_id)
        return CreateSessionResponse(session_id=session_id)
    except Exception as error:
        logger.error("Failed to create session: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="memory store unavailable",
        ) from error


@app.get(
    "/sessions/{session_id}/messages",
    response_model=SessionMessagesResponse,
)
def get_session_messages(session_id: str) -> SessionMessagesResponse:
    """Retrieve chat message history for a session."""
    settings = get_settings()
    if not read.session_exists(settings.agent_id, session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    raw_msgs = read.get_session_messages(settings.agent_id, session_id, limit=100)
    messages: list[MessageItem] = []
    for msg in raw_msgs:
        seq_val = msg.get("seq", 0)
        ts_val = msg.get("ts", 0)
        seq_num = int(seq_val) if isinstance(seq_val, (int, str)) else 0
        ts_num = int(ts_val) if isinstance(ts_val, (int, str)) else 0
        messages.append(
            MessageItem(
                role=str(msg.get("role", "")),
                text=str(msg.get("text", "")),
                seq=seq_num,
                ts=ts_num,
            )
        )
    return SessionMessagesResponse(session_id=session_id, messages=messages)


@app.post("/chat", response_model=ChatResponse)
def post_chat(body: ChatRequest) -> ChatResponse:
    """Send a user message, run memory recall, and generate assistant reply."""
    settings = get_settings()
    msg_text = body.message.strip()
    if not msg_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty",
        )
    if len(msg_text) > 4000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message exceeds 4000 character limit",
        )

    if not read.session_exists(settings.agent_id, body.session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{body.session_id}' not found",
        )

    try:
        turn_result = run_turn(settings.agent_id, body.session_id, msg_text)
    except Exception as error:
        err_msg = str(error).casefold()
        logger.error("Turn execution failed: %s", error)
        if "gemini" in err_msg or "model" in err_msg or "api_key" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="language model unavailable",
            ) from error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="memory store unavailable",
        ) from error

    pending = worker.pending_count()

    return ChatResponse(
        reply=turn_result.reply,
        session_id=turn_result.session_id,
        event_id=turn_result.event_id,
        recalled_fact_ids=turn_result.recalled_fact_ids,
        matched_entity_ids=turn_result.matched_entity_ids,
        recalled=turn_result.recalled,
        extraction_pending=pending,
    )


@app.get("/graph", response_model=GraphSnapshotResponse)
def get_graph_snapshot() -> GraphSnapshotResponse:
    """Return entity/fact graph snapshot and extraction status."""
    settings = get_settings()
    try:
        snapshot = read.get_graph_snapshot(settings.agent_id)
    except Exception as error:
        logger.error("Failed to read graph snapshot: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="memory store unavailable",
        ) from error

    pending = worker.pending_count()

    raw_nodes = snapshot.get("nodes", [])
    nodes = raw_nodes if isinstance(raw_nodes, list) else []

    raw_edges = snapshot.get("edges", [])
    edges = raw_edges if isinstance(raw_edges, list) else []

    raw_stats = snapshot.get("stats", {})
    stats_dict = raw_stats if isinstance(raw_stats, dict) else {}

    ts_val = snapshot.get("updated_at", 0)
    updated_at = int(ts_val) if isinstance(ts_val, (int, str)) else 0

    return GraphSnapshotResponse(
        nodes=nodes,
        edges=edges,
        stats=stats_dict,
        updated_at=updated_at,
        extraction_pending=pending,
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("mnemo.api.main:app", host="0.0.0.0", port=settings.port, reload=True)
