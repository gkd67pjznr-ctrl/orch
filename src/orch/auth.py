"""Read OAuth tokens from Claude Code's macOS Keychain entry."""

import json
import subprocess

def get_claude_tokens():
    """Read Claude Code's OAuth credentials from macOS Keychain.

    Returns a dict with accessToken, refreshToken, expiresAt, etc.
    Raises RuntimeError if credentials aren't found.
    """
    result = subprocess.run(
        ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Could not read Claude Code credentials from Keychain. "
            "Make sure Claude Code is installed and you're logged in."
        )
    
    data = json.loads(result.stdout)
    return data["claudeAiOauth"]