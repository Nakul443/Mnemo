# Mnemo

# Live Link
https://mnemo-chi-one.vercel.app/

> **Graph memory for AI agents, powered by FalkorDB.**
> Built for **Graph Hacks** (WeMakeDevs x FalkorDB) · Track 2: **Agent Memory and Coordination**

Mnemo is a project assistant with persistent, structured graph memory. When users talk about their projects, tools, decisions, people, and preferences, Mnemo extracts durable facts into **FalkorDB** in the background. Before each response, Mnemo traverses the memory graph to recall relevant facts—including 1-hop related entities and user preferences. When users change their mind (e.g., *"Switched Project X from Python to Go"*), old facts are preserved as historical memory with a directed `REPLACES` edge pointing from the new fact to the old one.

---

## Demo



Live demo uses limited free-tier AI quota; if replies fail, watch the video.

---

## Why a Graph Database?

A graph database is not decorative in Mnemo—it powers the core memory capabilities:

1. **Provenance (`CAME_FROM`)**: Every extracted fact links directly back to the specific conversation event (`Event`) it was learned from.
2. **History as Graph Structure (`REPLACES`)**: Changed facts are never deleted. A new fact creates a directed `REPLACES` edge to the superseded fact, preserving complete knowledge evolution.
3. **Related Memory Expansion (1-Hop Traversal)**: Recall traverses `Entity <- ABOUT - Fact - ABOUT -> Entity` paths to discover related tools or projects connected through shared facts.
4. **Typed Preference Retention**: Preferences are explicit entity nodes (`type: 'Preference'`), enabling reliable preference retrieval across arbitrary conversation topics.

---

## Architecture & System Flow

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (React + Vite + TypeScript, Port 5173)                                  │
│  Chat Panel ──► POST /chat                     Live Graph View ◄── GET /graph     │
└─────────────────────────┬──────────────────────────────────────────────────────────┘
                          │ HTTP (CORS Enabled)
┌─────────────────────────▼──────────────────────────────────────────────────────────┐
│  FASTAPI BACKEND SERVICE (Python 3.11+, Port 8000)                                 │
│  POST /sessions · POST /chat · GET /graph · GET /sessions/{id}/messages            │
└────────────────────┬───────────────────────────────────────────────────────────────┘
                     │ run_turn()
┌────────────────────▼───────────────────────────────────────────────────────────────┐
│  AGENT SERVICE (LangGraph: recall ──► respond)                                     │
│  1. Load chat history from FalkorDB                                                │
│  2. Store user Event in FalkorDB                                                   │
│  3. LangGraph turn: non-LLM Recall ──► Gemini Flash Respond                        │
│  4. Store assistant Event in FalkorDB                                              │
│  5. Submit user message to Background Extraction Queue                             │
└────────────────────┬────────────────────────────────────────┬──────────────────────┘
                     │ recall reads                           │ background job
                     │                      ┌─────────────────▼──────────────────────┐
                     │                      │ SINGLE-WORKER BACKGROUND QUEUE         │
                     │                      │ ThreadPoolExecutor(max_workers=1) FIFO │
                     │                      │ Extraction & Conflict Check Pipeline   │
                     │                      └─────────────────┬──────────────────────┘
┌────────────────────▼────────────────────────────────────────▼──────────────────────┐
│  FALKORDB GRAPH DATABASE (Docker, Port 6380)                                       │
│  Nodes: Agent · Session · Event · Entity · Fact                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### The Memory Processing Loop

1. **Store Event**: Incoming user messages are persisted as `Event` nodes immediately.
2. **Recall (Fast & Deterministic)**: Regex-based entity detection matches whole phrases. Fetches direct facts, 1-hop related entity facts, and user preference facts without an LLM call.
3. **Respond**: LangGraph executes `recall -> respond`, injecting formatted memory context into Gemini Flash.
4. **Immediate Reply**: Assistant response is saved and returned to the user without waiting for extraction.
5. **Background Extraction & Conflict Check**: A single FIFO worker thread extracts durable facts, evaluates conflicts against existing facts (`add`, `replace`, `skip`), and updates FalkorDB.

---

## Graph Data Model

### Node Schema

