"""Type definitions for agent state."""

# this file is used to define the structure of the agent's state in the Mnemo application.
# it uses TypedDict from the typing module to create a dictionary-like structure with specific keys and value types.

from typing import TypedDict


class AgentState(TypedDict, total=False):
    agent_id: str
    session_id: str
    user_message: str
    history: list[dict[str, str]]
    recall: dict[str, object]
    reply: str
