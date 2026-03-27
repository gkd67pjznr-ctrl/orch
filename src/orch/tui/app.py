"""Main TUI application for orch chat."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog
from textual.containers import VerticalScroll
from rich.markdown import Markdown


class ChatApp(App):
    """Orch chat TUI."""

    CSS = """
    #chat-log {
        height: 1fr;
        border: solid green;
        padding: 1;
    }
    #input {
        dock: bottom;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    def __init__(self, agent_callback=None):
        super().__init__()
        self.agent_callback = agent_callback

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="chat-log", wrap=True, markup=True)
        yield Input(placeholder="Type a message...", id="input")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.value.strip():
            return
        
        chat_log = self.query_one("#chat-log", RichLog)
        user_input = event.value
        event.input.clear()

        chat_log.write(f"[bold cyan]> {user_input}[/]")

        if self.agent_callback:
            response = self.agent_callback(user_input)
            chat_log.write(Markdown(response))

    