| Label | Properties | Description |
|---|---|---|
| `Agent` | `id` (str), `agent_id` (str), `name` (str), `created_at` (int ms) | Owning agent instance. |
| `Session` | `id` (UUID), `agent_id` (str), `started_at` (int ms), `goal` (str) | Conversation session. |
| `Event` | `id` (UUID), `agent_id` (str), `session_id` (str), `seq` (int), `role` (`"user"`/`"assistant"`), `text` (str), `ts` (int ms) | Chat message turn. |
| `Entity` | `id` (UUID), `agent_id` (str), `name` (str), `name_key` (normalized str), `type` (`Project`/`Tool`/`Person`/`Decision`/`Preference`), `created_at` (int ms) | Durable entity. |
| `Fact` | `id` (UUID), `agent_id` (str), `text` (str), `still_true` (bool), `created_at` (int ms), `replaced_at` (int ms, optional) | Standalone fact statement. |

### Relationship Schema

| Relationship | Direction | Description |
|---|---|---|
| `OWNS` | `Agent` $\rightarrow$ `Session` / `Fact` | Agent ownership |
| `CONTAINS` | `Session` $\rightarrow$ `Event` | Session message sequence |
| `MENTIONS` | `Event` $\rightarrow$ `Entity` | Message entity references |
| `ABOUT` | `Fact` $\rightarrow$ `Entity` | Fact entity subject |
| `CAME_FROM` | `Fact` $\rightarrow$ `Event` | Provenance link to original message |
| `REPLACES` | new `Fact` $\rightarrow$ old `Fact` | Directed supersession link |

### Fact Supersession Subgraph

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

---

## Cypher Queries

Mnemo relies on Cypher for graph operations. Full query definitions are documented in [`docs/queries.md`](docs/queries.md).

| Operation | Query Purpose | Location |
|---|---|---|
| **Graph Indexes** | Idempotent index initialization for entities, facts, and events | `backend/src/mnemo/memory/schema.py` |
| **Upsert Entity** | Merge entity by `(agent_id, name_key)` preserving initial display name | `backend/src/mnemo/memory/write.py` |
| **Add Fact** | Create fact node with `OWNS`, `CAME_FROM`, and `ABOUT` edges | `backend/src/mnemo/memory/write.py` |
| **Replace Fact** | Set `still_true=false` and create `(new)-[:REPLACES]->(old)` edge | `backend/src/mnemo/memory/write.py` |
| **1-Hop Neighbor Expansion** | Surface related entities sharing current facts | `backend/src/mnemo/memory/read.py` |
| **Graph Snapshot** | Pull nodes, ABOUT edges, and REPLACES edges for UI rendering | `backend/src/mnemo/memory/read.py` |

---

## Setup & Running Instructions

### Prerequisites
- **Docker** & Docker Compose
- **Python 3.11+**
- **Node.js 20+** & npm
- **Google AI Studio Gemini API Key** (Free tier)

### 1. Start FalkorDB
```bash
cd backend
docker compose up -d
```
*FalkorDB runs on port `6380` (database) and port `3000` (FalkorDB Browser UI).*

### 2. Configure Backend & Start API
```bash
cd backend
cp .env.example .env
# Edit .env and insert your GEMINI_API_KEY

python -m venv ../.venv
source ../.venv/bin/activate
# or on Windows: ..\.venv\Scripts\activate
pip install -r requirements.txt

# Run FastAPI server
uvicorn mnemo.api.main:app --port 8000
```

### 3. Start Frontend
In a new terminal:
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

### 4. Running Tests
```bash
# Backend unit tests (33 tests)
cd backend && ../.venv/bin/pytest

# Frontend unit tests (10 tests)
cd frontend && npm test
```

### 5. Reset Memory Graph
To wipe graph data and start fresh:
```bash
cd backend && docker compose exec falkordb redis-cli GRAPH.DELETE mnemo
```

---

## Deploying

### Frontend (Vercel)
- Set `VITE_API_BASE_URL` to your backend's public URL.
- Note: Environment variables are baked in at build time, so redeploy after changes.

### Backend (Render)
- **Start Command**: `uvicorn mnemo.api.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/health`
- **CORS_ORIGINS**: Set to the exact frontend URL without trailing slash (e.g. `https://your-app.vercel.app`).
- **Single Instance Only**: Run as a single instance because memory extraction relies on an in-memory single-worker FIFO queue.

### Database (FalkorDB Cloud)
- FalkorDB Cloud Free has no TLS and no persistence; use `FALKORDB_SSL=false` with the provided host, port, username, and password.

---

