""" Edit tool - lets Claude find and replace text in files."""

from pathlib import Path

from orch.tools.base import Tool


class EditTool(Tool):
    name = "edit"
    description = "Replace a specific string in a file with new content."

    def get_schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to edit.",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "The exact text to find and replace.",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The text to replace it with.",
                    },
                },
                "required": ["path", "old_string", "new_string"],
            },
        }
    
    def run(self, **kwargs):
        file_path = Path(kwargs["path"])
        if not file_path.exists():
            return f"Error: {file_path} does not exist."
        
        content = file_path.read_text()
        old_string = kwargs["old_string"]
        new_string = kwargs["new_string"]

        if old_string not in content:
            return f"Error: could not find the text to replace in {file_path}."
        
        count = content.count(old_string)
        if count > 1:
            return f"Error: found {count} matches. Provide more context to make a unique match."
        
        content = content.replace(old_string, new_string, 1)
        file_path.write_text(content)
        return f"Edited {file_path}"