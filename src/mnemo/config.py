"""Environment-backed configuration for Mnemo."""
# this file is responsible for reading configuration from environment variables
# and providing a structured Settings object.

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    extraction_model: str
    conflict_model: str
    falkordb_host: str
    falkordb_port: int
    falkordb_password: str | None
    falkordb_graph: str
    agent_id: str
    agent_name: str
    log_level: str


def get_settings() -> Settings:
    """Read current configuration from environment variables."""
    password = os.getenv("FALKORDB_PASSWORD", "").strip() or None
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        extraction_model=os.getenv(
            "EXTRACTION_MODEL", "gemini-2.5-flash-lite"
        ),
        conflict_model=os.getenv("CONFLICT_MODEL", "gemini-2.5-flash-lite"),
        falkordb_host=os.getenv("FALKORDB_HOST", "localhost"),
        falkordb_port=int(os.getenv("FALKORDB_PORT", "6380")),
        falkordb_password=password,
        falkordb_graph=os.getenv("FALKORDB_GRAPH", "mnemo"),
        agent_id=os.getenv("AGENT_ID", "agent_main"),
        agent_name=os.getenv("AGENT_NAME", "Mnemo"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


def load_prompt(name: str) -> str:
    """Load a packaged prompt by its filename stem."""
    if not name or Path(name).name != name:
        raise ValueError("Prompt name must be a filename stem")
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.md"
    return prompt_path.read_text(encoding="utf-8")
