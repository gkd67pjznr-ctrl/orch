"""Workflow state management - ACTIVE.toml, registry."""

from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import tomli_w

WORKFLOW_DIR = ".workflow"

def get_workflow_dir():
    """Return the .workflow directory path for the current project."""
    return Path.cwd() / WORKFLOW_DIR

def init_workflow():
    """Initialize a .workflow directory in the current project."""
    workflow_dir = get_workflow_dir()
    if workflow_dir.exists():
        return False, "Already initialized."
    
    workflow_dir.mkdir()
    (workflow_dir / "history").mkdir()
    (workflow_dir / "completions").mkdir()

    project_toml = {
        "project": {
            "name": Path.cwd().name,
            "description": "",
        },
    }
    (workflow_dir / "PROJECT.toml").write_text(tomli_w.dumps(project_toml))

    registry = {"items": []}
    (workflow_dir / "registry.toml").write_text(tomli_w.dumps(registry))

    return True, f"initialized {workflow_dir}"

def write_active(context):
    """Write ACTIVE.toml with focused context for the agent."""
    active_path = get_workflow_dir() / "ACTIVE.toml"
    active_path.write_text(tomli_w.dumps(context))
    return active_path

def read_active():
    """Read the current ACTIVE.toml."""
    active_path = get_workflow_dir() / "ACTIVE.toml"
    if not active_path.exists():
        return None
    with open(active_path, "rb") as f:
        return tomllib.load(f)
    
def clear_active():
    """Remove ACTIVE.toml when work is complete."""
    active_path = get_workflow_dir() / "ACTIVE.toml"
    if active_path.exists():
        active_path.unlink()
