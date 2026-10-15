"""Graph read operations for Mnemo memory."""

# this file is responsible for reading data from the FalkorDB graph database
# and returning it in a structured format.

from mnemo.memory.client import get_graph


def get_recent_events(
    agent_id: str,
    session_id: str,
    n: int = 3,
    before_seq: int | None = None,
) -> list[str]:
    """Return the most recent user messages in chronological order."""
    if n <= 0:
        return []
    result = get_graph().query(
        """
        MATCH (s:Session {id: $session_id, agent_id: $agent_id})
              -[:CONTAINS]->(ev:Event {agent_id: $agent_id, role: $role})
        WHERE $before_seq IS NULL OR ev.seq < $before_seq
        RETURN ev.text AS text
        ORDER BY ev.seq DESC
        LIMIT $limit
        """,
        {
            "agent_id": agent_id,
            "session_id": session_id,
            "role": "user",
            "limit": n,
            "before_seq": before_seq,
        },
    )
    return [str(row[0]) for row in reversed(result.result_set)]


def get_all_entities(agent_id: str) -> list[dict[str, str]]:
    """Return all entities stored for the given agent."""
    result = get_graph().query(
        """
        MATCH (e:Entity {agent_id: $agent_id})
        RETURN e.id AS id, e.name AS name, e.name_key AS name_key, e.type AS type
        """,
        {"agent_id": agent_id},
    )
    return [
        {
            "id": str(row[0]),
            "name": str(row[1]),
            "name_key": str(row[2]),
            "type": str(row[3]),
        }
        for row in result.result_set
    ]


def get_neighbor_entity_ids(agent_id: str, entity_ids: list[str]) -> list[str]:
    """Return entity IDs connected to the input entities via shared current facts."""
    if not entity_ids:
        return []
    result = get_graph().query(
        """
        MATCH (m:Entity {agent_id: $agent_id})<-[:ABOUT]-(f:Fact {agent_id: $agent_id, still_true: true})
              -[:ABOUT]->(n:Entity {agent_id: $agent_id})
        WHERE m.id IN $entity_ids AND NOT n.id IN $entity_ids
        RETURN DISTINCT n.id AS id
        """,
        {"agent_id": agent_id, "entity_ids": entity_ids},
    )
    return [str(row[0]) for row in result.result_set]


def get_preference_facts(agent_id: str, limit: int = 5) -> list[dict[str, object]]:
    """Return current facts about Preference entities, newest first."""
    if limit <= 0:
        return []
    result = get_graph().query(
        """
        MATCH (f:Fact {agent_id: $agent_id, still_true: true})
              -[:ABOUT]->(e:Entity {agent_id: $agent_id, type: 'Preference'})
        RETURN DISTINCT f.id AS id, f.text AS text, f.created_at AS created_at
        ORDER BY created_at DESC
        LIMIT $limit
        """,
        {"agent_id": agent_id, "limit": limit},
    )
    return [
        {"id": str(row[0]), "text": str(row[1]), "created_at": row[2]}
        for row in result.result_set
    ]


def get_recent_current_facts(agent_id: str, limit: int = 5) -> list[dict[str, object]]:
    """Return the most recent current facts overall."""
    if limit <= 0:
        return []
    result = get_graph().query(
        """
        MATCH (f:Fact {agent_id: $agent_id, still_true: true})
        RETURN f.id AS id, f.text AS text, f.created_at AS created_at
        ORDER BY created_at DESC
        LIMIT $limit
        """,
        {"agent_id": agent_id, "limit": limit},
    )
    return [
        {"id": str(row[0]), "text": str(row[1]), "created_at": row[2]}
        for row in result.result_set
    ]


