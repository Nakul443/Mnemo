# Mnemo — Cypher Query Reference

This document details all Cypher queries used by Mnemo to power its persistent agent memory graph in FalkorDB.

---

## 1. Schema & Index Initialization (`backend/src/mnemo/memory/schema.py`)

These index creation statements are executed idempotently on startup.

```cypher
CREATE INDEX FOR (e:Entity) ON (e.name_key)
CREATE INDEX FOR (e:Entity) ON (e.agent_id)
CREATE INDEX FOR (f:Fact) ON (f.id)
CREATE INDEX FOR (f:Fact) ON (f.still_true)
CREATE INDEX FOR (ev:Event) ON (ev.session_id)
```

---

## 2. Write Operations (`backend/src/mnemo/memory/write.py`)

### `ensure_agent`
Creates or updates the main `Agent` node.
```cypher
MERGE (a:Agent {agent_id: $agent_id})
ON CREATE SET a.id = $agent_id, a.created_at = $created_at
SET a.name = $name
RETURN a.id AS id, a.agent_id AS agent_id, a.name AS name,
       a.created_at AS created_at
```

### `create_session`
Creates a `Session` node linked to its owning `Agent`.
```cypher
MATCH (a:Agent {agent_id: $agent_id})
CREATE (s:Session {
    id: $session_id,
    agent_id: $agent_id,
    started_at: $started_at,
    goal: $goal
})
CREATE (a)-[:OWNS]->(s)
RETURN s.id AS id
```

### `add_event`
Atomically appends a conversation `Event` node with auto-incrementing `seq` inside `_ADD_EVENT_LOCK`.
```cypher
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
```

### `upsert_entity`
Upserts an `Entity` node by `(agent_id, name_key)`, preserving the original display name and entity type.
```cypher
MERGE (e:Entity {agent_id: $agent_id, name_key: $name_key})
ON CREATE SET e.id = $id, e.name = $name, e.type = $type,
              e.created_at = $created_at
RETURN e.id AS id, e.agent_id AS agent_id, e.name AS name,
       e.name_key AS name_key, e.type AS type, e.created_at AS created_at
```

### `link_event_mentions`
Links an `Event` to an `Entity` mentioned in the message text.
```cypher
MATCH (ev:Event {id: $event_id, agent_id: $agent_id})
MATCH (e:Entity {id: $entity_id, agent_id: $agent_id})
MERGE (ev)-[:MENTIONS]->(e)
RETURN ev.id AS id
```

### `add_fact`
Creates a current `Fact` node with `OWNS` (Agent), `CAME_FROM` (Event provenance), and `ABOUT` (Entity) relationships.
```cypher
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
```

### `replace_facts`
Marks superseded `Fact` nodes as `still_true = false` with a `replaced_at` timestamp and creates a `REPLACES` edge from the new fact.
```cypher
MATCH (new:Fact {id: $new_fact_id, agent_id: $agent_id})
MATCH (old:Fact {id: $old_fact_id, agent_id: $agent_id})
SET old.still_true = $still_true, old.replaced_at = $ts
MERGE (new)-[:REPLACES]->(old)
RETURN old.id AS id
```

---

## 3. Read & Recall Operations (`backend/src/mnemo/memory/read.py`)

### `get_all_entities`
Fetches all stored entities for matching against user messages during memory recall.
```cypher
MATCH (e:Entity {agent_id: $agent_id})
RETURN e.id AS id, e.name AS name, e.name_key AS name_key, e.type AS type
```

### `get_current_facts_for_entities`
Fetches current (`still_true = true`) facts for matched entities.
```cypher
MATCH (f:Fact {agent_id: $agent_id, still_true: $still_true})
      -[:ABOUT]->(e:Entity {agent_id: $agent_id})
WHERE e.id IN $entity_ids
RETURN DISTINCT f.id AS id, f.text AS text,
       f.created_at AS created_at
ORDER BY created_at DESC
```

### `get_neighbor_entity_ids` (One-Hop Graph Expansion)
Finds 1-hop related entities connected via shared current facts.
```cypher
MATCH (m:Entity {agent_id: $agent_id})<-[:ABOUT]-(f:Fact {agent_id: $agent_id, still_true: true})
      -[:ABOUT]->(n:Entity {agent_id: $agent_id})
WHERE m.id IN $entity_ids AND NOT n.id IN $entity_ids
RETURN DISTINCT n.id AS id
```

