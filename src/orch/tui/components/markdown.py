"""Markdown rendering for agent output."""

from rich.console import Console
from rich.markdown import Markdown


console = Console()

def render_markdown(text):
    """Render a markdown string to the terminal."""
    md = Markdown(text)
    console.print(md)