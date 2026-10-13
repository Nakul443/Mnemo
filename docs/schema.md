# Mnemo Graph Schema

FalkorDB is schemaless. The labels, properties, and relationships below are
conventions enforced by application code.

## Nodes

| Label | Properties |
|---|---|
| `Agent` | `id` (string), `agent_id` (string), `name` (string), `created_at` (epoch milliseconds) |
| `Session` | `id` (UUID string), `agent_id`, `started_at` (epoch milliseconds), `goal` (string, optional; empty for now) |
| `Event` | `id` (UUID string), `agent_id`, `session_id`, `seq` (integer, order within session), `role` (currently `"user"`), `text` (string), `ts` (epoch milliseconds) |
| `Entity` | `id` (UUID string), `agent_id`, `name` (display name), `name_key` (normalized name), `type` (`Project`, `Tool`, `Person`, `Decision`, or `Preference`), `created_at` (epoch milliseconds) |
| `Fact` | `id` (UUID string), `agent_id`, `text`, `still_true` (boolean), `created_at` (epoch milliseconds), `replaced_at` (epoch milliseconds, set when replaced) |

All timestamps are epoch milliseconds. Every node carries `agent_id` so graph
queries can be scoped to an agent. The `Agent` node uses the same value for
`id` and `agent_id`.

## Relationships

| Relationship | Direction | Properties | Meaning |
|---|---|---|---|
| `OWNS` | `Agent` → `Session` | — | Agent owns the session |
| `OWNS` | `Agent` → `Fact` | — | Agent owns the fact |
| `CONTAINS` | `Session` → `Event` | `seq` | Session contains a message |
| `MENTIONS` | `Event` → `Entity` | — | Message mentions an entity |
| `ABOUT` | `Fact` → `Entity` | — | Fact concerns an entity |
| `CAME_FROM` | `Fact` → `Event` | — | Provenance: source message for a fact |
| `REPLACES` | new `Fact` → old `Fact` | — | New fact supersedes old fact |

Replaced facts remain in the graph with `still_true=false` and a
`replaced_at` timestamp. They must not be deleted.

## Indexes

`memory/schema.py` creates these indexes. Initialization is safe to rerun and
only suppresses errors indicating that an index already exists.

```cypher
CREATE INDEX FOR (e:Entity) ON (e.name_key)
CREATE INDEX FOR (e:Entity) ON (e.agent_id)
CREATE INDEX FOR (f:Fact) ON (f.id)
CREATE INDEX FOR (f:Fact) ON (f.still_true)
CREATE INDEX FOR (ev:Event) ON (ev.session_id)
```

## Multi-agent readiness

Mnemo currently has one agent, `agent_main`. Queries must scope memory data by
`agent_id`. A future agent can be represented by another `Agent` node; shared
facts and their sharing relationships are not part of the current schema
implementation.

## Example

For “I'm building Project X in Python,” the graph links the message event to
the `Project X` and `Python` entities. A fact such as “Project X uses Python”
is owned by the agent, connected to both entities with `ABOUT`, and connected
to its source event with `CAME_FROM`.

If the user later switches to Go, the new “Project X uses Go” fact is current
and has a `REPLACES` edge to the Python fact. The Python fact stays in the graph
as historical memory.
