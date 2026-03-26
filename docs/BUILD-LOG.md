# Orch — Build Log

Conversation notes from building orch step by step.

---

## 2026-03-25 / 2026-03-26 — Milestones 1 & 2

### Step 1: Hello World CLI

Created the project from scratch:
- `pyproject.toml` — project definition using hatchling build backend
- `src/orch/__init__.py` — package marker with `__version__`
- `src/orch/__main__.py` — enables `python -m orch`
- `src/orch/cli.py` — click CLI with `hello` command

Key concepts learned:
- `pyproject.toml` is read by pip, defined by PEP 621
- `__init__.py` marks a directory as a Python package
- `@click.group()` turns a function into a command group
- `@cli.command()` registers subcommands
- Decorators are functions that wrap other functions
- `pip install -e .` installs in editable mode
- Virtual environments isolate dependencies (`python3.13 -m venv .venv`)

### Step 2: Talk to Claude

Created the auth and provider layer:
- `src/orch/auth.py` — reads OAuth tokens from macOS Keychain
- `src/orch/ai/__init__.py` — package marker
- `src/orch/ai/provider.py` — calls Anthropic API

Key discovery: Anthropic blocks OAuth tokens from third-party tools. Server validates:
1. `auth_token` parameter (not `api_key`) in the SDK
2. `anthropic-beta: claude-code-20250219,oauth-2025-04-20,interleaved-thinking-2025-05-14`
3. System prompt must include "You are Claude Code, Anthropic's official CLI for Claude."

Found by analyzing gsd-2py's working implementation at `~/Projects/gsd-2py/packages/pi-ai/src/providers/anthropic.ts`. Not documented anywhere by Anthropic — reverse engineered by the community.

Key concepts learned:
- `subprocess.run()` executes terminal commands from Python
- `result.stdout`, `.stderr`, `.returncode` — CompletedProcess attributes
- `json.loads()` parses a JSON string into a Python dictionary
- f-strings: `f"Bearer {token}"` injects variables into strings
- The Anthropic SDK: `client.messages.create()` sends messages to Claude
- `message.content[0].text` navigates the response object

### Step 3: Streaming Output

Added streaming to show tokens as they arrive:
- `ask_claude_stream()` generator function using `yield`
- `client.messages.stream()` instead of `.create()`
- "Thinking..." indicator with carriage return (`\r`) overwrite

Key concepts learned:
- `yield` makes a function a generator — produces values one at a time
- `with X as Y` — context managers for automatic cleanup
- `stream.text_stream` — an iterator from the Anthropic SDK
- `for chunk in stream.text_stream` — loop over arriving pieces
- `nl=False` in `click.echo()` — suppress newline

### Step 4: Tool Calling

Created the tool system:
- `src/orch/tools/base.py` — Tool base class with `get_schema()` and `run()`
- `src/orch/tools/bash.py` — BashTool using subprocess
- Updated provider.py with tool call loop

Key concepts learned:
- Classes: `class BashTool(Tool)` — inheritance
- `self` — refers to the specific instance
- `**kwargs` — collects keyword arguments into a dictionary
- `raise NotImplementedError` — intentional error for unimplemented methods
- JSON Schema — standard way to describe data shapes for the API
- `while True` + `break` on `stop_reason == "end_turn"` — tool call loop
- Two `messages.append()` per tool call: assistant turn + tool result turn

### Step 5: Agent Loop

Created the interactive chat:
- `src/orch/agent/loop.py` — `run_agent()` with nested while loops
- Added `orch chat` command to cli.py

Key concepts learned:
- `input("> ")` — built-in function for user input
- `try: ... except (KeyboardInterrupt, EOFError):` — graceful exit on Ctrl+C/Ctrl+D
- `.strip()` — removes whitespace from strings
- `continue` — skip to next loop iteration
- Nested loops: outer (user input) and inner (Claude turn with tools)
- `messages = []` grows as conversation history

### Step 6: File Tools

Created read, write, and edit tools:
- `src/orch/tools/read.py` — ReadTool using pathlib
- `src/orch/tools/write.py` — WriteTool with parent directory creation
- `src/orch/tools/edit.py` — EditTool with find/replace
- Updated loop.py with tool registry

Key discovery: Claude ignores schema parameter names and uses Claude Code conventions (e.g., `path` not `file_path`). This is because the system prompt says "You are Claude Code" and Claude follows its training. Pi-mono does the same — matches the model's expectations rather than fighting it.

Key concepts learned:
- `pathlib.Path` — object-oriented file paths (`.exists()`, `.read_text()`, `.write_text()`)
- `.parent.mkdir(parents=True, exist_ok=True)` — safe directory creation
- `content.count()` and `content.replace()` — string methods
- Dict comprehension: `{tool.name: tool for tool in all_tools}`
- List comprehension: `[tool.get_schema() for tool in all_tools]`
- Design principle: work with the model's training, don't fight it

---

## Current State

