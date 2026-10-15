"""Agent package initialization."""

# this file initializes the agent package in the Mnemo application,
# making the agent_graph available for import from the mnemo.agent module.

from mnemo.agent.graph import agent_graph

__all__ = ["agent_graph"]
