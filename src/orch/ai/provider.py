"""Talk to Claude using OAuth tokens from Claude Code."""

import anthropic

from orch.auth import get_claude_tokens
from orch.tools.bash import BashTool

def ask_claude_stream(prompt):
    """Send a message to Claude and yield response text as it arrives."""
    tokens = get_claude_tokens()

    client = anthropic.Anthropic(
        auth_token=tokens["accessToken"],
        default_headers={
            "anthropic-beta": "claude-code-20250219,oauth-2025-04-20,interleaved-thinking-2025-05-14",
        },
    )

    bash_tool = BashTool()
    tools = [bash_tool.get_schema()]

    messages = [{"role": "user", "content": prompt}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system="You are Claude Code, Anthropic's official CLI for Claude.",
            tools=tools,
            messages=messages,
        )

        for block in response.content:
            if block.type == "text":
                yield block.text
            elif block.type == "tool_use":
                yield f"\n[Running: {block.input.get('command', '')}]\n"
                result = bash_tool.run(**block.input)
                yield f"{result}\n"

                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    ],
                })

        if response.stop_reason == "end_turn":
            break