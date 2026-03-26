import json
from pathlib import Path

def save_message(session_path, message):
    """Append a single message to a session file."""
    session_path.parent.mkdir(parents=True, exist_ok=True)
    with open(session_path, "a") as f:
        f.write(json.dumps(message) + "\n")

def load_messages(session_path):
    """Load all messages from a session file."""
    if not session_path.exists():
        return []
    messages = []
    with open(session_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                messages.append(json.loads(line))
    return messages