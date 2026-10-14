from falkordb.graph import Graph

from mnemo.memory import schema


def test_schema_initialization_is_idempotent(
    isolated_graph: Graph,
    monkeypatch,
) -> None:
    monkeypatch.setattr(schema, "get_graph", lambda: isolated_graph)

    assert schema.init_schema() == 5
    assert schema.init_schema() == 0
