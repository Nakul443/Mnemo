"""Service orchestrating agent chat turns."""

# this file is reponsible for orchestrating the flow of a single conversation turn in the Mnemo agent.
# in simple words,
    # it handles the process of receiving a user message,
    # recalling relevant information from memory,
    # generating a response,
    # and saving the conversation history.

import logging

from mnemo.agent.graph import agent_graph
from mnemo.agent.models import TurnResult
from mnemo.agent.state import AgentState
from mnemo.memory import pipeline, read, worker, write
from mnemo.models import RecalledFact

logger = logging.getLogger(__name__)


def run_turn(agent_id: str, session_id: str, text: str) -> TurnResult:
    """Run a single conversation turn: load history, save user msg, recall/respond, save reply, enqueue background extraction."""
    # 1. Load history before storing new user message
    raw_history = read.get_session_messages(agent_id, session_id, limit=10)
    history = [
        {"role": str(msg["role"]), "content": str(msg["text"])} for msg in raw_history
    ]

    # 2. Store user Event in graph DB
    user_ev = write.add_event(agent_id, session_id, text, role="user")

    # 3. Invoke LangGraph agent flow (recall -> respond)
    initial_state: AgentState = {
        "agent_id": agent_id,
        "session_id": session_id,
        "user_message": text,
        "history": history,
    }
    final_state = agent_graph.invoke(initial_state)
    reply = str(final_state.get("reply", ""))

    # 4. Store assistant Event in graph DB
    write.add_event(agent_id, session_id, reply, role="assistant")

    # 5. Enqueue background extraction job for user message
    worker.submit_extraction(
        pipeline.process_message,
        agent_id,
        session_id,
        text,
        user_ev,
    )

    # Parse recalled facts
    recall_dict = final_state.get("recall", {})
    raw_facts = recall_dict.get("facts", []) if isinstance(recall_dict, dict) else []
    recalled_facts: list[RecalledFact] = []
    recalled_fact_ids: list[str] = []

    for item in raw_facts:
        if isinstance(item, dict):
            f_id = str(item.get("id", ""))
            recalled_fact_ids.append(f_id)
            ts_val = item.get("created_at", 0)
            created_at = int(ts_val) if isinstance(ts_val, (int, str)) else 0
            recalled_facts.append(
                RecalledFact(
                    id=f_id,
                    text=str(item.get("text", "")),
                    created_at=created_at,
                    source=str(item.get("source", "direct")),
                )
            )

    matched_entity_ids = (
        [str(eid) for eid in recall_dict.get("matched_entity_ids", [])]
        if isinstance(recall_dict, dict)
        else []
    )

    return TurnResult(
        reply=reply,
        session_id=session_id,
        event_id=str(user_ev["id"]),
        recalled_fact_ids=recalled_fact_ids,
        matched_entity_ids=matched_entity_ids,
        recalled=recalled_facts,
    )
