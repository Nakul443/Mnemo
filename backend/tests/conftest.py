# this file is responsible for setting up pytest fixtures for testing the Mnemo memory module.

from collections.abc import Iterator
from dataclasses import replace
from uuid import uuid4

import pytest
from falkordb.graph import Graph

from mnemo.memory import client


@pytest.fixture
def isolated_graph(monkeypatch: pytest.MonkeyPatch) -> Iterator[Graph]:
    settings = replace(
        client.get_settings(),
        falkordb_graph=f"mnemo_test_{uuid4().hex}",
    )
    monkeypatch.setattr(client, "get_settings", lambda: settings)
    client._get_db.cache_clear()
    graph = client.get_graph()
    yield graph
    graph.delete()
    client._get_db.cache_clear()
