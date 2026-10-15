"""Initialize the configured Mnemo graph."""

# this file is responsible for initializing the Mnemo graph in FalkorDB.
# in simple words, it sets up the database schema and ensures that the configured agent exists.

import logging

from mnemo.config import get_settings
from mnemo.memory.schema import init_schema
from mnemo.memory.write import ensure_agent


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    created_indexes = init_schema()
    ensure_agent(settings.agent_id, settings.agent_name)
    print(
        f"Initialized graph '{settings.falkordb_graph}': "
        f"{created_indexes} index(es) created; "
        f"agent '{settings.agent_id}' is ready."
    )


if __name__ == "__main__":
    main()
