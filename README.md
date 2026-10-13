# Mnemo

Mnemo is a graph-memory core for an AI project assistant, backed by FalkorDB.
This repository is being built in stages; the initial milestone focuses on
persistent memory, fact provenance, and replacement history.

## Development setup

```bash
docker compose up -d
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env` before running the LLM-backed extraction
scenario. The FalkorDB browser is available at <http://localhost:3000>.
