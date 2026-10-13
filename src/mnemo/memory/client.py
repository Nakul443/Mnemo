"""FalkorDB connection and graph selection."""

from functools import lru_cache

from falkordb import FalkorDB
from falkordb.graph import Graph

from mnemo.config import get_settings


@lru_cache(maxsize=1)
def _get_db(host: str, port: int, password: str | None) -> FalkorDB:
    options: dict[str, str | int] = {"host": host, "port": port}
    if password is not None:
        options["password"] = password
    return FalkorDB(**options)


def get_graph() -> Graph:
    """Return the configured FalkorDB graph handle."""
    settings = get_settings()
    db = _get_db(
        settings.falkordb_host,
        settings.falkordb_port,
        settings.falkordb_password,
    )
    return db.select_graph(settings.falkordb_graph)
