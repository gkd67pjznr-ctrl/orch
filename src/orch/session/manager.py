"""Session lifecycle - create, list, find sessions."""

import time
from pathlib import Path
from orch.config.settings import get_settings

def get_sessions_dir():
    """Return the path where sessions are stored."""
    settings = get_settings()
    sessions_dir = Path(settings.sessions_dir)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir

def create_session_id():
    """Create a unique session ID based on timestamp."""
    return str(int(time.time()))

def get_session_path(session_id):
    """Return the file path for a given session ID."""
    return get_sessions_dir() / f"{session_id}.jsonl"

def list_sessions():
    """List all existing sessions."""
    sessions_dir = get_sessions_dir()
    files = sorted(sessions_dir.glob("*.jsonl"), reverse=True)
    return [f.stem for f in files]