"""FalkorDB connection and graph selection."""


# this file is responsible for managing the connection to the FalkorDB database
# and selecting the appropriate graph for operations.

from functools import lru_cache

from falkordb import FalkorDB
from falkordb.graph import Graph

from mnemo.config import get_settings


@lru_cache(maxsize=1)
def _get_db(host: str, port: int, password: str | None) -> FalkorDB:
    if password is None:
        return FalkorDB(host=host, port=port)
    return FalkorDB(host=host, port=port, password=password)


def get_graph() -> Graph:
    """Return the configured FalkorDB graph handle."""
    settings = get_settings()
    db = _get_db(
        settings.falkordb_host,
        settings.falkordb_port,
        settings.falkordb_password,
    )
    return db.select_graph(settings.falkordb_graph)
