# Mnemo — Day 1: Memory Core

> **Mnemo**: graph memory for AI agents, powered by FalkorDB
> Hackathon: **Graph Hacks** (WeMakeDevs x FalkorDB), Oct 15–18, 2026
> Track: **Track 2 — Agent Memory and Coordination**
> Day 1 date: **Oct 15** · Goal: a working memory core, **no UI, no API, no chat agent yet**
> Save this file as `docs/day1.md` in the repo.

This file is the full spec for Day 1. It is written so a coding agent can build everything in it without further questions. Sections 1–3 give project context (so decisions make sense); sections 4–15 are the actual Day 1 work.

---

## 1. Project in one paragraph

Mnemo is a **single AI project assistant** that remembers things across sessions. The user tells it about their projects, tools, decisions, people and preferences. After **every message**, a background step extracts durable facts and stores them in **FalkorDB** as a graph. When the user changes their mind ("switched Project X from Python to Go"), the old fact is **marked as replaced (not deleted)** and linked to the new one, so history is preserved. Before replying, the agent will recall relevant facts from the graph (including one hop of related entities). The frontend (Day 3) shows the memory graph growing live next to the chat.

**Why this satisfies the track:** FalkorDB is the persistent memory layer (not decoration). Memory survives across sessions, has provenance (every fact points to the message it came from), and handles updates over time.

**Hackathon requirements to keep in mind**
- FalkorDB must be the **primary** graph database and support a **central** part of the product.
- It must be a working product built around one graph problem.
- Memory must **persist across sessions**.
- Track 2 topics: episodic / semantic / procedural memory, multi-agent state sharing, high-concurrency memory lookups.
- Check the official hackathon page for exact judging and submission rules before submitting.

---

## 2. Decisions already made (do not re-debate)

| Topic | Decision |
|---|---|
| Name | **Mnemo**. Python package `mnemo`, repo name `mnemo` |
| Track | Track 2: Agent Memory and Coordination |
| Agents | **One agent now.** Architecture must allow adding more agents later (see §6.5) |
| Concept | **Project assistant**: remembers projects, tools, decisions, people, preferences |
| Extraction timing | **After every user message**, not once per session (live graph) |
| Extraction placement | Day 1: run synchronously inside a script. Day 2: move to a background task after the reply is sent |
| Agent orchestration | **LangGraph** (Day 2), flow is `recall → respond` only. Not needed on Day 1 |
| Memory layer | **Written by hand** using the FalkorDB Python client + Cypher. **No** LangChain/LlamaIndex auto graph-extraction helpers |
| Graph DB | FalkorDB via Docker, one graph, `agent_id` on every node |
| API | FastAPI (Day 2) |
| LLM provider | **Gemini API, free tier** (Google AI Studio key). Flash-Lite for extraction + conflict checks, Flash for chat (Day 2) |
| Recall | Entity-name match → current facts → **one-hop expansion** → always include Preferences → cap ~15, newest first (Day 2) |
| Frontend | Chat panel + live graph view, polling `/graph` (Day 3) |
| Prompts | Stored as **`.md` files** in `src/mnemo/prompts/`, loaded at runtime |
| Scope control | One agent, one schema. Research/support "modes" are optional later config changes (different entity types + instructions), not new architecture |

---

## 3. Overall architecture (full project)

```
┌──────────────────────────────────────────────────────────────────┐
│  FRONTEND (web)                                        [Day 3]   │
│  chat panel ──► POST /chat      graph view ◄── GET /graph        │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│  API SERVICE — FastAPI                                 [Day 2]   │
│  /chat ──► LangGraph agent        /graph ──► graph read queries  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│  AGENT — LangGraph, sync path (user waits)             [Day 2]   │
│  recall ──► respond ──► return reply                             │
│  recall: find entities in message ──► pull current Facts         │
│  respond: LLM answers using recalled Facts as context            │
└──────────────────────────────┬───────────────────────────────────┘
                               │  triggered after reply is sent
┌──────────────────────────────▼───────────────────────────────────┐
│  EXTRACTION (pipeline.process_message), background    [DAY 1*]   │
│  store Event ──► extract ──► match entities ──► conflict check   │
│  conflict: contradicts old Fact? ──► old one marked replaced     │
└──────────────────────────────┬───────────────────────────────────┘
                               │  reads (agent) + writes (pipeline)
┌──────────────────────────────▼───────────────────────────────────┐
│  FALKORDB (Docker) — one graph, agent_id on every node [DAY 1]   │
│  Agent · Session · Event · Entity · Fact                         │
│  indexes: Entity.name_key                                        │
└──────────────────────────────────────────────────────────────────┘

* Day 1 builds the extraction pipeline as plain functions, run from a script.
```

