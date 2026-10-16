# Mnemo — Day 4: Polish and Submit

> **Mnemo**: graph memory for AI agents, powered by FalkorDB
> Hackathon: **Graph Hacks** (WeMakeDevs x FalkorDB) · Track: **Track 2 — Agent Memory and Coordination**
> Day 4 date: **Oct 18** · Goal: a rock-solid demo, a README that meets the submission rules, a video, and a **submitted** project with buffer to spare
> Save this file as `docs/day4.md` in the repo.

**Rule of the day: nothing new is built.** Day 4 is bug fixes, documentation, a demo, a video and the submission form. If an idea isn't a fix for something that breaks the demo or the submission requirements, it goes in the "What's next" section of the README, not in the code.

Assumes Days 1–3 are done (`docs/day1.md`–`docs/day3.md`). The repo layout is `backend/`, `frontend/`, `docs/`, root `README.md`. Use the real paths you find in the repo; where this doc shows `backend/src/mnemo/...`, adjust if yours differ.

---

## 1. Verify the official rules first (10 minutes, do this before anything else)

I could read the official rules page (wemakedevs.org/hackathons/falkordb/rules) but **could not confirm the exact submission deadline, time zone, submission method or judging criteria**. The schedule page I found still said "September 2026" and "exact dates being confirmed", which conflicts with the Oct 15–18 dates in our notes. It may be a stale copy. So:

- [ ] Open the hackathon page and the WeMakeDevs / FalkorDB Discord announcements. Write down: **deadline (date, time, time zone)**, **how to submit** (form? platform?), **required fields**, **judging criteria**, **video requirements** (length, platform), **team size** (solo or up to 4 is what the page says).
- [ ] Put the deadline in your calendar with alarms. **Plan to submit at least 3 hours before it.**
- [ ] Re-read the rules page for anything that changed.

### What the rules page says every submission must include (paraphrased)
1. **A README with setup instructions and your graph data model.**
2. **The Cypher queries or graph algorithms the product depends on.**

