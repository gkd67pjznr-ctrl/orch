"""The core agent loop - multi-turn conversation with tool calling."""

import anthropic

from orch.auth import get_claude_tokens
from orch.tools.bash import BashTool
from orch.tools.read import ReadTool
from orch.tools.write import WriteTool
from orch.tools.edit import EditTool
from orch.session.manager import create_session_id, get_session_path, list_sessions
from orch.session.store import save_message, load_messages
from orch.prompt.builder import build_system_prompt
from orch.config.settings import get_settings

def run_agent(session_id=None):
    """Run an interactive agent loop."""
    settings = get_settings()
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
    
    if session_id is None:
        session_id = create_session_id()
        print(f"New session: {session_id}")
    else:
        print(f"Resuming session: {session_id}")

    session_path = get_session_path(session_id)
    messages = load_messages(session_path)

    if messages:
        print(f"Loaded {len(messages)} messages from history.\n")
    else:
        print("orch chat - type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("> ")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if user_input.strip() == "exit":
            print("Goodbye!")
            break

        if not user_input.strip():
            continue

        user_message = {"role": "user", "content": user_input}
        messages.append(user_message)
        save_message(session_path, user_message)

        while True:
            response = client.messages.create(
                model=settings.model,
                max_tokens=settings.max_tokens,
                system=build_system_prompt(),
                tools=tools,
                messages=messages,
            )

            for block in response.content:
                if block.type == "text":
                    print(block.text)
                elif block.type == "tool_use":
                    print(f"\n[{block.name}: {block.input}]")
                    tool = tool_map[block.name]
                    result = tool.run(**block.input)
                    print(result)

                    assistant_msg = {"role": "assistant", "content": _serialize_content(response.content)}
                    messages.append(assistant_msg)
                    save_message(session_path, assistant_msg)
                    tool_result_msg = {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        ],
                    }
                    messages.append(tool_result_msg)
                    save_message(session_path, tool_result_msg)
            if response.stop_reason == "end_turn":
                assistant_msg = {"role": "assistant", "content": _serialize_content(response.content)}
                messages.append(assistant_msg)
                save_message(session_path, assistant_msg)
                break
                    
def _serialize_content(content):
    """Convert API response content blocks to JSON-serializable dicts."""
    result = []
    for block in content:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            result.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return result