Two paths:
- **User-facing path** (recall → respond) never waits on extraction.
- **Extraction path** runs after the reply and updates the graph; the frontend polls it.

---

## 4. Day 1 scope

### In scope
1. Repo scaffolding: `pyproject.toml`, `.gitignore`, `.env.example`, `docker-compose.yml`, stub `README.md`
2. FalkorDB running in Docker (with the built-in browser UI)
3. Graph schema indexes and `docs/schema.md`
4. Write functions (`memory/write.py`): add session, add event, upsert entity, add fact, replace fact
5. Read functions (`memory/read.py`): current facts for entities, recent events, dump
6. **Extraction** (Prompt 1) as a function (`memory/extract.py`)
7. **Conflict check** (Prompt 2) as a function (`memory/conflicts.py`)
8. **Pipeline** `process_message(...)` tying 6–7 to the graph writes (`memory/pipeline.py`)
9. A **scenario runner script** that feeds ~15 messages across 2 sessions
10. A **dump script** to print the resulting memory in a readable way
11. Basic automated tests for the non-LLM logic

### Out of scope (do NOT build today)
- Recall logic (`memory/recall.py`), one-hop expansion → Day 2
- LangGraph flow (`agent/`), chat model replies, `prompts/system.md` → Day 2
- FastAPI (`api/`) and `cli.py` → Day 2
- Background task execution → Day 2
- Frontend (`frontend/`) → Day 3
- Skill / procedural-memory nodes → later, only if time allows
- Multiple agents → later (but keep the schema ready, §6.5)

Do not create empty placeholder folders for later days.

### Definition of done (Day 1)
The headline check: feed the scenario, then verify that **"Project X uses Python" is marked replaced and "Project X uses Go" is current, with a `REPLACES` edge between them**, and the old fact is still in the graph. All acceptance criteria are in §11.

---

## 5. Tech stack and project layout

**Stack:** Python 3.11+, `falkordb` (Python client), `google-genai` (Gemini SDK), `pydantic` v2, `python-dotenv`, `pytest`. Docker for FalkorDB.

**Full planned layout.** Files marked **[D1]** are built today; everything else is for later days and must **not** be created yet.

```
mnemo/
├── README.md                    [D1: short stub, finalized on Day 4]
├── pyproject.toml               [D1] makes `import mnemo` work via `pip install -e .`
├── requirements.txt             [D1] contains: -e .[dev]
├── .env.example                 [D1]
├── .gitignore                   [D1]
├── docker-compose.yml           [D1]
├── docs/
│   ├── day1.md                  [D1] this file
│   ├── schema.md                [D1] copy of §6 (schema reference)
│   └── PROMPT_CHANGELOG.md      [D1] create when a prompt is changed
├── src/mnemo/
│   ├── __init__.py              [D1]
│   ├── config.py                [D1] env loading
│   ├── models.py                [D1] pydantic models (LLM outputs, domain objects)
│   ├── llm/
│   │   ├── __init__.py          [D1]
│   │   └── client.py            [D1] Gemini wrapper: JSON mode, temp 0, 429 backoff
│   ├── memory/
│   │   ├── __init__.py          [D1]
│   │   ├── client.py            [D1] FalkorDB connection + graph handle
│   │   ├── schema.py            [D1] index creation / init (indexes, not constraints)
│   │   ├── normalize.py         [D1] normalize_name()
│   │   ├── write.py             [D1] Cypher writes
│   │   ├── read.py              [D1] Cypher reads (current facts, recent events, dump)
│   │   ├── extract.py           [D1] LLM → entities/facts + validation
│   │   ├── conflicts.py         [D1] add / replace / skip decision
│   │   ├── pipeline.py          [D1] process_message()
│   │   └── recall.py            (Day 2) lookup + one-hop expansion
│   ├── prompts/
│   │   ├── extract.md           [D1] Prompt 1
│   │   ├── conflict.md          [D1] Prompt 2
│   │   └── system.md            (Day 2) chat system prompt
│   ├── agent/                   (Day 2) state.py, nodes.py (recall, respond), graph.py
│   ├── api/                     (Day 2) main.py: /chat, /graph
│   └── cli.py                   (Day 2) chat loop
├── frontend/                    (Day 3)
├── scripts/
│   ├── init_graph.py            [D1]
│   ├── run_scenario.py          [D1]
│   └── dump_graph.py            [D1]
└── tests/
    ├── scenarios/
    │   └── day1_scenario.json   [D1]
    ├── test_normalize.py        [D1]
    ├── test_validation.py       [D1] LLM-output validation, no network
    ├── test_schema.py           [D1] needs FalkorDB: index creation is idempotent
    ├── test_write_read.py       [D1] needs FalkorDB: writes and reads
    └── test_recall.py           (Day 2)
```

