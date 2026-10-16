# Mnemo Graph Schema Reference

FalkorDB is a high-performance graph database. The labels, properties, and relationships below represent the schema conventions enforced by Mnemo application code.

## Nodes

| Label | Properties | Description |
|---|---|---|
| `Agent` | `id` (string), `agent_id` (string), `name` (string), `created_at` (epoch ms) | Represents the AI agent instance owning sessions and facts. |
| `Session` | `id` (UUID string), `agent_id` (string), `started_at` (epoch ms), `goal` (string) | Represents a conversation thread between user and agent. |
| `Event` | `id` (UUID string), `agent_id` (string), `session_id` (string), `seq` (integer), `role` (`"user"` or `"assistant"`), `text` (string), `ts` (epoch ms) | Individual conversation turn/message. |
| `Entity` | `id` (UUID string), `agent_id` (string), `name` (string), `name_key` (normalized string), `type` (`Project`, `Tool`, `Person`, `Decision`, `Preference`), `created_at` (epoch ms) | Durable entity mentioned in conversation. |
| `Fact` | `id` (UUID string), `agent_id` (string), `text` (string), `still_true` (boolean), `created_at` (epoch ms), `replaced_at` (epoch ms, optional) | Standalone third-person statement about entities. |

All timestamps are stored as epoch milliseconds (integer). Every node carries `agent_id` so graph queries can be scoped per agent.

## Relationships

| Relationship | Direction | Properties | Description |
|---|---|---|---|
| `OWNS` | `Agent` $\rightarrow$ `Session` | — | Agent owns the session |
| `OWNS` | `Agent` $\rightarrow$ `Fact` | — | Agent owns the fact |
| `CONTAINS` | `Session` $\rightarrow$ `Event` | `seq` (integer) | Session contains an event message |
| `MENTIONS` | `Event` $\rightarrow$ `Entity` | — | Event mentions an entity |
| `ABOUT` | `Fact` $\rightarrow$ `Entity` | — | Fact relates to an entity |
| `CAME_FROM` | `Fact` $\rightarrow$ `Event` | — | Provenance link connecting a fact to its source message |
| `REPLACES` | new `Fact` $\rightarrow$ old `Fact` | — | Directed edge from active fact to superseded fact |

Replaced facts remain in the graph with `still_true = false` and `replaced_at` set. They are preserved for audit trail and history visualization.

## Graph Indexes

Created idempotently during application startup in `backend/src/mnemo/memory/schema.py`:

```cypher
CREATE INDEX FOR (e:Entity) ON (e.name_key)
CREATE INDEX FOR (e:Entity) ON (e.agent_id)
CREATE INDEX FOR (f:Fact) ON (f.id)
CREATE INDEX FOR (f:Fact) ON (f.still_true)
CREATE INDEX FOR (ev:Event) ON (ev.session_id)
```

## Subgraph Example (Fact Supersession)

When a user states *"I am building Project X in Python"* and later *"Actually I switched Project X to Go"*:

```
(Agent: agent_main)-[:OWNS]->(Fact: "Project X uses Go", still_true: true)
(Fact: "Project X uses Go")-[:ABOUT]->(Entity: "Project X")
(Fact: "Project X uses Go")-[:ABOUT]->(Entity: "Go")
(Fact: "Project X uses Go")-[:CAME_FROM]->(Event: "Actually I switched...")

(Fact: "Project X uses Go")-[:REPLACES]->(Fact: "Project X uses Python", still_true: false)

(Fact: "Project X uses Python")-[:ABOUT]->(Entity: "Project X")
(Fact: "Project X uses Python")-[:ABOUT]->(Entity: "Python")
(Fact: "Project X uses Python")-[:CAME_FROM]->(Event: "I am building Project X...")
```
