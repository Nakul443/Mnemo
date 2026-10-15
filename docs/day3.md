# Mnemo — Day 3: Frontend

> **Mnemo**: graph memory for AI agents, powered by FalkorDB
> Hackathon: **Graph Hacks** (WeMakeDevs x FalkorDB), Oct 15–18, 2026
> Track: **Track 2 — Agent Memory and Coordination**
> Day 3 date: **Oct 17** · Goal: the full demo story works in the browser: chat on the left, a **live memory graph** on the right
> Save this file as `docs/day3.md` in the repo.

This file is the full spec for Day 3. It assumes Days 1–2 are built and the API runs (`docs/day2.md`, `docs/api.md`). **No backend changes are needed today** except one `.env` line (§4.4). The frontend only talks to the existing endpoints.

---

## 1. Day 3 in one paragraph

Judges should be able to *watch the memory change*. The page has two panes. Left: a chat with the agent. Right: the memory graph, polled live from `GET /graph`. Entities are big colored circles, facts are small pills attached to them. When the user changes their mind, the old fact fades and gets a strikethrough, and a red arrow points from the new fact to the old one. After each reply, the facts the agent actually used **pulse in gold**. Clicking any fact shows the message it came from. A "New session" button makes the key demo moment possible: start a fresh chat and the agent still remembers.

**Done when:** the full demo walkthrough in §12 works in the browser, start to finish.

---

## 2. Decisions for Day 3 (do not re-debate)

