# Mnemo — Hackathon Submission Details

This document contains pre-formatted fields ready to copy and paste into the **Graph Hacks** submission form.

---

## Submission Fields

### Project Name
`Mnemo`

### Tagline (80 chars max)
`Graph memory for AI agents that remembers across sessions and keeps history.`

### Track
`Track 2 — Agent Memory and Coordination`

### Built With
`FalkorDB, LangGraph, FastAPI, Google Gemini API, Python, React, TypeScript, Vite, react-force-graph-2d`

---

### Short Description (350 chars max)
> Mnemo is a project assistant with persistent graph memory, powered by FalkorDB and LangGraph. After every message, it extracts durable entities and facts, recalls relevant context across sessions, and preserves changed facts as history (`REPLACES` edges) rather than deleting them. Designed for multi-agent state sharing.

---

### Full Description
> AI assistants forget. Mnemo is a project assistant whose memory lives in a FalkorDB graph database.
>
> **How It Works**:
> 1. **Extraction Pipeline**: After every message, a single-worker background queue extracts durable entities (projects, tools, decisions, people, preferences) and standalone facts into FalkorDB.
> 2. **Deterministic Recall**: Before responding, Mnemo matches entities, pulls direct facts, expands 1-hop across related entities, and incorporates user preferences without an extra LLM call.
> 3. **History as Graph Structure**: When user information changes (e.g., *"Switched Project X from Python to Go"*), Mnemo marks the old fact as inactive (`still_true = false`) and creates a directed `REPLACES` edge from the new fact to the old one. History is preserved rather than destroyed.
> 4. **Live Memory Graph**: A React + Vite frontend polls `/graph` and displays a 2D force-directed graph. Active facts, faded replaced facts, red `REPLACES` arrows, and pulsing gold recalled nodes render live alongside chat.
>
> Mnemo uses FalkorDB as the single source of truth for both chat events and semantic facts.

---

### Challenges & Learnings
1. **Managing Conflict Resolution**: Deciding when a new fact replaces an old one requires careful model prompting; defaulting to `"add"` when uncertain ensures facts are never mistakenly destroyed.
2. **Asynchronous Background Extraction**: Moving extraction to a background queue keeps chat response times under 1 second while using a single FIFO worker eliminates race conditions during conflict checks.
3. **Graph Layout Stability**: Force-directed graph libraries mutate node objects during simulation; preserving node references by ID across polling updates prevents visual layout jumps when new facts arrive.

---

### What's Next
- Multi-agent shared memory (`SHARED_WITH` edges between agent nodes)
- Procedural memory nodes (`Skill`)
- Vector embedding hybrid retrieval for entity lookup

---

### Links & Checklist
- **Repository URL**: `<your-github-repo-url>`
- **Demo Video URL**: `<your-youtube-unlisted-or-video-url>`
- **Live / Preview URL**: `http://localhost:5173`
- **License**: MIT
- **Release Tag**: `v1.0`
