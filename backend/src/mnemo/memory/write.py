"""Graph write operations."""

# this file is responsible for writing data to the FalkorDB graph database
# it provides functions to create and update agents, sessions, events, entities, and facts,
# ensuring that the graph structure is maintained and that relationships between nodes are correctly established.

import logging
import threading
import time
from uuid import uuid4

from falkordb.query_result import QueryResult

from mnemo.memory.client import get_graph
from mnemo.memory.normalize import normalize_name

logger = logging.getLogger(__name__)

# Single-process threading lock to prevent event seq calculation race conditions.
# Note: A multi-process deployment would require an atomic counter/sequence in FalkorDB.
_ADD_EVENT_LOCK = threading.Lock()


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def _one_row(result: QueryResult, operation: str) -> list[object]:
    rows = result.result_set
    if not rows:
        raise RuntimeError(f"FalkorDB did not return a result for {operation}")
    return rows[0]

# function to ensure that the result of a query returns exactly one row, otherwise raises an error
# one row because we expect certain operations
# (like creating an agent or session) to return a single result,
# and if it doesn't, something went wrong
def ensure_agent(agent_id: str, name: str) -> dict[str, object]:
    """Create or update the agent node and return its stored properties."""
    graph = get_graph()
    result = graph.query(
        """
        MERGE (a:Agent {agent_id: $agent_id})
        ON CREATE SET a.id = $agent_id, a.created_at = $created_at
        SET a.name = $name
        RETURN a.id AS id, a.agent_id AS agent_id, a.name AS name,
               a.created_at AS created_at
        """,
        {
            "agent_id": agent_id,
            "name": name,
            "created_at": _now_ms(),
        },
    )
    row = _one_row(result, "ensuring agent")
    return {
        "id": row[0],
        "agent_id": row[1],
        "name": row[2],
        "created_at": row[3],
    }


def create_session(agent_id: str) -> str:
    """Create a session owned by the specified agent and return its ID."""
    session_id = str(uuid4())
    result = get_graph().query(
        """
        MATCH (a:Agent {agent_id: $agent_id})
        CREATE (s:Session {
            id: $session_id,
            agent_id: $agent_id,
            started_at: $started_at,
            goal: $goal
        })
        CREATE (a)-[:OWNS]->(s)
        RETURN s.id AS id
        """,
        {
            "agent_id": agent_id,
            "session_id": session_id,
            "started_at": _now_ms(),
            "goal": "",
        },
    )
    row = _one_row(result, "creating session")
    return str(row[0])

# function to create a new session for an agent
def add_event(
    agent_id: str,
    session_id: str,
    text: str,
    role: str = "user",
) -> dict[str, object]:
    """Store an event at the next sequence position in its session."""
    with _ADD_EVENT_LOCK:
        event_id = str(uuid4())
        result = get_graph().query(
            """
            MATCH (s:Session {id: $session_id, agent_id: $agent_id})
            OPTIONAL MATCH (s)-[:CONTAINS]->(previous:Event {agent_id: $agent_id})
            WITH s, coalesce(max(previous.seq), 0) + 1 AS next_seq
            CREATE (ev:Event {
                id: $event_id,
                agent_id: $agent_id,
                session_id: $session_id,
                seq: next_seq,
                role: $role,
                text: $text,
                ts: $ts
            })
            CREATE (s)-[:CONTAINS {seq: next_seq}]->(ev)
            RETURN ev.id AS id, ev.agent_id AS agent_id, ev.session_id AS session_id,
                   ev.seq AS seq, ev.role AS role, ev.text AS text, ev.ts AS ts
            """,
            {
                "agent_id": agent_id,
                "session_id": session_id,
                "event_id": event_id,
                "role": role,
                "text": text,
                "ts": _now_ms(),
            },
        )
        row = _one_row(result, "adding event")
        return {
            "id": row[0],
            "agent_id": row[1],
            "session_id": row[2],
            "seq": row[3],
            "role": row[4],
            "text": row[5],
            "ts": row[6],
        }
    return {
        "id": row[0],
        "agent_id": row[1],
        "session_id": row[2],
        "seq": row[3],
        "role": row[4],
        "text": row[5],
        "ts": row[6],
    }