| Topic | Decision |
|---|---|
| Framework | **React + Vite + TypeScript** in `frontend/` at the repo root |
| Dev server | Port **5173** (3000 is FalkorDB's browser, 8000 is the API, 6380 is FalkorDB) |
| Graph library | **`react-force-graph-2d`** (canvas, fully custom node drawing, force layout built in) |
| Styling | **Plain CSS** in one `styles.css` with CSS variables. No Tailwind, no component library |
| State | React hooks only. No Redux/Zustand/React Query |
| Data | Poll `GET /graph` (adaptive interval, §8). No WebSockets/SSE |
| Design source | No Figma. The look is fully specified in this file (§6, §7) |
| Theme | Dark only. No light mode |
| Scope | One agent, one page. No routing, no auth, no settings screen |

---

## 3. What the frontend consumes (backend contract)

The API from Day 2 (full detail in `docs/api.md`). Base URL from `VITE_API_BASE_URL` (default `http://localhost:8000`).

| Method + path | Used for |
|---|---|
| `POST /sessions` → `{session_id}` | New session |
| `GET /sessions/{id}/messages` → `{session_id, messages:[{role,text,seq,ts}]}` | Restore chat after reload. `404` if unknown |
| `POST /chat` `{session_id, message}` → chat response | Send a message |
| `GET /graph` → graph snapshot | Poll the memory graph |
| `GET /health` | Optional: initial connectivity check |

### 3.1 TypeScript types (`src/api/types.ts`), exactly

```ts
export type Role = "user" | "assistant";

export interface ChatMessage {
  role: Role;
  text: string;
  seq: number;
  ts: number;               // epoch ms
}

export interface RecalledFact {
  id: string;
  text: string;
  source: "preference" | "direct" | "related" | "recent";
}

export interface ChatResponse {
  reply: string;
  session_id: string;
  event_id: string;
  recalled_fact_ids: string[];
  matched_entity_ids: string[];
  recalled: RecalledFact[];
  extraction_pending: number;
}

export type EntityType = "Project" | "Tool" | "Person" | "Decision" | "Preference";

export interface EntityNode {
  id: string;
  kind: "entity";
  label: string;
  entity_type: EntityType;
  created_at: number;
}

export interface FactNode {
  id: string;
  kind: "fact";
  label: string;
  status: "current" | "replaced";
  created_at: number;
  replaced_at: number | null;
  source_message: string | null;
}

export type ApiNode = EntityNode | FactNode;

export interface ApiEdge {
  source: string;           // fact id
  target: string;           // entity id (ABOUT) or old fact id (REPLACES)
  type: "ABOUT" | "REPLACES";
}

export interface GraphSnapshot {
  nodes: ApiNode[];
  edges: ApiEdge[];
  stats: { entities: number; current_facts: number; replaced_facts: number };
  updated_at: number;
  extraction_pending: number;
}
```

Edge semantics: `ABOUT`: fact → entity. `REPLACES`: **new fact → old fact**.

---

## 4. Setup: packages and commands

### 4.1 Prerequisites
Node.js 20+ and npm. The backend (FalkorDB + API on port 8000) must be running.

### 4.2 Scaffold and install (exactly these)

From the repo root:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-force-graph-2d
npm install -D vitest
```

That is the **complete** package list:

| Package | Type | Why |
|---|---|---|
| `react`, `react-dom` | dep (from template) | UI |
| `react-force-graph-2d` | dep | Force-directed graph on canvas |
| `typescript`, `vite`, `@vitejs/plugin-react`, ESLint packages | dev (from template) | Build, dev server, lint |
| `vitest` | dev | Unit tests for pure functions |

**Do not install** any UI kit, CSS framework, icon library, state library, router, HTTP client (use `fetch`), or D3 packages. If the install prints a peer-dependency error for `react-force-graph-2d` against the template's React version, re-run with `npm install react-force-graph-2d --legacy-peer-deps` (and note it in the final report). If the scaffolder asks about experimental options, answer **No**.

Commit `package-lock.json` so versions are pinned.

### 4.3 `package.json` scripts
`dev` (vite), `build` (`tsc -b && vite build`), `lint`, `preview`, and add `"test": "vitest run"`.

### 4.4 Config files

**`vite.config.ts`**: React plugin, `server: { port: 5173, strictPort: true, host: "localhost" }`. `strictPort` makes it fail loudly instead of silently picking a different port the API's CORS would reject.

**`frontend/.env.example`**
```
VITE_API_BASE_URL=http://localhost:8000
```
Copy to `frontend/.env`. Read it as `import.meta.env.VITE_API_BASE_URL` with the same value as the fallback.

**Backend (one line, repo-root `.env`)**: allow both spellings of localhost:
```
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```
Restart the API after changing it.

### 4.5 Run
```bash
# terminal 1: docker compose up -d && uvicorn mnemo.api.main:app --port 8000
# terminal 2:
cd frontend && npm run dev        # http://localhost:5173
```

---

## 5. File layout

```
frontend/
├── index.html                       title "Mnemo", dark color-scheme meta
├── package.json  vite.config.ts  tsconfig*.json  .env.example
└── src/
    ├── main.tsx
    ├── App.tsx                      layout + wiring of hooks
    ├── styles.css                   all CSS (variables at top)
    ├── api/
    │   ├── types.ts                 §3.1
    │   └── client.ts                fetch wrappers + ApiError
    ├── hooks/
    │   ├── useSession.ts            session id, restore, new session
    │   ├── useChat.ts               messages, send, recalled chips, errors
    │   └── useGraphPolling.ts       adaptive polling, status
    ├── lib/
    │   ├── colors.ts                palette constants (§6.2)
    │   ├── graphData.ts             snapshot → force-graph data, identity-preserving merge, history filter
    │   ├── draw.ts                  canvas drawing for entity nodes and fact pills
    │   └── time.ts                  relativeTime()
    ├── components/
    │   ├── Header.tsx
    │   ├── StatusBadge.tsx
    │   ├── ChatPanel.tsx            message list + empty state
    │   ├── MessageBubble.tsx
    │   ├── RecalledChips.tsx
    │   ├── Composer.tsx
    │   ├── GraphPanel.tsx           ForceGraph2D + overlays (legend, toggle, stats, empty state)
    │   ├── Legend.tsx
    │   └── NodeDetail.tsx           slide-in drawer
    └── test/
        ├── graphData.test.ts
        └── time.test.ts
```

---

## 6. Exactly how it should look

### 6.1 Layout (desktop, ≥ 900 px wide)

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ ◆ Mnemo  Graph memory for AI agents · powered by FalkorDB     ● Memory idle  [New session] 9d4d6f6c │  56 px
├────────────────────────────┬───────────────────────────────────────────────────────┤
│  CHAT                      │  MEMORY GRAPH                       ☑ Show history [Fit]│
│                            │  ● Project ● Tool ● Person ● Decision ● Preference     │
│        ┌──────────────────┐│                                                       │
│        │ I'm building ... ││            (Tool)                                     │
│        └──────────────────┘│               \                                       │
│ ┌────────────────────────┐ │   [Project X uses Go]──(Project X)──[is a task mgr]   │
│ │ Got it! ...            │ │        ▲ red arrow                                    │
│ └────────────────────────┘ │   [~~Project X uses Python~~]  (faded)                │
│  ▸ Recalled 2 facts        │                                         ┌───────────┐ │
│                            │                                         │ detail    │ │
│                            │                                         │ drawer    │ │
│ ┌────────────────────┐ [↑] │  3 entities · 2 current · 1 replaced    └───────────┘ │
│ │ Tell Mnemo about.. │     │                                                       │
│ └────────────────────┘     │                                                       │
└────────────────────────────┴───────────────────────────────────────────────────────┘
   chat column: 40% width, min 360 px, max 520 px          graph column: the rest
```

- Page is `100vh`, no page scroll. Header fixed height 56 px. Below it, a CSS grid with two columns: chat `clamp(360px, 40%, 520px)`, graph `1fr`. Each column scrolls/behaves independently.
- **Narrow screens (< 900 px):** stack vertically: graph on top (`45vh`), chat below. Nothing else changes. (Demo is on a laptop; don't spend time beyond this.)

### 6.2 Theme and palette (put these in `:root` CSS variables **and** `lib/colors.ts`)

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#0B1020` | App background, graph canvas |
| `--panel` | `#111833` | Chat panel, drawers, header |
| `--panel-2` | `#182044` | Assistant bubbles, fact pill fill, inputs |
| `--border` | `#1F2A4D` | All borders |
| `--text` | `#E6EAF5` | Primary text |
| `--muted` | `#8B96B8` | Secondary text, replaced facts |
| `--accent` | `#7C9CFF` | Buttons, user bubbles, focus rings |
| `--danger` | `#F87171` | REPLACES arrows, error banners |
| `--ok` | `#34D399` | "new node" flash, idle dot |
| `--gold` | `#FFD166` | Recalled-fact pulse |

**Entity type colors:**

| Type | Hex |
|---|---|
| Project | `#7C9CFF` |
| Tool | `#34D399` |
| Person | `#F59E0B` |
| Decision | `#F472B6` |
| Preference | `#A78BFA` |

Font: `Inter, system-ui, -apple-system, Segoe UI, sans-serif` (system fallback only; **do not** load web fonts). Base size 14 px. Border radius: 12 px for panels/bubbles, 8 px for buttons/inputs. Subtle `1px solid var(--border)` borders; no heavy shadows.

### 6.3 Header
- Left: `◆` glyph in `--accent`, **Mnemo** (600 weight, 18 px), then muted tagline `Graph memory for AI agents · powered by FalkorDB` (hide the tagline below 1100 px).
- Right, in order: `StatusBadge`, **New session** button, short session id (first 8 chars, muted, monospace, title attribute = full id).
- **StatusBadge** (pill):
  - idle: green dot + `Memory idle`
  - `extraction_pending > 0`: spinning ring + `Updating memory…` in `--accent`
  - API unreachable: red dot + `Disconnected`

### 6.4 Chat panel
- **Message list** (scrolls, auto-scrolls to bottom on new message): user bubbles right-aligned, `--accent` background, dark text `#0B1020`; assistant bubbles left-aligned, `--panel-2` background, `--text`. Max bubble width 85%. Text wraps, preserves newlines (`white-space: pre-wrap`). Container has `aria-live="polite"`.
- **Typing indicator** while waiting for a reply: an assistant-side bubble with three pulsing dots and the muted caption `Mnemo is thinking…`.
- **RecalledChips** under each assistant bubble that has recalled facts: a collapsed muted line `▸ Recalled 2 facts` (click toggles `▾`). Expanded: a list, one row per fact: a small colored tag for `source` (`preference`, `direct`, `related`, `recent`, in `--muted` outlined pills) + the fact text. Hovering a row **highlights that fact in the graph** (persistent gold ring while hovered); clicking selects it (opens the drawer).
- **Empty state** (no messages): centered muted text `Tell Mnemo about your projects. It remembers across sessions.` and three clickable suggestion chips that **fill the composer** (not auto-send):
  1. `I'm building Project X, a task manager, in Python.`
  2. `I prefer short, direct answers.`
  3. `What do you know about Project X?`
- **Composer**: auto-growing `<textarea>` (1–5 rows), placeholder `Tell Mnemo about your project…`, **Enter sends, Shift+Enter inserts a newline**, round Send button (`↑`) in `--accent`. Disabled (and button shows a spinner) while a reply is pending. Empty/whitespace-only messages cannot be sent. Max 4,000 characters (matches the API); show a muted counter only when over 3,500.
- **Error handling in chat:** see §9.

### 6.5 Graph panel

Canvas fills the whole column, background `--bg`. Overlays (absolutely positioned, `--panel` at 85% opacity, 1 px border, 8 px radius, blurred backdrop):
- **Top-left:** `Legend`: five dots with type names, plus two small sample shapes: a solid pill `current fact` and a dashed faded pill `replaced fact`, and a red arrow sample `replaces`.
- **Top-right:** checkbox **Show history** (default **on**) and a **Fit** button.
- **Bottom-left:** stats line `3 entities · 2 current · 1 replaced` (from `stats`), muted.
- **Empty state** (no nodes): centered muted text `Memory is empty. Say something to Mnemo.`

**Node drawing** (custom canvas via `nodeCanvasObject`, mode `'replace'`; implemented in `lib/draw.ts`). All sizes below are **screen pixels**, so divide by `globalScale` where the library draws in graph units.

*Entity node*
- Circle, radius **11** for `Project`, **8** for every other type. Fill = type color. 1.5 px stroke `--bg`.
- Label below the circle, 12 px, `--text`, drawn with a 3 px `--bg` stroke first (`strokeText`, then `fillText`) so it stays legible over edges. Centered, offset `radius + 12`.

*Fact node* (a "pill")
- Rounded rectangle, height **18**, horizontal padding **8**, corner radius **9**, text 10.5 px. Text = fact label truncated to **32 characters** with `…`. Width = measured text + padding.
- **Current:** fill `--panel-2`, 1 px stroke `#5B6DAA`, text `--text`.
- **Replaced:** fill `#12182F` at 50% alpha, **dashed** 1 px stroke `#5B6DAA` at 50% alpha, text `--muted` with a **strikethrough** (draw a 1 px line through the text's vertical middle; canvas has no strikethrough style).
- When `globalScale < 0.7`, draw facts as a small dot (radius 3) instead of a pill to avoid clutter when zoomed far out.
- Full text is available in the hover tooltip (`nodeLabel`).

*Edges*
- **ABOUT:** 1 px, `#3A4770`, no arrow.
- **REPLACES:** 1.5 px, `--danger`, **dashed** (`linkLineDash` `[4, 3]`), **arrow at the target end** (`linkDirectionalArrowLength` 6, `linkDirectionalArrowRelPos` 1, `linkDirectionalArrowColor` `--danger`). The arrow points **new fact → old fact**. If the installed library version lacks `linkLineDash`, draw REPLACES links with `linkCanvasObject` instead.

*Interaction states* (all drawn in the same canvas function)
- **Hover:** pointer cursor; native tooltip with the full label.
- **Selected:** 2 px white (`#FFFFFF`) outline around the node/pill.
- **Recalled pulse:** a `--gold` ring expanding from the node edge outward (extra radius 4 → 14 px, alpha 1 → 0), repeating every **1200 ms**, for **4000 ms** after a reply. Applies to every node whose id is in `recalled_fact_ids` or `matched_entity_ids`.
- **Hover-highlight from chat chip:** same gold ring, **static** (no animation), while the chip is hovered.
- **New node entrance:** scale from 0 to 1 over **400 ms** (ease-out) plus a `--ok` glow that fades over **1500 ms**. Track `bornAt` per node id on the client the first time the id is seen. Do **not** animate nodes that were present on the first load (set their `bornAt` to 0).
- **Fact becomes replaced** (status flips from `current` to `replaced` between polls): animate opacity from 1 to 0.45 over **700 ms**. Track `replacedSeenAt` per id.

*Layout / physics*
- Pass `cooldownTicks={120}`, `d3AlphaDecay={0.03}`, `d3VelocityDecay={0.35}`.
- Via the graph ref: charge strength **−140**; link distance **55** for `ABOUT`, **40** for `REPLACES`.
- Whenever new data adds nodes, call `d3ReheatSimulation()`.
- **Auto-fit:** when the node count increases, call `zoomToFit(500, 60)` after a 300 ms debounce. The **Fit** button calls the same.
- Set `autoPauseRedraw={false}` **only while** any animation is active (pulse, entrance, fade, hover-highlight); otherwise leave it `true` to save CPU.
- Size the canvas to its container with a `ResizeObserver` (`width`/`height` props).

### 6.6 Node detail drawer (`NodeDetail.tsx`)

Slides in from the right edge of the **graph panel** (320 px wide, `--panel`, left border, 200 ms transform transition). Opens on node click, closes on **×**, **Esc**, or clicking the canvas background.

*When a fact is selected:*
- Status pill: `Current` (green) or `Replaced` (muted).
- The fact text (16 px).
- **Source:** label `From your message`, then the `source_message` in a quoted block (if `null`, show `Source unavailable`).
- `Learned` + relative time (`created_at`), and, if replaced, `Replaced` + relative time (`replaced_at`).
- **Replaced by:** (if this fact was replaced) the new fact's text as a clickable row; clicking selects that node and centers the view on it. Derived from the `REPLACES` edge whose **target** is this fact.
- **Replaces:** (if this fact replaced others) clickable rows. Derived from `REPLACES` edges whose **source** is this fact.
- **About:** chips for each entity (colored dot + name), clickable. Derived from `ABOUT` edges.

*When an entity is selected:*
- Type pill (in the type color) and the name (16 px).
- **Facts** list: current facts first, then replaced ones faded with strikethrough; each row clickable.

Relative time format (`lib/time.ts`, `relativeTime(ts, now)`): `just now` (<1 min), `N min ago`, `N h ago`, `N days ago`. Pure function, takes `now` as a parameter so it's testable.

---

## 7. Data flow in code

### 7.1 `api/client.ts`
- `createSession()`, `getMessages(sessionId)`, `sendChat(sessionId, message)`, `getGraph()`, `getHealth()`.
- Throw `ApiError(status, detail)` for non-2xx (parse `{"detail": ...}` when present). Network failure → `ApiError(0, "network")`.
- No retries inside the client; retry policy lives in the hooks.

### 7.2 `hooks/useSession.ts`
- On mount: read `localStorage["mnemo.sessionId"]`.
  - If present: `getMessages(id)`. On success, restore the chat. On `404`, fall through to creating a new one.
  - If absent: `createSession()`.
- Store the id in `localStorage` after creating.
- `newSession()`: `createSession()`, replace the id, **clear the chat**, leave the graph untouched.

### 7.3 `hooks/useChat.ts`
- State: `messages`, `pending`, `lastError`, and `recalledByMessage` (a map from message index → `RecalledFact[]`).
- `send(text)`:
  1. Append the user message immediately (optimistic). `pending = true`.
  2. `sendChat(...)`.
  3. On success: append the assistant message; store `recalled` for it; call `onRecalled(recalled_fact_ids, matched_entity_ids)` so the graph can pulse; call `onChatDone()` so the polling hook goes into fast mode (§8).
  4. On failure: see §9.
- Prevent double-sends while `pending`.

### 7.4 `lib/graphData.ts` (pure, unit-tested)

The force-graph library **mutates** the objects you pass it: it replaces each link's `source`/`target` id with the node object and adds `x`, `y`, `vx`, `vy` to nodes. Therefore:

- `mergeSnapshot(prev, snapshot, now) -> GraphData`
  - **Reuse the previous node object** for every id that still exists (copy over updated fields like `status`, `label`, `replaced_at`), so positions survive polling. Create new node objects only for new ids.
  - Always build **fresh link objects** `{source: id, target: id, type}` from the snapshot.
  - Maintain `bornAt` (first seen; `0` for the very first snapshot) and `replacedSeenAt` (when `status` first became `replaced` on the client).
- `filterHistory(data, showHistory) -> GraphData`: when `showHistory` is false, drop `replaced` fact nodes and every link touching them (including `REPLACES`).
- `snapshotChanged(prev, next) -> boolean`: true when `updated_at` differs **or** the node count or edge count differs. Only rebuild graph data when this is true. (`extraction_pending` is stored separately and updates the badge on every poll.)
- Derived helpers for the drawer: `factsForEntity`, `entitiesForFact`, `replacedBy`, `replaces`.

---

## 8. Polling (`hooks/useGraphPolling.ts`)

- Poll `GET /graph`. **Adaptive interval:**
  - **Fast (700 ms)** while `extraction_pending > 0`, and for up to **15 s** after each completed chat call, or until two consecutive polls report `extraction_pending === 0`.
  - **Normal (2000 ms)** otherwise.
- Fetch immediately on mount and immediately after each chat response.
- **Never overlap requests:** schedule the next poll only after the previous one settles (`setTimeout` chain, not `setInterval`).
- **Pause** while `document.visibilityState === "hidden"`; refetch right away when the tab becomes visible.
- **On error:** keep the last good graph on screen, set status `Disconnected`, back off to **5 s**, and recover automatically on the next success.
- Expose: `{ graph, pending, connected, refreshNow(), enterFastMode() }`.
- Clean up timers and abort in-flight requests on unmount (`AbortController`).

---

## 9. Error and edge states

| Situation | Behavior |
|---|---|
| `POST /chat` returns `502` | Inline error bubble in the chat (`--danger` outline): `The language model is unavailable. Try again in a moment.` with a **Retry** button that resends the same text. The user's message stays visible |
| `503` | Same bubble: `Memory store unavailable. Check that FalkorDB is running.` |
| `404` on chat (session gone) | Silently create a new session, show a muted notice `Started a new session.`, and retry the message once |
| `422` | Should not happen (client-side validation); show `Message not accepted.` |
| Network failure | `Can't reach the API at <base url>.` + Retry |
| `/graph` fails | Header badge → `Disconnected`; graph stays as last seen |
| Empty graph | Graph empty-state text (§6.5) |
| Very long replies | Bubbles wrap; the list scrolls |
| Reload mid-session | Chat restored from `GET /sessions/{id}/messages`; graph from `/graph`. Recalled chips are **not** restored (they are only in-memory); that's fine |

Never show raw stack traces or JSON to the user.

---

## 10. Tests (`npm test`)

Unit tests only, no DOM or browser needed.

**`graphData.test.ts`**
- `mergeSnapshot` reuses the previous node object for an existing id (same reference, `x`/`y` preserved) and creates a new one for a new id.
- Links are always fresh objects with string `source`/`target`.
- `bornAt` is `0` on the first snapshot and `> 0` for nodes added later.
- `replacedSeenAt` is set when a fact flips `current → replaced`.
- `filterHistory(false)` removes replaced facts and every link touching them.
- `snapshotChanged`: false when nothing changed (even if `extraction_pending` differs), true on `updated_at` change, node-count change, edge-count change.
- Derived helpers: `replacedBy`, `replaces`, `entitiesForFact`, `factsForEntity` on a small fixture mirroring the Day 2 sample JSON (Project X / Python / Go).

**`time.test.ts`**: each bucket of `relativeTime` with a fixed `now`.

Also run `npm run build` and `npm run lint`; both must pass.

---

## 11. Suggested build order

1. Scaffold, install, config (`§4`), `types.ts`, `client.ts`, `colors.ts`, `time.ts` and `styles.css` variables.
2. `useSession` + `useChat` + `ChatPanel`/`Composer`/`MessageBubble` (chat works end to end, graph pane is a placeholder).
3. `graphData.ts` + tests, then `useGraphPolling`.
4. `GraphPanel` with a plain graph (circles and lines) and polling. Confirm nodes appear as you chat.
5. `draw.ts`: entity circles, fact pills, edges (dashed red arrows), replaced styling.
6. Animations: entrance, fade, recalled pulse, auto-fit, reheat.
7. `NodeDetail` drawer, `RecalledChips` hover/click linking, legend, history toggle, stats.
8. Header status badge, New session, error states, empty states.
9. Run the §12 walkthrough, fix what breaks, then `npm run build`.

**If behind, cut in this order:** entrance/fade animations → recalled-chip hover linking → click-for-source drawer details (keep a minimal drawer with the source message) → responsive stacking → legend. **Never cut:** the live polling graph, the replaced-fact styling (fade + strikethrough + red arrow), the recalled pulse, and the New session button. Those four *are* the demo.

---

## 12. Demo walkthrough (the Day 3 acceptance test, ≈2 minutes)

Use fake data only. This script is refined on Day 4.

**Reset memory first** (clean graph):
```bash
docker compose exec falkordb redis-cli GRAPH.DELETE mnemo
# then restart the API so it recreates indexes and the agent
```
Clear the browser's `localStorage` (or use a private window).

1. **Session 1.** Send `I'm building Project X, a task manager, in Python.` → the badge shows `Updating memory…`, then nodes **grow in**: `Project X`, `Python`, and fact pills (`Project X uses Python`, `Project X is a task manager`). Badge returns to `Memory idle`.
2. Send `I prefer short, direct answers.` → a violet **Preference** node appears with its fact.
3. Click **New session**. The chat clears; the **graph stays**.
4. Send `What do you know about Project X?` → a short reply, a `▸ Recalled N facts` line, and the matching nodes **pulse gold** in the graph. Expand the chip row to show which facts were used.
5. Send `Actually I switched Project X to Go.` → a `Go` node and `Project X uses Go` pill appear; `Project X uses Python` **fades with a strikethrough**, and a **red dashed arrow** points from the new fact to the old one.
6. **Click** the faded Python fact → the drawer shows `Replaced`, the source message, and `Replaced by: Project X uses Go`.
7. Send `What language is Project X written in?` → the reply says Go.
8. *(Optional)* Send `I prefer detailed explanations.` → the old preference fact fades, the new one replaces it (same Preference entity), and later replies get longer.
9. Toggle **Show history** off → replaced facts and red arrows disappear; on → they return.
10. Reload the page → the chat history and the graph are both restored.

---

## 13. Acceptance criteria (Day 3 checklist)

**Setup**
- [ ] Only the packages in §4.2 were installed; lockfile committed
- [ ] `npm run dev` serves on **5173**; `npm run build`, `npm run lint`, `npm test` all pass
- [ ] No CORS errors in the browser console

**Chat**
- [ ] Send with Enter, newline with Shift+Enter; empty messages blocked; composer disabled while pending
- [ ] User message appears immediately; typing indicator while waiting
- [ ] Chat is restored after a page reload; New session clears it and keeps the graph
- [ ] Recalled chips show under assistant replies with source tags; hovering a chip ring-highlights the node; clicking opens the drawer
- [ ] 502 / 503 / network errors show the specified inline messages with a working Retry

**Graph**
- [ ] Entities are colored by type per §6.2; Project nodes are larger
- [ ] Facts render as pills (32-char truncation) and as dots when zoomed far out
- [ ] Replaced facts: faded, dashed outline, strikethrough; `REPLACES` edge is a red dashed arrow pointing new → old
- [ ] After a reply, recalled nodes pulse gold for ~4 s
- [ ] New nodes animate in; a fact turning `replaced` fades over ~0.7 s
- [ ] Positions do **not** jump on every poll (identity-preserving merge)
- [ ] Auto-fit when nodes are added; the Fit button works
- [ ] Show history toggle hides/shows replaced facts and their arrows
- [ ] Stats line matches `/graph` `stats`

**Polling and status**
- [ ] Poll is fast while `extraction_pending > 0` and slow when idle; never overlapping; paused when the tab is hidden
- [ ] Badge shows `Updating memory…` / `Memory idle` / `Disconnected` correctly; stopping the API shows `Disconnected` and the graph stays visible; restarting it recovers on its own

**Detail drawer**
- [ ] Fact: status, text, source message, learned/replaced times, Replaced by / Replaces / About rows all clickable
- [ ] Entity: type, name, facts (current first, replaced faded)
- [ ] Closes via ×, Esc, and background click

**Demo**
- [ ] The §12 walkthrough works end to end, including reload

---

## 14. Known risks and rules of thumb

- **Library mutation.** `react-force-graph-2d` mutates the data you give it. Rebuilding nodes from scratch on every poll resets the layout and makes the graph jump. Reuse node objects by id (§7.4).
- **Canvas performance.** Keep `draw.ts` cheap: no per-frame allocations of fonts/paths where avoidable; cache `measureText` widths per label if drawing slows down. The demo graph is small (tens of nodes), so don't over-engineer.
- **Redraw pausing.** The canvas stops redrawing when idle. Animations only run if `autoPauseRedraw` is `false` while they are active (§6.5).
- **Port clashes.** Frontend is **5173**; FalkorDB's browser is **3000**; API is **8000**; FalkorDB is **6380**.
- **Eventual consistency.** A fact appears a few seconds *after* the reply (background extraction). That's expected; the `Updating memory…` badge and fast polling exist to make it look intentional.
- **Don't invent design.** If something isn't specified here, pick the simplest option that fits the palette. Don't add new colors, fonts, icon packs, or screens.
- **Fake data only** in demos and screenshots.

---

## 15. Roadmap (so Day 3 choices make sense)

**Day 4 (Oct 18): polish and submit**
- Fix extraction/recall bugs found in real use; tune the prompts if the demo walkthrough misbehaves.
- Final demo script, rehearsed twice; record a backup video.
- Finalize the root `README.md`: tagline, architecture diagram, setup, demo GIF/screenshot, FalkorDB credit.
- Submit. **Nothing new is built on Day 4.**

**Optional later:** a second agent sharing selected facts; procedural-memory `Skill` nodes; research/support modes as config changes.

---

## 16. Instructions for the coding agent

1. Build exactly what is in §4–§10. Do **not** add features, pages, packages, or styling beyond this file.
2. Install **only** the packages in §4.2. If something seems missing, say so instead of installing it.
3. Use the types in §3.1 verbatim; use the palette and sizes in §6 verbatim.
4. Keep drawing code in `lib/draw.ts` and the data merge logic in `lib/graphData.ts` (pure functions, unit-tested).
5. No backend changes except the single `CORS_ORIGINS` line in §4.4.
6. Create individual files (no zip archives).
7. When done, report: `npm run build` / `lint` / `test` results, a description or screenshot of the page after the §12 walkthrough, and any §13 item that is not met.