"""LangGraph definition for Mnemo agent flow."""

# this file defines the LangGraph flow for the Mnemo agent, which consists of two main nodes: recall and respond.

from langgraph.graph import END, START, StateGraph

from mnemo.agent.nodes import recall_node, respond_node
from mnemo.agent.state import AgentState


def create_agent_graph():
    """Compile and return the recall -> respond LangGraph flow."""
    builder = StateGraph(AgentState)
    builder.add_node("recall", recall_node)
    builder.add_node("respond", respond_node)
    builder.add_edge(START, "recall")
    builder.add_edge("recall", "respond")
    builder.add_edge("respond", END)
    return builder.compile()


agent_graph = create_agent_graph()
