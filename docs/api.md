# Mnemo API Specification

This document defines the HTTP API contract exposed by the FastAPI server (`mnemo.api.main:app`). Day 3 frontend components consume these endpoints.

Base URL: `http://localhost:8000`

---

## Endpoints

### 1. `GET /health`
Verify server and FalkorDB graph store health.

**Response `200 OK`**:
```json
{
  "status": "ok",
  "graph": "mnemo",
  "agent_id": "agent_main"
}
```

**Response `503 Service Unavailable`** (FalkorDB unreachable):
```json
{
  "detail": "memory store unavailable"
}
```

---

### 2. `POST /sessions`
Create a new chat session for the default agent (`agent_main`).

**Response `201 Created`**:
```json
{
  "session_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a"
}
```

---

### 3. `GET /sessions/{session_id}/messages`
Retrieve full conversation message history for a session (chronological order).

**Response `200 OK`**:
```json
{
  "session_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
  "messages": [
    {
      "role": "user",
      "text": "I am building Project X in Python.",
      "seq": 1,
      "ts": 1760000000000
    },
    {
      "role": "assistant",
      "text": "Got it! I will remember Project X is built in Python.",
      "seq": 2,
      "ts": 1760000001000
    }
  ]
}
```

**Response `404 Not Found`**:
```json
{
  "detail": "Session 'nonexistent-session' not found"
}
```

---

### 4. `POST /chat`
Send a user message, run memory recall, generate an assistant reply, and enqueue background fact extraction.

**Request Body**:
```json
{
  "session_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
  "message": "Actually I switched Project X from Python to Go."
}
```

**Response `200 OK`**:
```json
{
  "reply": "Understood, I've noted that Project X is now using Go.",
  "session_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
  "event_id": "f281e289-53e3-4d6b-9c71-081e82811a22",
  "recalled_fact_ids": [
    "7a1e2f89-823a-41bc-9d01-1e9218201b55"
  ],
  "matched_entity_ids": [
    "e91a2f11-0021-4d1a-8e22-1920aa112001"
  ],
  "recalled": [
    {
      "id": "7a1e2f89-823a-41bc-9d01-1e9218201b55",
      "text": "Project X uses Python",
      "created_at": 1760000000000,
      "source": "direct"
    }
  ],
  "extraction_pending": 1
}
```

**Error Responses**:
- `404 Not Found`: Session does not exist.
- `422 Unprocessable Entity`: Message is empty or exceeds 4000 characters.
- `502 Bad Gateway`: Language model API failure.
- `503 Service Unavailable`: Database store failure.

---

### 5. `GET /graph`
Retrieve the current entity/fact graph snapshot and background extraction queue status for visualization.

**Response `200 OK`**:
```json
{
  "nodes": [
    {
      "id": "e91a2f11-0021-4d1a-8e22-1920aa112001",
      "kind": "entity",
      "label": "Project X",
      "entity_type": "Project",
      "created_at": 1760000000000
    },
    {
      "id": "7a1e2f89-823a-41bc-9d01-1e9218201b55",
      "kind": "fact",
      "label": "Project X uses Go",
      "status": "current",
      "created_at": 1760000010000,
      "replaced_at": null,
      "source_message": "Actually I switched Project X from Python to Go."
    },
    {
      "id": "1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e",
      "kind": "fact",
      "label": "Project X uses Python",
      "status": "replaced",
      "created_at": 1760000000000,
      "replaced_at": 1760000010000,
      "source_message": "I am building Project X in Python."
    }
  ],
  "edges": [
    {
      "source": "7a1e2f89-823a-41bc-9d01-1e9218201b55",
      "target": "e91a2f11-0021-4d1a-8e22-1920aa112001",
      "type": "ABOUT"
    },
    {
      "source": "7a1e2f89-823a-41bc-9d01-1e9218201b55",
      "target": "1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e",
      "type": "REPLACES"
    }
  ],
  "stats": {
    "entities": 1,
    "current_facts": 1,
    "replaced_facts": 1
  },
  "updated_at": 1760000010000,
  "extraction_pending": 0
}
```