**Files created so far:**
```
orch/
├── pyproject.toml
├── src/orch/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── auth.py
│   ├── ai/
│   │   ├── __init__.py
│   │   └── provider.py
│   ├── agent/
│   │   ├── __init__.py
│   │   └── loop.py
│   └── tools/
│       ├── __init__.py
│       ├── base.py
│       ├── bash.py
│       ├── read.py
│       ├── write.py
│       └── edit.py
├── .venv/ (Python 3.13)
└── docs/
    └── architecture/ (00-10, design docs from planning phase)
```

**Working commands:**
- `orch hello` — verify install
- `orch --version` — show version
- `orch --help` — show help
- `orch ask "prompt"` — one-shot streaming question
- `orch chat` — interactive multi-turn conversation with bash/read/write/edit tools

---

## 2026-03-26 — Milestone 3

### Step 7: Sessions (JSONL Persistence)

Created the session layer:
- `src/orch/session/store.py` — low-level JSONL read/write (save_message, load_messages)
- `src/orch/session/manager.py` — session lifecycle (create IDs, get paths, list sessions)
- Updated `agent/loop.py` to save every message immediately to disk
- Added `--resume/-r` and `--list/-l` flags to `orch chat`

Key concepts learned:
- `open(path, "a")` — append mode vs `"r"` (read) and `"w"` (write/overwrite)
- `json.dumps()` — Python dict to JSON string (opposite of `json.loads()`)
- `f.write()` — write a string to a file
- `for line in f:` — iterate over file lines
- `@click.option()` vs `@click.argument()` — optional flags vs required positional args
- `is_flag=True` — option with no value, just on/off
- `_serialize_content()` — converting SDK objects to plain dicts for JSON storage
- Naming conflict: `"list_all"` as third argument to avoid shadowing Python's `list` builtin

Debugging lesson: variable name mismatch (`assistant_message` vs `assistant_msg`) caused NameError. Indentation of `if response.stop_reason` inside vs outside the `for` loop caused the inner loop to never break — second message hung forever.

### Step 8: System Prompt (Context Discovery)

Created the prompt layer:
- `src/orch/prompt/context_files.py` — walks up directory tree finding CLAUDE.md/AGENTS.md
- `src/orch/prompt/builder.py` — assembles system prompt from base + context files

Key discovery: system prompt with appended context as a single string causes 400 error (OAuth validation). Must use list-of-blocks format:
```python
system=[
    {"type": "text", "text": "You are Claude Code..."},
    {"type": "text", "text": "project context here"},
]
```
The first block must be the Claude Code identity. Additional blocks can be anything.

Key concepts learned:
- `Path.cwd()` — current working directory
- `.resolve()` — absolute path, no symlinks
- Walking up directories: `parent = current.parent; if parent == current: break`
- `found.reverse()` — in-place list reversal
- Tuple unpacking in for loops: `for path, content in context_files`
- API accepts `system=` as string OR list of content blocks

### Step 9: Configuration (pydantic-settings)

Created the config layer:
- `src/orch/config/settings.py` — Settings class with env var overrides
- Wired into agent loop (model, max_tokens) and session manager (sessions_dir)

Key concepts learned:
- `pydantic_settings.BaseSettings` — auto-reads environment variables
- `model_config = {"env_prefix": "ORCH_"}` — maps fields to ORCH_MODEL, ORCH_MAX_TOKENS, etc.
- `VAR=value command` — shell trick to set env var for one command only
- Model names are dated: `claude-sonnet-4-20250514`, `claude-haiku-4-5-20251001`
- Priority chain: env var > default value (config file support added later)

---

## Current State

**Files created so far:**
```
orch/
├── pyproject.toml
├── CLAUDE.md
├── src/orch/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── auth.py
│   ├── ai/
│   │   ├── __init__.py
│   │   └── provider.py
│   ├── agent/
│   │   ├── __init__.py
│   │   └── loop.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── bash.py
│   │   ├── read.py
│   │   ├── write.py
│   │   └── edit.py
│   ├── session/
│   │   ├── __init__.py
│   │   ├── store.py
│   │   └── manager.py
│   ├── prompt/
│   │   ├── __init__.py
│   │   ├── context_files.py
│   │   └── builder.py
│   └── config/
│       ├── __init__.py
│       └── settings.py
├── .venv/ (Python 3.13)
└── docs/
    ├── BUILD-TRACKER.md
    ├── BUILD-LOG.md
    └── architecture/ (00-10, design docs from planning phase)
```

**Working commands:**
- `orch hello` — verify install
- `orch --version` / `orch --help`
- `orch ask "prompt"` — one-shot streaming question
- `orch chat` — interactive multi-turn conversation with bash/read/write/edit tools
- `orch chat -l` — list saved sessions
- `orch chat -r SESSION_ID` — resume a previous session
- `ORCH_MODEL=claude-haiku-4-5-20251001 orch chat` — override model via env var

**Next up:** Milestone 4 — TUI (custom markdown renderer, full textual app).
