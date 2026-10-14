"""Graph read operations for Mnemo memory."""

# this file is responsible for reading data from the FalkorDB graph database
# and returning it in a structured format.

from mnemo.memory.client import get_graph


def get_recent_events(
    agent_id: str,
    session_id: str,
    n: int = 3,
) -> list[str]:
    """Return the most recent user messages in chronological order."""
    if n <= 0:
        return []
    result = get_graph().query(
        """
        MATCH (s:Session {id: $session_id, agent_id: $agent_id})
              -[:CONTAINS]->(ev:Event {agent_id: $agent_id, role: $role})
        RETURN ev.text AS text
        ORDER BY ev.seq DESC
        LIMIT $limit
        """,
        {
            "agent_id": agent_id,
            "session_id": session_id,
            "role": "user",
            "limit": n,
        },
    )
    return [str(row[0]) for row in reversed(result.result_set)]


def get_current_facts_for_entities(
    agent_id: str,
    entity_ids: list[str],
) -> list[dict[str, object]]:
    """Return distinct current facts associated with any requested entity."""
    if not entity_ids:
        return []
    result = get_graph().query(
        """
        MATCH (f:Fact {agent_id: $agent_id, still_true: $still_true})
              -[:ABOUT]->(e:Entity {agent_id: $agent_id})
        WHERE e.id IN $entity_ids
        RETURN DISTINCT f.id AS id, f.text AS text,
               f.created_at AS created_at
        ORDER BY created_at DESC
        """,
        {"agent_id": agent_id, "entity_ids": entity_ids, "still_true": True},
    )
    return [
        {"id": row[0], "text": row[1], "created_at": row[2]}
        for row in result.result_set
    ]


def _append_about_entity(
    about: list[dict[str, object]],
    entity_id: object,
    name: object,
    entity_type: object,
) -> None:
    if entity_id is None:
        return
    entity = {"id": entity_id, "name": name, "type": entity_type}
    if entity not in about:
        about.append(entity)


def _group_fact_rows(
    rows: list[list[object]],
    *,
    replaced: bool,
) -> list[dict[str, object]]:
    facts: dict[object, dict[str, object]] = {}
    for row in rows:
        if replaced:
            (
                fact_id,
                text,
                created_at,
                replaced_at,
                entity_id,
                entity_name,
                entity_type,
                source_message,
                replacement_id,
                replacement_text,
            ) = row
        else:
            (
                fact_id,
                text,
                created_at,
                entity_id,
                entity_name,
                entity_type,
                source_message,
            ) = row

        fact = facts.setdefault(
            fact_id,
            {
                "id": fact_id,
                "text": text,
                "created_at": created_at,
                "about": [],
                "source_message": None,
            },
        )
        about = fact["about"]
        if isinstance(about, list):
            _append_about_entity(about, entity_id, entity_name, entity_type)
        if source_message is not None:
            fact["source_message"] = source_message

        if replaced:
            fact["replaced_at"] = replaced_at
            replacements = fact.setdefault("replaced_by", [])
            if replacement_id is not None and isinstance(replacements, list):
                replacement = {"id": replacement_id, "text": replacement_text}
                if replacement not in replacements:
                    replacements.append(replacement)

    return list(facts.values())


def dump_memory(agent_id: str) -> dict[str, list[dict[str, object]]]:
    """Return entities, current facts, and replaced facts with provenance."""
    graph = get_graph()
    entity_rows = graph.query(
        """
        MATCH (e:Entity {agent_id: $agent_id})
        RETURN e.id AS id, e.agent_id AS agent_id, e.name AS name,
               e.name_key AS name_key, e.type AS type, e.created_at AS created_at
        ORDER BY e.type, e.name_key
        """,
        {"agent_id": agent_id},
    ).result_set
    entities = [
        {
            "id": row[0],
            "agent_id": row[1],
            "name": row[2],
            "name_key": row[3],
            "type": row[4],
            "created_at": row[5],
        }
        for row in entity_rows
    ]

    current_rows = graph.query(
        """
        MATCH (f:Fact {agent_id: $agent_id, still_true: $still_true})
        OPTIONAL MATCH (f)-[:ABOUT]->(e:Entity {agent_id: $agent_id})
        OPTIONAL MATCH (f)-[:CAME_FROM]->(ev:Event {agent_id: $agent_id})
        RETURN f.id AS id, f.text AS text, f.created_at AS created_at,
               e.id AS entity_id, e.name AS entity_name, e.type AS entity_type,
               ev.text AS source_message
        ORDER BY created_at DESC, entity_name
        """,
        {"agent_id": agent_id, "still_true": True},
    ).result_set
    current_facts = _group_fact_rows(current_rows, replaced=False)

    replaced_rows = graph.query(
        """
        MATCH (f:Fact {agent_id: $agent_id, still_true: $still_true})
        OPTIONAL MATCH (f)-[:ABOUT]->(e:Entity {agent_id: $agent_id})
        OPTIONAL MATCH (f)-[:CAME_FROM]->(ev:Event {agent_id: $agent_id})
        OPTIONAL MATCH (replacement:Fact {agent_id: $agent_id})-[:REPLACES]->(f)
        RETURN f.id AS id, f.text AS text, f.created_at AS created_at,
               f.replaced_at AS replaced_at, e.id AS entity_id,
               e.name AS entity_name, e.type AS entity_type,
               ev.text AS source_message, replacement.id AS replacement_id,
               replacement.text AS replacement_text
        ORDER BY replaced_at DESC, entity_name
        """,
        {"agent_id": agent_id, "still_true": False},
    ).result_set
    replaced_facts = _group_fact_rows(replaced_rows, replaced=True)
    return {
        "entities": entities,
        "current_facts": current_facts,
        "replaced_facts": replaced_facts,
    }
