"""Graph index initialization."""

import logging

from mnemo.memory.client import get_graph

logger = logging.getLogger(__name__)

INDEXES = (
    "CREATE INDEX FOR (e:Entity) ON (e.name_key)",
    "CREATE INDEX FOR (e:Entity) ON (e.agent_id)",
    "CREATE INDEX FOR (f:Fact) ON (f.id)",
    "CREATE INDEX FOR (f:Fact) ON (f.still_true)",
    "CREATE INDEX FOR (ev:Event) ON (ev.session_id)",
)


def init_schema() -> int:
    """Create graph indexes, ignoring only the already-indexed condition."""
    graph = get_graph()
    created = 0
    for query in INDEXES:
        try:
            graph.query(query)
            created += 1
        except Exception as error:
            message = str(error).casefold()
            already_indexed = "index" in message and (
                "already" in message or "exists" in message
            )
            if not already_indexed:
                raise
            logger.debug("Graph index already exists: %s", query)
    return created
