"""History recording - append-only log of completed work."""

import time
from pathlib import Path

from orch.orchestrator.state import get_workflow_dir


def record_completion(work_id: str, summary: str, status: str = "done") -> Path:
    """Record a completed work item to history."""
    history_dir = get_workflow_dir() / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    filename = f"{timestamp}-{work_id}.md"
    entry_path = history_dir / filename

    content = f"""# {work_id}

**Status**: {status}
**Completed**: {timestamp}

## Summary

{summary}
"""

    entry_path.write_text(content)
    return entry_path

def list_history() -> list[str]:
    """List all history entries, newest first."""
    history_dir = get_workflow_dir() / "history"
    if not history_dir.exists():
        return []
    files = sorted(history_dir.glob("*.md"), reverse=True)
    return [f.stem for f in files]