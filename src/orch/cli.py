"""CLI entry point for orch."""

import click

from orch import __version__


@click.group()
@click.version_option(version=__version__, prog_name="orch")
def cli():
    """orch - Context-centric AI coding agent CLI."""

@cli.command()
def hello():
    """Say hello to verify orch is installed."""
    click.echo("Hello from orch!")

@cli.command()
@click.argument("prompt")
def ask(prompt):
    """Ask Claude a question."""
    from orch.ai.provider import ask_claude_stream

    first = True
    click.echo("Thinking...", nl=False)
    for chunk in ask_claude_stream(prompt):
        if first:
            click.echo("\r", nl=False)
            first = False
        click.echo(chunk, nl=False)
    click.echo()

@cli.command()
@click.option("--resume", "-r", default=None, help="Resume a session by ID.")
@click.option("--list", "-l", "list_all", is_flag=True, help="List all sessions.")
def chat(resume, list_all):
    """Start an interactive chat with Claude."""
    from orch.agent.loop import run_agent
    from orch.session.manager import list_sessions
    
    if list_all:
        sessions = list_sessions()
        if not sessions:
            click.echo("No sessions found.")
        else:
            click.echo("Sessions:")
            for s in sessions:
                click.echo(f" {s}")
        return
    
    run_agent(session_id=resume)


@cli.command()
@click.option("--resume", "-r", default=None, help="Resume a session by ID.")
def tui(resume):
    """Start the TUI chat interface."""
    from orch.agent.loop import single_turn
    from orch.auth import get_claude_tokens
    from orch.config.settings import get_settings
    from orch.prompt.builder import build_system_prompt
    from orch.session.manager import create_session_id, get_session_path
    from orch.session.store import save_message, load_messages
    from orch.tools.bash import BashTool
    from orch.tools.read import ReadTool
    from orch.tools.write import WriteTool
    from orch.tools.edit import EditTool
    from orch.tui.app import ChatApp
    import anthropic

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
    
    session_id = resume or create_session_id()
    session_path = get_session_path(session_id)
    messages = load_messages(session_path)

    def handle_message(user_input):
        user_msg = {"role": "user", "content": user_input}
        messages.append(user_msg)
        save_message(session_path, user_msg)
        
        response = single_turn(messages, client, tools, tool_map)
        
        save_message(session_path, messages[-1])
        return response
    
    app = ChatApp(agent_callback=handle_message)
    app.run()


@cli.command()
def init():
    """Initialize .workflow/ in the current project."""
    from orch.orchestrator.state import init_workflow

    success, message = init_workflow()
    click.echo(message)

@cli.command()
@click.argument("prompt")
def quick(prompt):
    """Run a one-off task with orchestrator tracking."""
    from orch.orchestrator.orchestrator import run_quick
    from orch.tui.components.markdown import render_markdown

    click.echo("Working...")
    response = run_quick(prompt)
    render_markdown(response)

@cli.command()
def status():
    """Show workflow status."""
    from orch.orchestrator.state import read_active, get_workflow_dir
    from orch.orchestrator.history import list_history

    workflow_dir = get_workflow_dir()
    if not workflow_dir.exists():
        click.echo("No .workflow/ found. Run 'orch init' first.")
        return
    
    active = read_active
    if active:
        click.echo("Active work:")
        click.echo(f"  {active}")
    else:
        click.echo("No active work.")

    history = list_history()
    if history:
        click.echo(f"\nHistory ({len(history)} items):")
        for h in history[:5]:
            click.echo(f"  {h}")
    else:
        click.echo("\nNo history yet.")