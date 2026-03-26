"""Read tool - lets Claude read file contents."""

from pathlib import Path

from orch.tools.base import Tool

class ReadTool(Tool):
    name = "read"
    description = "Read the contents of a file."

    def get_schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to read."
                    },
                },
                "required": ["path"]
            },
        }
    def run(self, **kwargs):
        file_path = Path(kwargs["path"])
        if not file_path.exists():
            return f"Error: {file_path} does not exist."
        return file_path.read_text()