### `get_preference_facts`
Fetches current user preference facts (always included in recall context).
```cypher
MATCH (f:Fact {agent_id: $agent_id, still_true: true})
      -[:ABOUT]->(e:Entity {agent_id: $agent_id, type: 'Preference'})
RETURN DISTINCT f.id AS id, f.text AS text, f.created_at AS created_at
ORDER BY created_at DESC
LIMIT $limit
```

### `get_recent_current_facts`
Fallback query returning recent active facts when no entities match the message.
```cypher
MATCH (f:Fact {agent_id: $agent_id, still_true: true})
RETURN f.id AS id, f.text AS text, f.created_at AS created_at
ORDER BY created_at DESC
LIMIT $limit
```

### `get_session_messages`
Retrieves chat history for session context generation or UI restoration.
```cypher
MATCH (s:Session {id: $session_id, agent_id: $agent_id})
      -[:CONTAINS]->(ev:Event {agent_id: $agent_id})
WHERE $before_seq IS NULL OR ev.seq < $before_seq
RETURN ev.role AS role, ev.text AS text, ev.seq AS seq, ev.ts AS ts
ORDER BY ev.seq DESC
LIMIT $limit
```

### `get_graph_snapshot`
Pulls full graph state for the frontend live visualization (Entities, Facts with source message, ABOUT edges, REPLACES edges).
```cypher
// 1. Entities
MATCH (e:Entity {agent_id: $agent_id})
RETURN e.id AS id, e.name AS label, e.type AS entity_type, e.created_at AS created_at

// 2. Facts
MATCH (f:Fact {agent_id: $agent_id})
OPTIONAL MATCH (f)-[:CAME_FROM]->(ev:Event {agent_id: $agent_id})
RETURN f.id AS id, f.text AS label, f.still_true AS still_true,
       f.created_at AS created_at, f.replaced_at AS replaced_at,
       ev.text AS source_message

// 3. ABOUT Edges
MATCH (f:Fact {agent_id: $agent_id})-[:ABOUT]->(e:Entity {agent_id: $agent_id})
RETURN f.id AS source, e.id AS target

// 4. REPLACES Edges
MATCH (new_f:Fact {agent_id: $agent_id})-[:REPLACES]->(old_f:Fact {agent_id: $agent_id})
RETURN new_f.id AS source, old_f.id AS target
```

---

## 4. Ad-Hoc Analytics & Inspection Queries

These queries demonstrate graph capabilities in FalkorDB Browser or CLI inspection.

### Query 1: Current Facts for an Entity
```cypher
MATCH (f:Fact {still_true: true})-[:ABOUT]->(e:Entity {name_key: 'project x'})
RETURN f.text AS fact, f.created_at AS learned_at
ORDER BY learned_at DESC
```
*Why it needs a graph*: Filters active facts connected via `ABOUT` edges to a specific entity.

### Query 2: Replaced Fact History & Audit Trail
```cypher
MATCH (new:Fact)-[:REPLACES]->(old:Fact)
RETURN old.text AS was, new.text AS now, old.replaced_at AS replaced_at
ORDER BY replaced_at DESC
```
*Why it needs a graph*: Follows `REPLACES` directed edges to inspect memory mutation history.

### Query 3: Message Provenance Audit
```cypher
MATCH (f:Fact)-[:CAME_FROM]->(ev:Event)
RETURN f.text AS fact, ev.text AS source_message, f.still_true AS current
```
*Why it needs a graph*: Traverses `CAME_FROM` edges linking facts to original conversation messages.

### Query 4: One-Hop Entity Co-occurrence Discovery
```cypher
MATCH (m:Entity {name_key: 'project x'})<-[:ABOUT]-(f:Fact {still_true: true})-[:ABOUT]->(n:Entity)
WHERE n.id <> m.id
RETURN DISTINCT n.name AS related, n.type AS type
```
*Why it needs a graph*: Performs 2-step edge traversal (`Entity <- ABOUT - Fact - ABOUT -> Entity`) to surface related tools/people.

### Query 5: Full Fact Replacement Chains
```cypher
MATCH p = (a:Fact)-[:REPLACES*1..5]->(b:Fact)
RETURN p
```
*Why it needs a graph*: Uses variable-length path matching (`:REPLACES*1..5`) to visualize multi-step fact updates.

### Query 6: Full Graph Visualization Subgraph
```cypher
MATCH p = (f:Fact)-[:ABOUT]->(e:Entity)
RETURN p LIMIT 50
```
*Why it needs a graph*: Renders the entire semantic memory network in FalkorDB Browser.
