from pathlib import Path

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Orch configuration with layered decaults."""

    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    sessions_dir: str = str(Path.home() / ".config" / "orch" / "sessions")

    model_config = {
        "env_prefix": "ORCH_",
    }

def get_settings():
    """Load settings."""
    return Settings()