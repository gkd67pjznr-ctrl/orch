"""Assemble the system prompt from base prompt + context files."""

from orch.prompt.context_files import find_context_files

BASE_PROMPT = "You are Claude Code, Anthropic's official CLI for Claude."

def build_system_prompt():
    """Build the full system prompt with discovered context."""
    blocks = [{"type": "text", "text": BASE_PROMPT}]

    context_files = find_context_files()
    for path, content in context_files:
        blocks.append({"type": "text", "text": f"# {path}\n\n{content}"})

    return blocks