Other rules that matter:
- FalkorDB must be the **primary graph database** and support a **central** part of the product ("the graph has to do real work").
- The main coding and design work must start **after the hackathon starts**; original work done during the hackathon is what is judged. Keep your git history intact (don't squash or rewrite history) so commits show the work happening during the event.
- Plagiarism or manipulating the judging process leads to disqualification.
- The page also lists kinds of "graph work" (for example multi-hop expansion, running graph algorithms, exploring the graph in FalkorDB Browser). Mnemo's real graph work is described in §8.2; use those points in the README and video.

**Everything in §6 (README) and §7 (queries doc) exists mainly to satisfy items 1 and 2. They are not optional polish.**

---

## 2. Day 4 priorities

**Must (submission fails or looks broken without these)**
1. Demo works reliably, three clean runs in a row (§4)
2. Root `README.md` with setup instructions **and graph data model** (§6)
3. `docs/queries.md` with the Cypher the product depends on (§7)
4. Public repo that a stranger can clone and run (§9)
5. Demo video (§5)
6. Submission form filled and **submitted** with buffer (§10)

**Should**
7. Screenshots and a short GIF for the README
8. Clean-clone setup test
9. Prompt tuning, only for failures you can reproduce

**Nice (only if everything above is done)**
10. LICENSE file, release tag, Q&A prep (§8.3)

### Suggested time blocks (adjust to your deadline; T = deadline)
| Block | What | Length |
|---|---|---|
| A | Reset-and-run bug bash, fixes (§4). **Feature freeze when done** | ~2 h |
| B | `queries.md`, `schema.md` sync, README, screenshots (§6, §7) | ~2 h |
| C | Rehearse twice, record video (§5, §8) | ~1.5 h |
| D | Clean-clone test, repo hygiene, submission text, **submit** (§9, §10) | ~1 h |
| Buffer | Something will go wrong | **≥ 3 h before T** |

---

## 3. Carry-over from Day 3 (do these first)

1. **Replaced-fact count.** The last walkthrough showed `Replaced Facts: 3` where a clean run should show **1**. Confirm whether it was stale data or over-replacement:
   ```bash
   docker compose exec falkordb redis-cli GRAPH.DELETE mnemo
   # restart the API so it recreates indexes and the agent
   ```
   Then run walkthrough steps 1–5 (§8.1). In `GET /graph` the **only** replaced fact should be `Project X uses Python`. If more are replaced, collect the replaced fact labels and the messages that caused them, then tune `prompts/conflict.md` (§4.3).
2. **Visual checks in the browser** (the four Day 3 fixes are visual, so verify with your eyes):
   - [ ] Graph stays still when idle (no drifting)
   - [ ] Gold pulse stops after about 4 s
   - [ ] Clicking a recalled chip opens the drawer for that fact
   - [ ] Replaced fact is faded with strikethrough, red dashed arrow points new → old
3. Run all tests: backend `pytest`, frontend `npm test`, `npm run build`, `npm run lint`.

---

## 4. Bug bash (Block A)

### 4.1 Method
- Always start from a **reset graph** (command above). Use **fake data only**.
- Run the demo script (§8.1) **three times in a row**. Any deviation (wrong replacement, missing node, weird reply, error) becomes a bug with: the message you sent, what happened, what you expected.
- Fix only reproducible bugs. One fix at a time; re-run the whole script after each fix.

### 4.2 Scenario checklist (each should be tried once)
- [ ] **Persistence across sessions**: new session still recalls (the headline)
- [ ] **Persistence across restarts**: restart API and FalkorDB; chat history and `/graph` are still there
- [ ] **Change of mind**: Python → Go; only the Python fact is replaced
- [ ] **Preference change**: "short answers" → "detailed explanations"; exactly one Preference entity, old fact replaced
- [ ] **One-hop recall**: say `Project Y uses Go`, then ask about Project X; the Project Y fact shows up as `related`
- [ ] **Short-name guard**: "let's go ahead" does not pull in Go facts
- [ ] **Small talk**: "thanks", "what's the weather" create no facts
- [ ] **Quick successive messages**: send 3 messages fast; facts appear in order, no duplicate or missing entities
- [ ] **Long message** (about 1,000 characters) and a message at the 4,000-character limit
- [ ] **Rate limit / overload**: a 429 or 503 from Gemini leads to a retry or a friendly inline error, never a crash or blank screen
- [ ] **API down**: stop the API; the badge shows `Disconnected`, graph stays visible, recovers on restart
- [ ] **Reload mid-session**: chat and graph restore
- [ ] **Empty states**: fresh browser, empty graph

### 4.3 Prompt tuning rules (only if a reproducible failure demands it)
- Change **one prompt at a time** (`extract.md` or `conflict.md`), and only the part that addresses the failure.
- Re-run the Day 1 scenario **and** the demo script after each change.
- Log every change (what failed, what changed, result) in `docs/PROMPT_CHANGELOG.md`.
- Safe default when unsure remains `add` (a wrong replace destroys information; a wrong add is a harmless extra fact).
- If a fix doesn't work after two attempts, **stop**: adjust the demo script to avoid the weak case instead, and list it under "Limitations" in the README.

### 4.4 Feature freeze
When the bug bash is done, **commit and tag** (`git tag v1.0-rc`). From here on only docs, assets and the submission. If you must touch code, re-run the demo script and tests afterwards.

---

## 5. Demo video (Block C)

The video is likely the first thing a judge sees. Spend real effort here.

- **Length:** 2–3 minutes unless the submission page says otherwise (check §1).
- **Format:** screen recording with voice-over, 1080p, 30 fps. Free tools are fine (OBS Studio, or your OS's built-in recorder). Record audio in a quiet room; a phone headset mic is better than a laptop mic.
- **Screen setup:** browser at 100% zoom, window about 1440×900, hide bookmarks and other tabs, **no `.env`, API keys or terminals with secrets on screen**, notifications off, dark mode (matches the app). Put the app on the left half-to-full screen; keep a second tab ready with FalkorDB Browser (`http://localhost:3000`).
- **Before every take:** reset the graph, restart the API, clear `localStorage` (or use a private window), confirm `CHAT_MODEL`/`EXTRACTION_MODEL` work with a throwaway message (then reset again).
- **Structure:** hook (15 s) → demo (about 90 s) → "how it works" with the architecture diagram (20 s) → close (10 s). Script in §8.1.
- **Recording tips:** do 2–3 takes; keep the best. Don't talk over the moments where the graph changes; pause one beat so viewers can see the fade and the red arrow. Pre-type nothing: use the suggestion chips and paste prepared messages so there are no typos.
- **Export and upload:** upload to whatever the submission form accepts (check §1; YouTube unlisted or a direct upload are common). Test the link in a **private/incognito window**.
- **Backup:** keep the video file locally too.

### Screenshots and GIF for the README
Save in `docs/assets/`:
1. `graph-after-demo.png`: the full app after the walkthrough
2. `replaced-fact.png`: the faded Python fact with the red arrow, drawer open showing the source message
3. `falkordb-browser.png`: the same graph in FalkorDB Browser (shows the graph is real, in FalkorDB)
4. `demo.gif` (optional, under about 10 MB, 10–15 s): the moment of the change of mind. From a recorded clip:
   ```bash
   ffmpeg -i clip.mp4 -vf "fps=12,scale=900:-1" -loop 0 docs/assets/demo.gif
   ```

---

## 6. Root `README.md` (Block B) — required content

The rules require a README with **setup instructions** and the **graph data model**. Use this exact outline. Write for a judge who has 5 minutes and has never seen the project.

```
# Mnemo
<tagline> + hero GIF (docs/assets/demo.gif) + 3 badges max (optional)

## What it is            (3–4 sentences)
## Why a graph           (the graph does real work: 4 bullets, see §8.2)
## Demo                  (video link + 2 screenshots)
## How it works          (architecture diagram + the memory loop in 5 steps)
## Graph data model      (REQUIRED)
## Cypher queries        (REQUIRED: summary table + link to docs/queries.md)
## Setup                 (REQUIRED)
## Configuration         (env var table)
## Project structure
## Design decisions and trade-offs
## Limitations and what's next
## Built for Graph Hacks (track, credits)
```

### 6.1 Section content

**What it is.** A project assistant with persistent graph memory, built on FalkorDB and LangGraph. After every message it extracts projects, tools, decisions and preferences; before every reply it recalls what's relevant; when facts change it keeps the old ones as history instead of deleting them. A live graph view shows the memory growing.

**Why a graph** (use these, they are true of the implementation):
- **Provenance:** every fact links back (`CAME_FROM`) to the exact message it was learned from.
- **History as structure:** a changed fact creates a `REPLACES` edge; the old fact stays queryable as history.
- **Related recall:** recall expands one hop across entities that share current facts, so asking about one project can surface a connected tool or project.
- **Typed entities:** preferences are entities of type `Preference`, so they are always retrievable regardless of the topic.

**How it works.** Include the final architecture diagram (take it from `docs/day2.md` §3, with the frontend now built) and this loop:
1. User message is stored as an `Event`.
2. **Recall** (no LLM call): detect known entities in the message, pull their current facts, expand one hop, always include preferences, cap at 15.
3. **Respond:** the chat model answers with recalled facts as context (LangGraph `recall → respond`).
4. The reply is returned immediately.
5. **Extract** in the background (single FIFO worker): entities and facts are extracted, conflicts checked (`add` / `replace` / `skip`), and written to FalkorDB. The frontend polls `/graph`.

**Graph data model (REQUIRED).** Copy from `docs/schema.md` and make sure it matches the code (see §7.3): node labels with properties, relationship types with direction and meaning, indexes, and the example subgraph for "Project X uses Python → Go". Include a small diagram:
```
(Agent)-[:OWNS]->(Session)-[:CONTAINS {seq}]->(Event)-[:MENTIONS]->(Entity)
(Agent)-[:OWNS]->(Fact)-[:ABOUT]->(Entity)
(Fact)-[:CAME_FROM]->(Event)
(new:Fact)-[:REPLACES]->(old:Fact)
```

**Cypher queries (REQUIRED).** A table with the 6–8 queries the product depends on most (name, what it does, file), then "Full list with exact Cypher: `docs/queries.md`". Include 2–3 queries inline that show the graph doing real work (one-hop neighbors, supersession chain, provenance); copy them from §7.2.

**Setup (REQUIRED).** Must be exact, tested on a clean clone (§9.3):
- Prerequisites: Docker, Python 3.11+, Node.js 20+, a Gemini API key (free from Google AI Studio).
- Steps: clone → copy `.env.example` files (backend and `frontend/`) → fill `GEMINI_API_KEY` → `docker compose up -d` → backend install (`pip install -r requirements.txt`) → run the API (`uvicorn mnemo.api.main:app --port 8000`) → frontend (`cd frontend && npm install && npm run dev`) → open `http://localhost:5173`.
- Ports table: FalkorDB 6380 (host) / 3000 (FalkorDB Browser), API 8000, frontend 5173.
- "Verify it works": one-line check (`curl localhost:8000/health`) and a first message to try.
- Run tests: backend `pytest`, frontend `npm test`.
- Reset memory: the `GRAPH.DELETE mnemo` command, then restart the API.
- Model names: note that free-tier Gemini model names change; say where to change them (`.env`).

**Configuration.** Table of every env var (backend and frontend) with default and meaning.

**Design decisions and trade-offs.** Short bullets: append-only history instead of deletes; extraction after the reply on a single FIFO worker (ordering and no racing conflict checks); recall without an LLM call (fast, predictable); hand-written Cypher memory layer (no auto graph builders) so the schema and replacement logic are explicit; graph DB as the single source of truth for chat history and memory (no separate checkpointer); conflict check defaults to `add` when unsure.

**Limitations and what's next** (be honest, judges respect it):
- One agent today. The schema is multi-agent ready: `agent_id` on every node and an explicit `Agent` node; shared memory would be a `Fact` linked to several agents.
- Recall is one hop and name-based; the short-name guard reduces but doesn't remove false matches.
- Extraction and conflict detection are LLM judgment and can be wrong; the default is the safe `add`.
- Extraction runs after the reply, so a fact appears a few seconds later.
- Single-process app (worker queue and event lock assume one process).
- Free-tier Gemini: rate limits apply and inputs may be used by Google to improve models, so use demo data only.
- Next: multi-agent shared memory, procedural-memory `Skill` nodes, multi-hop recall.

**Built for Graph Hacks.** Track 2 (Agent Memory and Coordination). Credit FalkorDB and WeMakeDevs; mention Gemini API, LangGraph, FastAPI, React. State the build dates (confirm them in §1). Add a LICENSE (MIT unless you prefer another) and name it here.

### 6.2 README quality checklist
- [ ] Every image and link works when viewed on GitHub (relative paths to `docs/assets/`)
- [ ] No secrets, no personal paths, no TODOs
- [ ] The setup section was followed on a clean clone, line by line (§9.3)
- [ ] The first screen (above the fold) shows the GIF or screenshot and the one-line pitch
- [ ] No claim in the README is untrue (for example, don't say "multi-agent" for what is single-agent; say "multi-agent ready")

---

## 7. `docs/queries.md` and `docs/schema.md` (Block B)

### 7.1 `docs/queries.md` — the Cypher the product depends on

Build this **from the actual code**. Open `memory/schema.py`, `memory/write.py`, `memory/read.py` and **copy each Cypher string verbatim** (do not retype or "clean up", so the doc stays truthful). For each query give:

| Field | Content |
|---|---|
| Name | e.g. `neighbors-one-hop` |
| Purpose | One sentence, plain language |
| Where used | file and function |
| Cypher | verbatim, with parameters shown (`$agent_id`, …) |

Group them:
- **Schema:** index creation
- **Writes:** ensure agent, create session, add event (with `seq`), upsert entity (`MERGE`), link event mentions, add fact (with `ABOUT`, `CAME_FROM`, `OWNS`), replace facts (`REPLACES` edge and `still_true=false`)
- **Reads:** current facts for entities, recent events, session messages, all entities, preference facts, recent current facts, **neighbor entities (one-hop)**, graph snapshot (the four queries behind `/graph`), memory dump

Mark the ones that show the graph doing real work with a short "Why it needs a graph" note: neighbor expansion (traversal across shared facts), provenance (`CAME_FROM`), supersession (`REPLACES`), preferences by entity type.

### 7.2 Ad-hoc queries to include (also useful to run live in FalkorDB Browser)

```cypher
// 1. Current facts about an entity
MATCH (f:Fact {still_true:true})-[:ABOUT]->(e:Entity {name_key:'project x'})
RETURN f.text AS fact, f.created_at AS learned_at
ORDER BY learned_at DESC

// 2. Everything that was replaced, and by what
MATCH (new:Fact)-[:REPLACES]->(old:Fact)
RETURN old.text AS was, new.text AS now, old.replaced_at AS replaced_at
ORDER BY replaced_at DESC

// 3. Provenance: which message did each fact come from?
MATCH (f:Fact)-[:CAME_FROM]->(ev:Event)
RETURN f.text AS fact, ev.text AS source_message, f.still_true AS current

// 4. Related entities via shared current facts (one hop)
MATCH (m:Entity {name_key:'project x'})<-[:ABOUT]-(f:Fact {still_true:true})-[:ABOUT]->(n:Entity)
WHERE n.id <> m.id
RETURN DISTINCT n.name AS related, n.type AS type

// 5. Full history chains (variable-length path, good for the Browser graph view)
MATCH p = (a:Fact)-[:REPLACES*1..5]->(b:Fact)
RETURN p

// 6. Visualize the memory graph in FalkorDB Browser
MATCH p = (f:Fact)-[:ABOUT]->(e:Entity)
RETURN p LIMIT 50
```

These omit the `agent_id` filter because there is one agent. Run each against the demo data once and confirm it returns sensible rows before putting it in the docs. If one errors in your FalkorDB version, fix the query, don't ship it broken.

### 7.3 `docs/schema.md` — sync with the code
Compare against the real code and update where it drifted: `Event.role` can now be `assistant` as well as `user`; the final index list; property names; the example subgraph. The README's data model section must match this file.

---

## 8. Final demo script, talking points and Q&A

### 8.1 Script (about 2 minutes). Fake data only.

**Reset first** (clean graph, restart API, clear browser storage). Suggested narration in quotes.

| Time | Action | Say |
|---|---|---|
| 0:00 | App open, empty graph | "AI assistants forget. Mnemo gives an agent a memory that lives in a graph, so it remembers across sessions and knows how its knowledge changed." |
| 0:15 | Send `I'm building Project X, a task manager, in Python.` Nodes grow in; badge shows "Updating memory…" | "After every message, a background step extracts entities and facts into FalkorDB. The reply doesn't wait for it." |
| 0:30 | Send `I prefer short, direct answers.` Violet Preference node appears | "Preferences are entities too, so they're always recalled." |
| 0:45 | Click **New session**. Chat clears, graph stays | "New session, same memory." |
| 0:50 | Send `What do you know about Project X?` Reply is short; recalled facts pulse gold; expand the "Recalled" chip | "Recall walks the graph: it finds Project X, pulls its current facts, and the gold ring shows exactly what the agent used. The short answer comes from the stored preference." |
| 1:10 | Send `Actually I switched Project X to Go.` Python fact fades with strikethrough, red arrow to the new fact | "When I change my mind, the old fact isn't deleted. It's replaced, with a REPLACES edge, so history stays in the graph." |
| 1:25 | Click the faded Python fact; drawer shows source message and "Replaced by" | "Every fact links back to the message it came from." |
| 1:35 | Send `What language is Project X written in?` Reply says Go | "And the agent now answers with the updated fact." |
| 1:45 | Switch to FalkorDB Browser, run query 2 from §7.2 | "This is the same memory in FalkorDB: what was replaced, and by what, as a graph query." |
| 1:55 | Back to the app | "One agent today; the schema is ready for agents to share this memory." |

Optional extra (only if time allows, 15 s): `I prefer detailed explanations.` shows the preference replaced and longer answers afterwards.

### 8.2 Talking points: "the graph does real work"
- Provenance, history and related recall are all **graph traversals**, not text search.
- FalkorDB holds the **only** copy of memory and chat history, and the UI reads straight from it.
- The schema is explicit and small: 5 node labels, 7 relationship types, each with a purpose.

### 8.3 Likely questions (one-line answers)
- **Why a graph and not a vector DB?** Memory here is about relationships and change over time: what a fact is about, where it came from, what replaced it. Those are edges, and following them is the query.
- **How does it decide a fact is outdated?** A model compares each new fact with current facts about the same entities and answers add, replace or skip; it defaults to add when unsure, so it never destroys information by guessing.
- **What if extraction is wrong?** The source message is linked to every fact, so errors are visible and traceable; the wrong-replace risk is reduced by the add default.
- **Does it scale?** Honest answer: built for a hackathon demo, single process, one agent. Recall does one name-match query plus a few traversals, with no LLM call; the next step would be indexing entity lookup and moving the worker to a queue service.
- **How would multiple agents share memory?** Every node already carries `agent_id` and there's an explicit `Agent` node; sharing would be a fact linked to several agents.

---

## 9. Repo hygiene and clean-clone test (Block D)

### 9.1 Hygiene
- [ ] **No secrets in the repo or history.** Check: `git grep -nI "AIza"` (Gemini keys start this way), `git ls-files | grep -E "(^|/)\.env$"` (must print nothing), and skim `git log -p` for keys if you ever committed one. **If a key was ever committed, rotate it in Google AI Studio.**
- [ ] `.env.example` files exist for backend and `frontend/`, with every variable documented, **no real values**
- [ ] `.gitignore` covers `.env`, `.venv/`, `node_modules/`, `dist/`, `__pycache__/`, `.pytest_cache/`, `*.egg-info/`, `logs/`
- [ ] Dead files removed (template leftovers, scratch scripts, unused assets); `docs/` contains `day1.md`–`day4.md` (build log), `schema.md`, `queries.md`, `api.md`, `PROMPT_CHANGELOG.md`, `assets/`
- [ ] LICENSE added (suggest MIT, unless you want something else)
- [ ] Commit history intact and shows work during the event; **don't squash or rewrite**
- [ ] Repo description and topics set (use the text from earlier: description up to 350 characters; topics `falkordb`, `agent-memory`, `ai-agents`, `langgraph`, `knowledge-graph`, `graph-database`, `gemini`, `hackathon`)
- [ ] Tag the final commit: `git tag v1.0 && git push --tags`
- [ ] **Repo is public**, checked in a private/incognito window while logged out

### 9.2 Final test run
- [ ] Backend `pytest` passes
- [ ] Frontend `npm test`, `npm run build`, `npm run lint` pass (warnings OK, errors not)

### 9.3 Clean-clone test (do this for real; it catches missing files and wrong setup steps)
```bash
git clone <your-public-repo-url> /tmp/mnemo-clean
cd /tmp/mnemo-clean
# follow the README Setup section EXACTLY, with no extra steps from memory
```
- [ ] Setup works as written, in a reasonable time (note how long it takes)
- [ ] The first message works end to end
- [ ] The demo script runs on the clean clone
- [ ] Any step that needed an unwritten command is now fixed **in the README**

---

## 10. Submission (Block D)

### 10.1 Submit-day checklist
- [ ] §1 verified: deadline, method, fields, video rules
- [ ] §3 carry-over resolved
- [ ] Bug bash done, feature freeze committed, `v1.0` tagged
- [ ] README (setup + graph data model) and `docs/queries.md` done
- [ ] Video uploaded; link tested in a private window; backup file saved locally
- [ ] Repo public; description and topics set
- [ ] Clean-clone test passed
- [ ] Submission text prepared (§10.2)
- [ ] **Submitted at least 3 hours before the deadline**
- [ ] Screenshot or email of the confirmation saved; open the submitted page once to check that links and video work

### 10.2 Submission text (drafts to paste and adjust)

**Project name:** Mnemo

**Tagline (about 80 characters):** Graph memory for AI agents that remembers across sessions and keeps history.

**Short description (up to 350 characters):**
> Mnemo: a project assistant with persistent graph memory, built on FalkorDB and LangGraph. After every message it extracts projects, tools, decisions and preferences, recalls them across sessions, and keeps replaced facts as history instead of deleting them. Designed so more agents can share the same memory later.

**Full description (about 170 words):**
> AI assistants forget. Mnemo is a project assistant whose memory lives in a FalkorDB graph. After every message, a background step extracts entities (projects, tools, people, decisions, preferences) and facts into the graph. Before every reply, recall finds the entities you mention, pulls their current facts, expands one hop to related entities and always includes your preferences, so the agent answers with context, even in a brand-new session.
>
> When you change your mind, Mnemo doesn't delete the old fact. A new fact `REPLACES` the old one, which stays in the graph as history, and every fact links back to the message it came from. A live graph view shows memory growing, facts fading when replaced, and which facts the agent used for each answer.
>
> It's single-agent today, with a schema built for sharing memory across agents: `agent_id` on every node and an explicit agent node. Built with FalkorDB, LangGraph, FastAPI, Gemini and React.

**Built with:** FalkorDB, LangGraph, FastAPI, Gemini API, Python, React, TypeScript, Vite, react-force-graph.

**Track:** Track 2 — Agent Memory and Coordination.

**Challenges and learnings (pick 3):**
- Deciding when a new fact replaces an old one is a judgment call for the model; defaulting to "add when unsure" keeps it safe.
- Extraction after every message must never slow the reply, so it runs on a single FIFO worker, which also keeps conflict checks from racing each other.
- The graph visualization library mutates the data it's given, so the UI merges snapshots by node id to keep the layout stable while polling.
- Free-tier model limits shaped the design: fewer LLM calls on the reply path, retry with backoff on rate limits.

**What's next:** multi-agent shared memory, procedural-memory skill nodes, multi-hop recall.

**Links and assets:** repo URL, video URL, screenshots from `docs/assets/`, team member names.

---

## 11. Risks and rules of thumb (read before the day starts)

- **Don't build new things.** Every new feature risks the demo. Write it under "What's next".
- **The video is the safety net.** A live demo can fail (rate limits, network). Record a clean take early.
- **Gemini free tier.** Don't hammer it with rehearsals right before recording. If you hit rate limits, set `CHAT_MODEL` to the same model as `EXTRACTION_MODEL`, wait a minute, and retry. Model names change; confirm the names in `.env` still work before you record.
- **Fake data only**, in the video, screenshots and README.
- **Never leave submission to the last minute.** Forms break, uploads stall, links need testing.
- **Keep claims true.** Say "multi-agent ready", not "multi-agent". Judges check.
- **If something is broken and unfixable in the time left**, remove it from the demo, list it under Limitations, and move on.

---

## 12. Instructions for the coding agent

What the **coding agent** should do today (the video, recording, upload and submission form are done by you manually):

1. **Do not add features.** Fix only bugs reproduced in the bug bash (§4), one at a time, and re-run tests after each.
2. Create `docs/queries.md` (§7.1) by copying the Cypher **verbatim** from `schema.py`, `write.py` and `read.py`, plus the ad-hoc queries in §7.2. Run every ad-hoc query against a graph with demo data and report which returned rows.
3. Sync `docs/schema.md` with the real code (§7.3).
4. Write the root `README.md` following the outline and content in §6. Use real file paths, real env var names and real ports from the repo. Leave clearly marked placeholders only for the video link and screenshots (`<!-- TODO: video link -->`), and list them in your final report.
5. Run the hygiene checks in §9.1 and report results (especially the secret scan and `.env` tracking).
6. Add a `LICENSE` (MIT) unless told otherwise.
7. Follow the §9.3 clean-clone setup on a fresh copy of the repo and report every place the README was wrong or incomplete, then fix the README.
8. Create individual files (no zip archives).
9. Final report: bugs fixed (with the message that reproduced each), prompt changes logged, test results (backend and frontend), query results, hygiene results, clean-clone result, and anything in §10.1 that you could not do.