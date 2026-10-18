"""Environment-backed configuration for Mnemo."""
# this file is responsible for reading configuration from environment variables
# and providing a structured Settings object.

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# this class represents the configuration settings for the Mnemo application
# it is frozen to prevent modification after creation,
# ensuring that the settings remain consistent throughout the application's lifecycle
@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    extraction_model: str
    conflict_model: str
    chat_model: str
    cors_origins: list[str]
    falkordb_host: str
    falkordb_port: int
    falkordb_password: str | None
    falkordb_username: str | None
    falkordb_ssl: bool
    falkordb_url: str | None
    falkordb_graph: str
    agent_id: str
    agent_name: str
    log_level: str
    port: int


# function to parse a comma-separated string of CORS origins into a list of strings
def _parse_cors_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


# function to read current configuration from environment variables and return a Settings object
def get_settings() -> Settings:
    """Read current configuration from environment variables."""
    password = os.getenv("FALKORDB_PASSWORD", "").strip() or None
    username = os.getenv("FALKORDB_USERNAME", "").strip() or None
    url = os.getenv("FALKORDB_URL", "").strip() or None
    ssl_env = os.getenv("FALKORDB_SSL", "").strip().lower()
    is_ssl = ssl_env in ("1", "true", "yes")
    raw_cors = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        extraction_model=os.getenv("EXTRACTION_MODEL", "gemini-2.5-flash-lite"),
        conflict_model=os.getenv("CONFLICT_MODEL", "gemini-2.5-flash-lite"),
        chat_model=os.getenv("CHAT_MODEL", "gemini-2.5-flash"),
        cors_origins=_parse_cors_origins(raw_cors),
        falkordb_host=os.getenv("FALKORDB_HOST", "localhost"),
        falkordb_port=int(os.getenv("FALKORDB_PORT", "6380")),
        falkordb_password=password,
        falkordb_username=username,
        falkordb_ssl=is_ssl,
        falkordb_url=url,
        falkordb_graph=os.getenv("FALKORDB_GRAPH", "mnemo"),
        agent_id=os.getenv("AGENT_ID", "agent_main"),
        agent_name=os.getenv("AGENT_NAME", "Mnemo"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        port=int(os.getenv("PORT", "8000")),
    )


def load_prompt(name: str) -> str:
    """Load a packaged prompt by its filename stem."""
    if not name or Path(name).name != name:
        raise ValueError("Prompt name must be a filename stem")
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.md"
    return prompt_path.read_text(encoding="utf-8")
