"""Write tool - lets Claude create and write files."""

from pathlib import Path

from orch.tools.base import Tool


class WriteTool(Tool):
    name = "write"
    description = "Write content to a file. Creates the file if it doesn't exist."

    def get_schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file.",
                    },
                },
                "required": ["path", "content"],
            },
        }
    
    def run(self, **kwargs):
        file_path = Path(kwargs["path"])
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(kwargs["content"])
        return f"Wrote {len(kwargs['content'])} characters to {file_path}"