## Environment Configuration

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(Required)* | Google AI Studio API key |
| `EXTRACTION_MODEL` | `gemini-2.5-flash-lite` | Model for fact extraction |
| `CONFLICT_MODEL` | `gemini-2.5-flash-lite` | Model for conflict resolution |
| `CHAT_MODEL` | `gemini-2.5-flash` | Model for chat responses |
| `FALKORDB_HOST` | `localhost` | FalkorDB database host |
| `FALKORDB_PORT` | `6380` | FalkorDB database port |
| `FALKORDB_USERNAME` | `""` | FalkorDB database username |
| `FALKORDB_PASSWORD` | `""` | FalkorDB database password |
| `FALKORDB_SSL` | `false` | Enable SSL/TLS (`false` for FalkorDB Cloud Free) |
| `FALKORDB_URL` | *(Optional)* | Full connection URI (e.g. `redis://...`) |
| `FALKORDB_GRAPH` | `mnemo` | FalkorDB graph name |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed CORS origins |
| `AGENT_ID` | `agent_main` | Default agent identifier |
| `AGENT_NAME` | `Mnemo` | Agent display name |
| `LOG_LEVEL` | `INFO` | Application log level |
| `PORT` | `8000` | FastAPI server port |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

---

## Project Structure

```
mnemo/
├── backend/
│   ├── src/mnemo/
│   │   ├── agent/            # LangGraph flow & turn service
│   │   ├── api/              # FastAPI application & Pydantic schemas
│   │   ├── llm/              # Gemini SDK wrapper with 429/503 retry
│   │   ├── memory/           # FalkorDB client, Cypher writes/reads, recall, pipeline, worker
│   │   ├── prompts/          # System prompts (extract.md, conflict.md, system.md)
│   │   ├── config.py         # Env settings loader
│   │   └── models.py         # Validated domain models
│   ├── scripts/              # init_graph.py, run_scenario.py, dump_graph.py
│   ├── tests/                # Pytest unit & integration test suite
│   ├── docker-compose.yml
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/              # Typed fetch API client
│   │   ├── components/       # ChatPanel, GraphPanel, Header, NodeDetail, RecalledChips
│   │   ├── hooks/            # useSession, useChat, useGraphPolling
│   │   ├── lib/              # 2D canvas draw, graphData merge, colors, time
│   │   └── test/             # Vitest pure function tests
│   ├── package.json
│   └── vite.config.ts
├── docs/                     # Queries manual, schema spec, prompt changelog, daily specs
└── README.md
```

---

## Design Decisions & Trade-offs

- **Append-Only Knowledge History**: Replaced facts are marked `still_true=false` and linked via `REPLACES` edges rather than deleted, maintaining complete auditability.
- **Single-Worker FIFO Extraction Queue**: Extraction and conflict checks run asynchronously on a single-worker `ThreadPoolExecutor` to eliminate race conditions while the reply never waits for memory extraction.
- **Deterministic Non-LLM Memory Recall**: Whole-phrase entity detection and 1-hop graph traversals execute in milliseconds without extra LLM latency or cost.
- **FalkorDB as Single Source of Truth**: FalkorDB stores both conversation history (`Event` nodes) and semantic facts (`Fact` nodes), avoiding separate checkpointer stores.
- **Conservative Conflict Default**: Conflict classification defaults to `"add"` when uncertain, ensuring information is never mistakenly destroyed.

---

## Limitations & Future Roadmap

- **Asynchronous Extraction**: Memory appears seconds after the reply because extraction and conflict checks run in the background.
- **Model Decisions**: Model add/replace decisions can be wrong depending on LLM output and reasoning.
- **Free-Tier Quota & Data-Use**: Subject to Gemini free-tier rate limits and provider data-use caveats.
- **Single Process**: Designed for a single process with an in-memory queue; multi-worker scaling requires an external job queue.
- **Command Syntax**: Explicit "replace X with Y" commands are not supported; memory updates must be expressed naturally.
- **Entity Sharing for Replacement**: Facts only replace each other if they share an entity.
- **Single-Agent Instance**: Currently deployed for one agent (`agent_main`). The schema is multi-agent ready via `agent_id` property scoping on every node.
- **Regex Entity Detection**: Uses phrase matching with short-name case-sensitivity rules. Semantic entity linking via embeddings is planned for future releases.
- **Future Enhancements**: Multi-agent shared facts (`SHARED_WITH` edges), procedural memory nodes (`Skill`), and multi-hop graph path queries.

---

## License & Credits

Built for **Graph Hacks** (WeMakeDevs x FalkorDB) — Track 2: Agent Memory and Coordination.
Powered by [FalkorDB](https://www.falkordb.com/), [LangGraph](https://www.langchain.com/langgraph), [FastAPI](https://fastapi.tiangolo.com/), and [Google Gemini](https://ai.google.dev/).

Licensed under the [MIT License](LICENSE).
