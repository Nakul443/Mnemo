import mnemo.memory.read as read
import mnemo.memory.write as write
from falkordb.graph import Graph


def test_memory_writes_and_reads_preserve_history(
    isolated_graph: Graph,
    monkeypatch,
) -> None:
    monkeypatch.setattr(write, "get_graph", lambda: isolated_graph)
    monkeypatch.setattr(read, "get_graph", lambda: isolated_graph)

    agent = write.ensure_agent("agent_test", "Test Agent")
    assert agent["agent_id"] == "agent_test"

    session_id = write.create_session("agent_test")
    first_event = write.add_event("agent_test", session_id, "Project X uses Python.")
    second_event = write.add_event("agent_test", session_id, "Project X now uses Go.")
    third_event = write.add_event("agent_test", session_id, "Project X has a deadline.")
    fourth_event = write.add_event("agent_test", session_id, "Project X uses Go.")
    assert [
        first_event["seq"],
        second_event["seq"],
        third_event["seq"],
        fourth_event["seq"],
    ] == [1, 2, 3, 4]
    assert read.get_recent_events("agent_test", session_id, n=3) == [
        "Project X now uses Go.",
        "Project X has a deadline.",
        "Project X uses Go.",
    ]

    project = write.upsert_entity("agent_test", "Project X", "Project")
    same_project = write.upsert_entity("agent_test", " project  x ", "Tool")
    assert same_project["id"] == project["id"]
    assert same_project["name"] == "Project X"
    assert same_project["type"] == "Project"

    python = write.upsert_entity("agent_test", "Python", "Tool")
    go = write.upsert_entity("agent_test", "Go", "Tool")
    write.link_event_mentions("agent_test", first_event["id"], project["id"])
    old_fact = write.add_fact(
        "agent_test",
        "Project X uses Python",
        [project["id"], python["id"]],
        first_event["id"],
    )
    new_fact = write.add_fact(
        "agent_test",
        "Project X uses Go",
        [project["id"], go["id"]],
        second_event["id"],
    )
    write.replace_facts("agent_test", new_fact["id"], [old_fact["id"]], 123456789)

    current_facts = read.get_current_facts_for_entities(
        "agent_test",
        [project["id"]],
    )
    assert [fact["id"] for fact in current_facts] == [new_fact["id"]]

    memory = read.dump_memory("agent_test")
    assert len(memory["entities"]) == 3
    assert len(memory["current_facts"]) == 1
    assert len(memory["replaced_facts"]) == 1
    current = memory["current_facts"][0]
    replaced = memory["replaced_facts"][0]
    assert current["id"] == new_fact["id"]
    assert current["source_message"] == "Project X now uses Go."
    assert {entity["id"] for entity in current["about"]} == {
        project["id"],
        go["id"],
    }
    assert replaced["id"] == old_fact["id"]
    assert replaced["replaced_at"] == 123456789
    assert replaced["source_message"] == "Project X uses Python."
    assert replaced["replaced_by"] == [
        {"id": new_fact["id"], "text": "Project X uses Go"}
    ]
