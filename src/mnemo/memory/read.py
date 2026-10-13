"""Graph read operations for Mnemo memory."""

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


def _clean_entities(entities: list[dict[str, object]]) -> list[dict[str, object]]:
    return [entity for entity in entities if entity.get("id") is not None]


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
        WITH f, collect(DISTINCT {id: e.id, name: e.name, type: e.type}) AS about
        OPTIONAL MATCH (f)-[:CAME_FROM]->(ev:Event {agent_id: $agent_id})
        WITH f, about, collect(DISTINCT ev.text) AS sources
        RETURN f.id AS id, f.text AS text, f.created_at AS created_at,
               about AS about, head(sources) AS source_message
        ORDER BY created_at DESC
        """,
        {"agent_id": agent_id, "still_true": True},
    ).result_set
    current_facts = [
        {
            "id": row[0],
            "text": row[1],
            "created_at": row[2],
            "about": _clean_entities(row[3]),
            "source_message": row[4],
        }
        for row in current_rows
    ]

    replaced_rows = graph.query(
        """
        MATCH (f:Fact {agent_id: $agent_id, still_true: $still_true})
        OPTIONAL MATCH (f)-[:ABOUT]->(e:Entity {agent_id: $agent_id})
        WITH f, collect(DISTINCT {id: e.id, name: e.name, type: e.type}) AS about
        OPTIONAL MATCH (f)-[:CAME_FROM]->(ev:Event {agent_id: $agent_id})
        WITH f, about, collect(DISTINCT ev.text) AS sources
        OPTIONAL MATCH (replacement:Fact {agent_id: $agent_id})-[:REPLACES]->(f)
        WITH f, about, sources,
             collect(DISTINCT {id: replacement.id, text: replacement.text})
                 AS replacements
        RETURN f.id AS id, f.text AS text, f.created_at AS created_at,
               f.replaced_at AS replaced_at, about AS about,
               head(sources) AS source_message, replacements AS replaced_by
        ORDER BY replaced_at DESC
        """,
        {"agent_id": agent_id, "still_true": False},
    ).result_set
    replaced_facts = [
        {
            "id": row[0],
            "text": row[1],
            "created_at": row[2],
            "replaced_at": row[3],
            "about": _clean_entities(row[4]),
            "source_message": row[5],
            "replaced_by": [
                replacement
                for replacement in row[6]
                if replacement.get("id") is not None
            ],
        }
        for row in replaced_rows
    ]
    return {
        "entities": entities,
        "current_facts": current_facts,
        "replaced_facts": replaced_facts,
    }
