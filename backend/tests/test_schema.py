# this file is responsible for testing the schema initialization in the Mnemo memory module.
# in simple words, it checks that the init_schema function correctly sets up the database schema and is idempotent.

from falkordb.graph import Graph

from mnemo.memory import schema


def test_schema_initialization_is_idempotent(
    isolated_graph: Graph,
    monkeypatch,
) -> None:
    monkeypatch.setattr(schema, "get_graph", lambda: isolated_graph)

    assert schema.init_schema() == 5
    assert schema.init_schema() == 0
