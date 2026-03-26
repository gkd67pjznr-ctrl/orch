"""Base class for all tools."""

class Tool:
    """A tool that Claude can call."""

    name: str = ""
    description: str = ""

    def get_schema(self):
        """Return the tool schema for the Anthropic API."""
        raise NotImplementedError
    
    def run(self, **kwargs):
        """Execute the tool with the given arguments."""
        raise NotImplementedError