"""Main orchestrator - runs agents with focused context."""

from orch.orchestrator.state import write_active, read_active, clear_active, get_workflow_dir
from orch.orchestrator.history import record_completion
from orch.agent.loop import single_turn
from orch.auth import get_claude_tokens
from orch.config.settings import get_settings
from orch.tools.bash import BashTool
from orch.tools.read import ReadTool
from orch.tools.write import WriteTool
from orch.tools.edit import EditTool
from orch.prompt.builder import build_system_prompt

import anthropic


def run_quick(prompt: str) -> str:
    """Run a one-off task with orchestrator tracking."""
    tokens = get_claude_tokens()

    client = anthropic.Anthropic(
        auth_token=tokens["accessToken"],
        default_headers={
            "anthropic-beta": "claude-code-20250219,oauth-2025-04-20,interleaved-thinking-2025-05-14",
        },
    )

    all_tools = [BashTool(), ReadTool(), WriteTool(), EditTool()]
    tool_map = {tool.name: tool for tool in all_tools}
    tools = [tool.get_schema() for tool in all_tools]

    context = {
        "task": {"type": "quick", "prompt": prompt},
    }
    write_active(context)

    messages = [{"role": "user", "content": prompt}]
    response = single_turn(messages, client, tools, tool_map)

    clear_active()
    record_completion("quick", summary=prompt, status="done")

    return response