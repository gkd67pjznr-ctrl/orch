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