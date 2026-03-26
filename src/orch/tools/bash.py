import subprocess

from orch.tools.base import Tool

class BashTool(Tool):
    name = "bash"
    description = "Run a shell command and return the output."

    def get_schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run."
                    },
                },
                "required": ["command"]
            },
        }
    
    def run(self, **kwargs):
        command = kwargs["command"]
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        return output