def get_session_messages(
    agent_id: str,
    session_id: str,
    limit: int = 10,
    before_seq: int | None = None,
) -> list[dict[str, object]]:
    """Return messages for a session in chronological order."""
    if limit <= 0:
        return []
    result = get_graph().query(
        """
        MATCH (s:Session {id: $session_id, agent_id: $agent_id})
              -[:CONTAINS]->(ev:Event {agent_id: $agent_id})
        WHERE $before_seq IS NULL OR ev.seq < $before_seq
        RETURN ev.role AS role, ev.text AS text, ev.seq AS seq, ev.ts AS ts
        ORDER BY ev.seq DESC
        LIMIT $limit
        """,
        {
            "agent_id": agent_id,
            "session_id": session_id,
            "limit": limit,
            "before_seq": before_seq,
        },
    )
    rows = reversed(result.result_set)
    return [
        {
            "role": str(row[0]),
            "text": str(row[1]),
            "seq": row[2],
            "ts": row[3],
        }
        for row in rows
    ]


def session_exists(agent_id: str, session_id: str) -> bool:
    """Check if a session exists for the given agent."""
    result = get_graph().query(
        """
        MATCH (s:Session {id: $session_id, agent_id: $agent_id})
        RETURN s.id AS id
        """,
        {"agent_id": agent_id, "session_id": session_id},
    )
    return bool(result.result_set)


def get_graph_snapshot(agent_id: str) -> dict[str, object]:
    """Return entities and facts formatted as a graph snapshot for the UI."""
    graph = get_graph()

    # 1. Entities
    entity_rows = graph.query(
        """
        MATCH (e:Entity {agent_id: $agent_id})
        RETURN e.id AS id, e.name AS label, e.type AS entity_type, e.created_at AS created_at
        """,
        {"agent_id": agent_id},
    ).result_set

    nodes: list[dict[str, object]] = []
    max_ts = 0

    for row in entity_rows:
        created_at = int(row[3]) if row[3] is not None else 0
        max_ts = max(max_ts, created_at)
        nodes.append(
            {
                "id": str(row[0]),
                "kind": "entity",
                "label": str(row[1]),
                "entity_type": str(row[2]),
                "created_at": created_at,
            }
        )

    # 2. Facts with source messages
    fact_rows = graph.query(
        """
        MATCH (f:Fact {agent_id: $agent_id})
        OPTIONAL MATCH (f)-[:CAME_FROM]->(ev:Event {agent_id: $agent_id})
        RETURN f.id AS id, f.text AS label, f.still_true AS still_true,
               f.created_at AS created_at, f.replaced_at AS replaced_at,
               ev.text AS source_message
        """,
        {"agent_id": agent_id},
    ).result_set

    num_current = 0
    num_replaced = 0

    for row in fact_rows:
        still_true = bool(row[2])
        created_at = int(row[3]) if row[3] is not None else 0
        replaced_at = int(row[4]) if row[4] is not None else None

        max_ts = max(max_ts, created_at)
        if replaced_at:
            max_ts = max(max_ts, replaced_at)

        if still_true:
            num_current += 1
            status = "current"
        else:
            num_replaced += 1
            status = "replaced"

        nodes.append(
            {
                "id": str(row[0]),
                "kind": "fact",
                "label": str(row[1]),
                "status": status,
                "created_at": created_at,
                "replaced_at": replaced_at,
                "source_message": str(row[5]) if row[5] is not None else None,
            }
        )

    # 3. ABOUT Edges
    about_rows = graph.query(
        """
        MATCH (f:Fact {agent_id: $agent_id})-[:ABOUT]->(e:Entity {agent_id: $agent_id})
        RETURN f.id AS source, e.id AS target
        """,
        {"agent_id": agent_id},
    ).result_set

    edges: list[dict[str, str]] = [
        {"source": str(row[0]), "target": str(row[1]), "type": "ABOUT"}
        for row in about_rows
    ]

    # 4. REPLACES Edges
    replaces_rows = graph.query(
        """
        MATCH (new_f:Fact {agent_id: $agent_id})-[:REPLACES]->(old_f:Fact {agent_id: $agent_id})
        RETURN new_f.id AS source, old_f.id AS target
        """,
        {"agent_id": agent_id},
    ).result_set

    edges.extend(
        [
            {"source": str(row[0]), "target": str(row[1]), "type": "REPLACES"}
            for row in replaces_rows
        ]
    )

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "entities": len(nodes) - (num_current + num_replaced),
            "current_facts": num_current,
            "replaced_facts": num_replaced,
        },
        "updated_at": max_ts,
    }


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
