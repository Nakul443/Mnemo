"""LangGraph graph nodes for recall and response generation."""

# this file defines the nodes used in the LangGraph flow for the Mnemo agent,
# specifically for recalling relevant information from memory and generating responses based on that information.

import logging

from mnemo.agent.state import AgentState
from mnemo.config import get_settings, load_prompt
from mnemo.llm.client import generate_text
from mnemo.memory import recall

logger = logging.getLogger(__name__)


def recall_node(state: AgentState) -> dict[str, object]:
    """Execute memory recall based on the user's message."""
    agent_id = state.get("agent_id", "agent_main")
    user_message = state.get("user_message", "")
    recall_result = recall.recall(agent_id, user_message)
    return {"recall": recall_result.model_dump()}


def respond_node(state: AgentState) -> dict[str, object]:
    """Generate assistant chat reply using recalled memory context."""
    settings = get_settings()
    user_message = state.get("user_message", "")
    history = state.get("history", [])
    recall_dict = state.get("recall", {})

    context_block = str(recall_dict.get("context_block", "(nothing stored yet)"))
    system_prompt = f"{load_prompt('system')}\n\nMEMORY:\n{context_block}"

    messages: list[dict[str, str]] = list(history)
    messages.append({"role": "user", "content": user_message})

    reply = generate_text(
        settings.chat_model,
        system_prompt,
        messages,
        temperature=0.6,
    )
    return {"reply": reply}
