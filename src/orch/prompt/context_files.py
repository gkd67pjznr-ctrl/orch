"""Discover context files by walking up from the current directory."""

from pathlib import Path

CONTEXT_FILENAMES = [
    "CLAUDE.md",
    "AGENTS.md",
    ".claude/instructions.md",
]

def find_context_files(start_dir=None):
    """Walk up from start_dir to root, collecting context files.
    
        Returns a list of (path, content) tuples, outermost directory first.
    """
    if start_dir is None:
        start_dir = Path.cwd()
    else:
        start_dir = Path(start_dir)

    found = []
    current = start_dir.resolve()

    while True:
        for name in CONTEXT_FILENAMES:
            candidate = current / name
            if candidate.is_file():
                found.append((str(candidate), candidate.read_text()))

        parent = current.parent
        if parent == current:
            break
        current = parent

    found.reverse()
    return found