**Rules**
- **All Cypher lives in `memory/write.py`, `memory/read.py` and `memory/schema.py`.** No Cypher strings anywhere else. This keeps Day 2 (agent, API) clean.
- All LLM calls go through `llm/client.py`. No other module imports the Gemini SDK.
- Imports use the package name: `from mnemo.memory.write import ...`.

### 5.1 `pyproject.toml` requirements
- Project name `mnemo`, Python `>=3.11`.
- Dependencies: `falkordb`, `google-genai`, `pydantic>=2`, `python-dotenv`.
- Optional dependency group `dev`: `pytest`.
- Setuptools with `src/` layout: find packages under `src`, and **include package data** so `prompts/*.md` ships with the package.
- `requirements.txt` contains only `-e .[dev]`, so dependencies live in one place.

### 5.2 `.gitignore`
`.env`, `.venv/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`, `logs/`, `node_modules/`.

### 5.3 Prompt loading
Prompts live as plain files in `src/mnemo/prompts/`. Add a tiny loader (e.g. `load_prompt("extract")` in `config.py` or `llm/client.py`) that reads `Path(__file__).parent / "prompts" / f"{name}.md"` (adjust the relative path to the module's location). Editing a prompt must not require touching Python code.

---

## 6. Graph schema

FalkorDB is schemaless, so the schema below is a **convention enforced by code**. Also write this section into `docs/schema.md`.

### 6.1 Plain-language summary
- **Agent**: the one assistant
- **Session**: one conversation
- **Event**: one message inside a session
- **Entity**: a *thing* the user talks about (Project X, Go, Rafael, …)
- **Fact**: a short takeaway ("Project X uses Go"), which can later become *no longer true*

### 6.2 Nodes

| Label | Properties |
|---|---|
| `Agent` | `id` (str), `name` (str), `created_at` (int ms) |
| `Session` | `id` (str uuid), `agent_id`, `started_at` (int ms), `goal` (str, optional, empty for now) |
| `Event` | `id` (str uuid), `agent_id`, `session_id`, `seq` (int, order within session), `role` (`"user"` for now), `text` (str), `ts` (int ms) |
| `Entity` | `id` (str uuid), `agent_id`, `name` (display name), `name_key` (normalized, see §7.1), `type` (`Project\|Tool\|Person\|Decision\|Preference`), `created_at` (int ms) |
| `Fact` | `id` (str uuid), `agent_id`, `text`, `still_true` (bool), `created_at` (int ms), `replaced_at` (int ms, only set when replaced) |

All timestamps are **epoch milliseconds (int)** for easy sorting.

### 6.3 Relationships

| Edge | From → To | Properties | Meaning |
|---|---|---|---|
| `OWNS` | Agent → Session | none | agent owns the session |
| `OWNS` | Agent → Fact | none | agent owns the fact |
| `CONTAINS` | Session → Event | `seq` | session contains the message |
| `MENTIONS` | Event → Entity | none | message mentions the thing |
| `ABOUT` | Fact → Entity | none | fact is about the thing |
| `CAME_FROM` | Fact → Event | none | **provenance**: the message the fact was extracted from |
| `REPLACES` | new Fact → old Fact | none | new fact replaces the old one |

### 6.4 Indexes (created by `memory/schema.py`, must be idempotent)

```cypher
CREATE INDEX FOR (e:Entity) ON (e.name_key)
CREATE INDEX FOR (e:Entity) ON (e.agent_id)
CREATE INDEX FOR (f:Fact)   ON (f.id)
CREATE INDEX FOR (f:Fact)   ON (f.still_true)
CREATE INDEX FOR (ev:Event) ON (ev.session_id)
```

FalkorDB raises an error if an index already exists. Wrap each in try/except and ignore the "already indexed" error so `init_graph.py` can be re-run safely.

### 6.5 Multi-agent readiness (do this now, costs nothing)
- **`agent_id` is a property on every node** and **every query filters by `agent_id`**.
- There is an explicit `Agent` node even though there is only one (`agent_id = "agent_main"`).
- Adding a second agent later = a new `Agent` node. **Shared memory** later = one `Fact` linked to two agents (e.g. a `KNOWS`/`SHARED_WITH` edge). Do **not** build this today, just don't block it.

### 6.6 Example: what one message becomes

User says: *"I'm building Project X in Python."*

```
(Agent agent_main)-[:OWNS]->(Session s1)-[:CONTAINS {seq:2}]->(Event e2 "I'm building Project X in Python.")
(Event e2)-[:MENTIONS]->(Entity "Project X" : Project)
(Event e2)-[:MENTIONS]->(Entity "Python"    : Tool)
(Fact "Project X uses Python" still_true=true)-[:ABOUT]->(Project X)
(Fact "Project X uses Python")-[:ABOUT]->(Python)
(Fact "Project X uses Python")-[:CAME_FROM]->(Event e2)
(Agent agent_main)-[:OWNS]->(Fact "Project X uses Python")
```

Later: *"Actually I switched Project X from Python to Go."*

```
(Fact "Project X uses Go" still_true=true)-[:REPLACES]->(Fact "Project X uses Python")
Fact "Project X uses Python":  still_true=false, replaced_at=<ts>   (kept, not deleted)
```

---

## 7. Module specs

### 7.1 `memory/normalize.py`

`normalize_name(name) -> name_key`:
- strip, collapse internal whitespace to a single space, lowercase
- keep punctuation that is part of the name (e.g. `C++`, `Node.js`); do not strip it
- `"Project X"`, `"project x"`, `" Project  X "` → `"project x"`

Entity identity = (`agent_id`, `name_key`). The **display name** (`name`) is the first spelling seen.

If an entity already exists with a *different* type than the model returned, **keep the existing type** and log a warning.

### 7.2 `memory/client.py`
- Connect using `FALKORDB_HOST`, `FALKORDB_PORT`, optional password.
- `get_graph()` returns `db.select_graph(FALKORDB_GRAPH)`.
- Use query **parameters** (not string formatting) for all values.

### 7.3 `memory/write.py` and `memory/read.py` — functions to implement

All functions take `agent_id` where relevant. Each does one clear thing.

**`write.py`**

| Function | Behavior |
|---|---|
| `ensure_agent(agent_id, name)` | `MERGE` the Agent node |
| `create_session(agent_id) -> session_id` | create Session + `OWNS` edge |
| `add_event(agent_id, session_id, text, role="user") -> event` | compute next `seq` for the session, create Event + `CONTAINS` edge (with `seq`), return event dict |
| `upsert_entity(agent_id, name, type) -> entity` | `MERGE` on (`agent_id`, `name_key`); `ON CREATE SET` id/name/type/created_at; return entity dict (including actual stored type) |
| `link_event_mentions(event_id, entity_id)` | `MERGE` a `MENTIONS` edge (no duplicates) |
| `add_fact(agent_id, text, about_entity_ids, event_id) -> fact` | create Fact (`still_true=true`), `ABOUT` edges, `CAME_FROM` edge, `OWNS` edge from Agent |
| `replace_facts(new_fact_id, old_fact_ids, ts)` | for each old fact: set `still_true=false`, `replaced_at=ts`; create `(new)-[:REPLACES]->(old)` |

**`read.py`**

| Function | Behavior |
|---|---|
| `get_recent_events(session_id, n=3) -> list[str]` | last `n` user messages **before** the current one, oldest first (used as RECENT context) |
| `get_current_facts_for_entities(agent_id, entity_ids) -> list[fact]` | all `still_true=true` facts with an `ABOUT` edge to any of the entities, `DISTINCT`, newest first |
| `dump_memory(agent_id) -> dict` | everything needed by `dump_graph.py`: entities, current facts, replaced facts with what replaced them, source message per fact |

Reference Cypher (adapt as needed):

```cypher
// upsert entity
MERGE (e:Entity {agent_id:$agent_id, name_key:$name_key})
ON CREATE SET e.id=$id, e.name=$name, e.type=$type, e.created_at=$ts
RETURN e.id AS id, e.name AS name, e.type AS type

// current facts for entities
MATCH (f:Fact {agent_id:$agent_id, still_true:true})-[:ABOUT]->(e:Entity {agent_id:$agent_id})
WHERE e.id IN $entity_ids
RETURN DISTINCT f.id AS id, f.text AS text, f.created_at AS created_at
ORDER BY created_at DESC

// replace
MATCH (old:Fact {id:$old_id})
SET old.still_true=false, old.replaced_at=$ts
WITH old
MATCH (new:Fact {id:$new_id})
CREATE (new)-[:REPLACES]->(old)
```

### 7.4 `llm/client.py` — Gemini wrapper

- Uses the `google-genai` SDK with `GEMINI_API_KEY`.
- One function: `generate_json(model, system_prompt, user_content) -> str` (returns raw text).
- Config: **temperature 0**, `response_mime_type="application/json"`.
- **Retry on rate limits (HTTP 429 / resource-exhausted)** with exponential backoff + jitter, up to 5 tries. The free tier has real limits, so a 429 must never crash a run.
- **Model names come from env** (`EXTRACTION_MODEL`, `CONFLICT_MODEL`). Do not hardcode them. Model names change often; **verify the current free-tier model names and limits in Google AI Studio** before starting.
- Log model, latency and (in verbose mode) the raw output.

Free-tier notes:
- Free-tier access covers Flash / Flash-Lite class models; Pro models are paid.
- Limits depend on model and account; check AI Studio.
- Free-tier inputs/outputs may be used by Google to improve its models. **Use only fake/demo data in scenarios.**
- Each message costs about 1 extraction call + up to N conflict calls (one per new fact that has existing facts to compare against). The pre-filters in §7.7 reduce this.

### 7.5 Prompt 1 — Extraction (`src/mnemo/prompts/extract.md`)

Use as the **system instruction**. Use it verbatim as a starting point. The file contains only the prompt text below (no surrounding markdown fences).

```
You extract memory from a conversation between a user and their project assistant.

Input:
- RECENT: the last few messages, for context only
- MESSAGE: the new user message to extract from

Return ONLY valid JSON, no other text:
{
  "entities": [
    {"name": "string", "type": "Project|Tool|Person|Decision|Preference"}
  ],
  "facts": [
    {"text": "string", "about": ["entity name", ...]}
  ]
}

Rules:
1. Extract only from MESSAGE. Use RECENT only to resolve words like "it" or "that".
2. Save only durable information: what projects exist, tools and tech used,
   decisions made, preferences, people involved, status changes.
   Skip greetings, thanks, questions, and small talk.
3. Facts are short, standalone, third-person statements.
   Good: "Project X uses Go". Bad: "he said he switched it".
4. One idea per fact. Split compound statements.
5. Every fact must list at least one entity in "about", and that entity
   must also appear in "entities".
6. Use the user's canonical spelling for names (e.g. "Project X", not
   "project x"). Reuse the same name every time.
7. Record only what the user states. Do not infer or guess.
8. If nothing is worth saving, return {"entities": [], "facts": []}.

Example
MESSAGE: "I switched Project X from Python to Go last week, mostly for speed."
Output:
{"entities":[{"name":"Project X","type":"Project"},{"name":"Go","type":"Tool"},{"name":"Python","type":"Tool"}],
 "facts":[{"text":"Project X uses Go","about":["Project X","Go"]},
          {"text":"Project X switched from Python to Go for speed","about":["Project X","Python","Go"]}]}
```

**User content format** sent to the model:

```
RECENT:
- <previous user message 1>
- <previous user message 2>
MESSAGE: <current user message>
```

(If there is no recent context, send `RECENT:\n(none)`.)

### 7.6 Prompt 2 — Conflict check (`src/mnemo/prompts/conflict.md`)

Same rule: the file contains only the prompt text.

```
You compare a NEW fact against EXISTING facts about the same entities.

Return ONLY valid JSON:
{"action": "add" | "replace" | "skip", "replaces": ["fact id", ...]}

- "replace": NEW contradicts or updates an EXISTING fact, so the old one is
  no longer true. List its id(s) in "replaces".
- "skip": NEW says the same thing as an EXISTING fact.
- "add": NEW is additional information that doesn't conflict.

Examples: "uses Python" vs NEW "uses Go" -> replace.
"uses Go" vs NEW "uses Go" -> skip.
"uses Go" vs NEW "deadline is Friday" -> add.
When unsure, choose "add".
```

**User content format:**

```
NEW: Project X uses Go
EXISTING:
- [id: 7c1e...] Project X uses Python
- [id: 91ab...] Project X is a task manager app
```

This is the hard part of the project. Spend real testing time here (§10).

### 7.7 `memory/extract.py` and `memory/conflicts.py`

**Extraction function:** `extract(message, recent) -> ExtractionResult`

1. Build user content (§7.5), call `generate_json(EXTRACTION_MODEL, ...)`.
2. Strip stray ```json fences defensively, `json.loads`.
3. Validate with pydantic (`ExtractionResult`, defined in `models.py`).
4. **Post-validation cleanup in code** (do not trust the model):
   - drop entities whose `type` is not in the allowed set
   - drop facts with empty `text` or empty `about`
   - drop `about` names that aren't in `entities` (compare by `name_key`); drop the fact if nothing is left
   - de-duplicate entities by `name_key`
5. If JSON is malformed or fails validation: **retry once**; if it fails again, return an empty result and log (never crash, never write garbage).

**Conflict function:** `check_conflict(new_fact_text, existing_facts) -> ConflictDecision`

Pre-filters (no LLM call):
1. If `existing_facts` is empty → `add`.
2. If the normalized text of NEW exactly equals an existing fact's normalized text → `skip`.

Otherwise call `generate_json(CONFLICT_MODEL, ...)`, parse, validate. Rules:
- `action` must be one of `add|replace|skip`, otherwise treat as `add`.
- `replaces` must be a **subset of the existing fact ids that were sent**. Drop unknown ids. If action is `replace` and no valid ids remain → treat as `add`.
- If `action != "replace"`, force `replaces = []`.
- Malformed output after one retry → `add` (the safe default; matches "when unsure, choose add").

### 7.8 `memory/pipeline.py` — `process_message`

`process_message(agent_id, session_id, text) -> ProcessResult`

```
1. recent = read.get_recent_events(session_id, n=3)
2. event  = write.add_event(agent_id, session_id, text)          # store first, always
3. result = extract(text, recent)
4. for each entity in result.entities:
       ent = write.upsert_entity(agent_id, name, type)
       write.link_event_mentions(event.id, ent.id)
   build map: name_key -> entity id
5. for each fact in result.facts:
       entity_ids = [map[normalize_name(n)] for n in fact.about]
       existing   = read.get_current_facts_for_entities(agent_id, entity_ids)
       decision   = check_conflict(fact.text, existing)
       if decision.action == "skip":    continue
       new_fact   = write.add_fact(agent_id, fact.text, entity_ids, event.id)
       if decision.action == "replace": write.replace_facts(new_fact.id, decision.replaces, now)
6. return a summary: entities created/reused, facts added, facts replaced, facts skipped
```

Important details:
- **The Event is stored before extraction**, so even if extraction fails the message is not lost.
- `get_recent_events` is called **before** `add_event`, so RECENT excludes the current message.
- Process facts **sequentially**, and re-read existing facts per fact, so a fact added earlier in the same message is visible to later ones.
- Wrap extraction/conflict in try/except; on failure log and continue with the rest.
- `ProcessResult` is a small pydantic model in `models.py`; the scenario runner prints it per message.
- On Day 2 the `/chat` endpoint calls this same function as a background task. Keep it free of any CLI or script assumptions.

---

## 8. Environment setup

### 8.1 `docker-compose.yml`

```yaml
services:
  falkordb:
    image: falkordb/falkordb:latest
    ports:
      - "6379:6379"   # database
      - "3000:3000"   # FalkorDB browser UI
    volumes:
      - falkordb_data:/var/lib/falkordb/data
    restart: unless-stopped

volumes:
  falkordb_data:
```

Persisting the volume matters: **memory must survive restarts** (that is the whole point of the track). After setup, test: add data, `docker compose restart`, confirm the data is still there. If the image's data path differs, check the FalkorDB docs and adjust the volume mount.

### 8.2 `.env.example`

```
GEMINI_API_KEY=your_key_from_ai_studio
# Verify current free-tier model names in Google AI Studio; these change.
EXTRACTION_MODEL=gemini-flash-lite-latest
CONFLICT_MODEL=gemini-flash-lite-latest

FALKORDB_HOST=localhost
FALKORDB_PORT=6379
FALKORDB_GRAPH=mnemo

AGENT_ID=agent_main
AGENT_NAME=Mnemo
LOG_LEVEL=INFO
```

### 8.3 Run order

```bash
docker compose up -d
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # installs mnemo in editable mode + dev deps
cp .env.example .env                 # then fill in the key
python scripts/init_graph.py         # indexes + Agent node (safe to re-run)
python scripts/run_scenario.py tests/scenarios/day1_scenario.json --verbose
python scripts/dump_graph.py
pytest
```

Open the FalkorDB browser at `http://localhost:3000` to visually inspect the graph.

---

## 9. Scripts

### `scripts/init_graph.py`
Create indexes (idempotent) and `ensure_agent`. Print what it did.

### `scripts/run_scenario.py`
- Args: path to scenario JSON, `--verbose`, `--reset` (optional: delete the graph first for a clean run).
- Scenario JSON format:
  ```json
  {
    "sessions": [
      {"name": "A", "messages": ["...", "..."]},
      {"name": "B", "messages": ["...", "..."]}
    ]
  }
  ```
- For each session: `create_session`, then each message through `process_message`, printing per message: the text, extracted entities/facts, and the decision for each fact (`add`/`replace`/`skip`).
- Sessions run **in order** to simulate "closed the chat, came back later".

### `scripts/dump_graph.py`
Print, for the agent:
1. Entities grouped by type
2. **Current facts** (`still_true=true`) with the entities they're about
3. **Replaced facts** with `replaced_at` and the text of the fact that replaced them
4. For each fact, the source message text (follow `CAME_FROM`)

Plain text output is fine. It's for you and the coding agent to eyeball.

---

## 10. Test scenario (`tests/scenarios/day1_scenario.json`)

Use fake/demo data only. Two sessions. "Expected" describes ideal behavior; the LLM may phrase fact text differently, so judge **meaning**, not exact wording.

### Session A

| # | Message | Expected |
|---|---|---|
| 1 | "Hi, I'm starting a new project called Project X, it's a task manager app." | Entity `Project X` (Project). Fact like "Project X is a task manager app". |
| 2 | "I'm building Project X in Python with FastAPI." | Entities `Python`, `FastAPI` (Tool). Facts "Project X uses Python", "Project X uses FastAPI" (split, one idea each). |
| 3 | "I prefer short, direct answers." | A `Preference` entity (e.g. "Concise answers"). A fact stating the preference. |
| 4 | "Thanks!" | **Nothing extracted.** |
| 5 | "We decided to use PostgreSQL for the database." | `PostgreSQL` (Tool) and/or a `Decision` entity. A fact linking PostgreSQL to Project X (the model must use RECENT to know "we" = Project X). |

### Session B (new session, memory must already exist)

| # | Message | Expected |
|---|---|---|
| 6 | "Rafael is helping me on Project X with the frontend." | `Rafael` (Person). Fact "Rafael works on Project X frontend" (or similar). |
| 7 | "Actually I switched Project X from Python to Go for speed." | **REPLACE**: "Project X uses Python" → `still_true=false`; new "Project X uses Go" current; `REPLACES` edge. **Headline test.** |
| 8 | "What's the weather like today?" | **Nothing extracted.** |
| 9 | "I'm using Redis for caching in Project X." | Add `Redis` (Tool) + fact. |
| 10 | "Project X's deadline is October 30." | Add fact (deadline). |
| 11 | "The deadline for Project X moved to November 15." | **REPLACE** the October 30 deadline fact. |
| 12 | "I use Go for Project X." | **SKIP** (already known). No new fact. |
| 13 | "I'm starting a second project, Project Y, a CLI tool in Rust." | New `Project Y`, `Rust`; facts. Must **not** touch Project X facts. |
| 14 | "I changed my mind, I prefer detailed explanations." | **REPLACE** the "short, direct answers" preference. |
| 15 | "Rafael left the project." | *Stretch case.* Ideally replaces/ends the Rafael fact. If the model chooses `add`, that is acceptable on Day 1 (log it as a known weakness). |

### Things to watch while testing
- Duplicate entities from spelling variants (`Project X` vs `project x`): should be **one** node.
- Over-extraction (junk facts from small talk): tune Prompt 1.
- Wrong replacements (e.g. Project Y facts replacing Project X facts): tune Prompt 2.
- Compound facts not being split.
- Spend real time on messages 7, 11, 14. They are the demo.

---

## 11. Acceptance criteria (Day 1 checklist)

**Infra**
- [ ] `docker compose up -d` brings up FalkorDB; browser opens at `localhost:3000`
- [ ] `pip install -r requirements.txt` works and `import mnemo` works from anywhere in the venv
- [ ] `init_graph.py` runs twice without errors
- [ ] Data survives `docker compose restart`

**Schema and writes**
- [ ] Every node has `agent_id`; every query filters on it
- [ ] Re-processing the same entity name in different casing yields **one** `Entity` node
- [ ] Each `Fact` has `ABOUT` edge(s), a `CAME_FROM` edge to an `Event`, and an `OWNS` edge from the Agent
- [ ] Events in a session have increasing `seq`
- [ ] No Cypher outside `memory/write.py`, `memory/read.py`, `memory/schema.py`

**Pipeline**
- [ ] Messages 4 and 8 ("Thanks!", weather) produce no facts
- [ ] Message 7 replaces the Python fact (old: `still_true=false` + `replaced_at`, still present; edge `REPLACES` exists)
- [ ] Message 11 replaces the October deadline
- [ ] Message 12 is skipped as a duplicate
- [ ] Message 14 replaces the old preference
- [ ] Project Y facts don't replace Project X facts
- [ ] Malformed LLM JSON never crashes the run (test by feeding a bad string to the validators)
- [ ] A 429 triggers backoff and retry, not a crash
- [ ] Editing `prompts/extract.md` changes behavior without any Python change

**Tooling**
- [ ] `dump_graph.py` shows current facts, replaced facts (and what replaced them), and source messages
- [ ] `docs/schema.md` exists and matches §6
- [ ] `pytest` passes

---

## 12. Testing notes

- `test_normalize.py`: casing, whitespace, punctuation (`C++`, `Node.js`).
- `test_validation.py` (no network): feed crafted bad outputs to the extraction/conflict validators: invalid types, `about` naming unknown entities, unknown `replaces` ids, `replace` with no valid ids, malformed JSON, code-fenced JSON.
- `test_schema.py` (needs FalkorDB): run index creation twice; no error.
- `test_write_read.py` (needs FalkorDB): use a **separate graph name** (e.g. `mnemo_test`) and clean it between tests. Cover upsert idempotency, `seq` ordering, `replace_facts`, and current-fact queries.
- Don't write automated tests that call the real LLM. Use the scenario runner for that.

---

## 13. Known risks and rules of thumb

- **Conflict detection is judgment-based.** When unsure, `add`. Wrong `add` is harmless (a stray extra fact); wrong `replace` destroys information.
- **Never delete facts.** Replaced facts stay as history. That history is a demo feature.
- **Never trust LLM output.** Validate and clean in code (§7.7).
- **Free-tier limits are real.** Keep backoff on, avoid needless calls, and don't run the full scenario repeatedly in a tight loop.
- **Free-tier data may be used for training.** Fake data only.
- **Keep Cypher inside `memory/` only.**
- **Don't build ahead.** No recall, API, agent, or UI today.

---

## 14. Roadmap (so Day 1 choices make sense)

**Day 2 (Oct 16): agent and API**
- `memory/recall.py`: find entities in the message (case-insensitive match on `name_key`, no LLM call) → pull current facts → **one-hop expansion** to connected entities → always include `Preference` facts → newest first, cap ~15 → format as a short "what you know about the user" block. If nothing matches: preferences + a few recent facts.
- `agent/`: LangGraph flow `recall → respond` (chat model = Gemini Flash). Extraction is **not** a graph node; it is a background call to `pipeline.process_message` after the reply is sent.
- `api/main.py`: `/chat` (returns reply + ids of recalled facts) and `/graph`.
- `cli.py`: simple chat loop.
- *Done when:* chat via API, close the session, start a new one, and it remembers.

**Day 3 (Oct 17): frontend**
- Chat panel left, live graph right, polling `/graph` every 1–2 s.
- Node colors by type; replaced facts faded/struck through with a "replaced by" link; recalled nodes highlighted after each reply; click a fact to see its source message.
- *Done when:* the full demo story works in the browser.
- If behind: simplify to a basic force-directed layout.

**Day 4 (Oct 18): polish and submit**
- Fix extraction bugs, write and rehearse the demo script twice, record a backup video, finalize `README.md` with architecture diagram, submit. **Nothing new is built on Day 4.**

**Cut list if behind (in order):** one-hop expansion → click-for-source → animations. **Never cut** replace-old-fact or the live graph.

**Demo story (≈2 min):** tell the agent about a project in session 1 → start session 2 → it remembers → change your mind → watch the old fact fade and the new one appear → show where each fact came from. The visible memory (provenance and replacement history) is what sets Mnemo apart from a generic "assistant with memory".

**Optional later:** more modes (research, support) as config changes (different entity types + instructions); a second agent sharing selected facts; procedural-memory `Skill` nodes.

---

## 15. Instructions for the coding agent

1. Build exactly what's marked **[D1]** in §5 and specified in §4–§12. Do not add features or folders from later days.
2. Create individual files (no zip archives); follow the layout in §5.
3. Keep all Cypher in `memory/write.py`, `memory/read.py` and `memory/schema.py`, and use query parameters.
4. Route every LLM call through `llm/client.py`.
5. Read all configuration (keys, model names, host/port, agent id) from environment variables.
6. Load prompts from `src/mnemo/prompts/*.md`. Use them as the starting point; iterate on them only based on scenario results, and note any change in `docs/PROMPT_CHANGELOG.md`.
7. When done, run the scenario and report: the per-message decisions, the output of `dump_graph.py`, and any acceptance criteria in §11 that are not met.