# entity means a thing or concept that is represented in the graph, such as a person, place, object, or idea
def upsert_entity(agent_id: str, name: str, entity_type: str) -> dict[str, object]:
    """Create an entity once, preserving its first display name and type."""
    name_key = normalize_name(name)
    result = get_graph().query(
        """
        MERGE (e:Entity {agent_id: $agent_id, name_key: $name_key})
        ON CREATE SET e.id = $id, e.name = $name, e.type = $type,
                      e.created_at = $created_at
        RETURN e.id AS id, e.agent_id AS agent_id, e.name AS name,
               e.name_key AS name_key, e.type AS type, e.created_at AS created_at
        """,
        {
            "agent_id": agent_id,
            "name_key": name_key,
            "id": str(uuid4()),
            "name": name.strip(),
            "type": entity_type,
            "created_at": _now_ms(),
        },
    )
    row = _one_row(result, "upserting entity")
    if row[4] != entity_type:
        logger.warning(
            "Entity %r already exists as type %r; keeping the stored type "
            "instead of %r",
            name,
            row[4],
            entity_type,
        )
    return {
        "id": row[0],
        "agent_id": row[1],
        "name": row[2],
        "name_key": row[3],
        "type": row[4],
        "created_at": row[5],
    }


def link_event_mentions(
    agent_id: str,
    event_id: str,
    entity_id: str,
) -> None:
    """Connect an event to an entity mentioned in that event."""
    result = get_graph().query(
        """
        MATCH (ev:Event {id: $event_id, agent_id: $agent_id})
        MATCH (e:Entity {id: $entity_id, agent_id: $agent_id})
        MERGE (ev)-[:MENTIONS]->(e)
        RETURN ev.id AS id
        """,
        {
            "agent_id": agent_id,
            "event_id": event_id,
            "entity_id": entity_id,
        },
    )
    _one_row(result, "linking event mention")


def add_fact(
    agent_id: str,
    text: str,
    about_entity_ids: list[str],
    event_id: str,
) -> dict[str, object]:
    """Create a current fact with ownership, entity, and provenance edges."""
    entity_ids = list(dict.fromkeys(about_entity_ids))
    if not entity_ids:
        raise ValueError("A fact must be about at least one entity")

    fact_id = str(uuid4())
    result = get_graph().query(
        """
        MATCH (a:Agent {agent_id: $agent_id})
        MATCH (ev:Event {id: $event_id, agent_id: $agent_id})
        UNWIND $entity_ids AS entity_id
        MATCH (e:Entity {agent_id: $agent_id})
        WHERE e.id = entity_id
        WITH a, ev, collect(DISTINCT e) AS entities
        WHERE size(entities) = size($entity_ids)
        CREATE (f:Fact {
            id: $fact_id,
            agent_id: $agent_id,
            text: $text,
            still_true: $still_true,
            created_at: $created_at
        })
        CREATE (a)-[:OWNS]->(f)
        CREATE (f)-[:CAME_FROM]->(ev)
        WITH f, entities
        UNWIND entities AS e
        CREATE (f)-[:ABOUT]->(e)
        WITH DISTINCT f
        RETURN f.id AS id, f.agent_id AS agent_id, f.text AS text,
               f.still_true AS still_true, f.created_at AS created_at
        """,
        {
            "agent_id": agent_id,
            "event_id": event_id,
            "entity_ids": entity_ids,
            "fact_id": fact_id,
            "text": text,
            "still_true": True,
            "created_at": _now_ms(),
        },
    )
    row = _one_row(result, "adding fact")
    return {
        "id": row[0],
        "agent_id": row[1],
        "text": row[2],
        "still_true": row[3],
        "created_at": row[4],
    }


def replace_facts(
    agent_id: str,
    new_fact_id: str,
    old_fact_ids: list[str],
    ts: int,
) -> None:
    """Mark old facts as replaced and link each one from the new fact."""
    if new_fact_id in old_fact_ids:
        raise ValueError("A fact cannot replace itself")

    graph = get_graph()
    for old_fact_id in dict.fromkeys(old_fact_ids):
        result = graph.query(
            """
            MATCH (new:Fact {id: $new_fact_id, agent_id: $agent_id})
            MATCH (old:Fact {id: $old_fact_id, agent_id: $agent_id})
            SET old.still_true = $still_true, old.replaced_at = $ts
            MERGE (new)-[:REPLACES]->(old)
            RETURN old.id AS id
            """,
            {
                "agent_id": agent_id,
                "new_fact_id": new_fact_id,
                "old_fact_id": old_fact_id,
                "still_true": False,
                "ts": ts,
            },
        )
        _one_row(result, "replacing fact")
