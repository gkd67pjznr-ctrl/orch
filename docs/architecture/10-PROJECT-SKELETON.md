# Orch — Project Skeleton & Build Tracker

## Project Name: `orch`

Short for orchestrator. Context-centric AI coding agent CLI.

## Directory Structure

```
orch/
├── pyproject.toml                 # Project config, dependencies, build
├── README.md                      # Project overview
├── .gitignore                     # Python gitignore
│
├── src/
│   └── orch/
│       ├── __init__.py            # Package version
│       ├── __main__.py            # `python -m orch` entry point
│       ├── cli.py                 # click CLI definition (all commands)
│       │
│       ├── ai/                    # LLM provider layer
│       │   ├── __init__.py
│       │   ├── provider.py        # Unified interface (anthropic SDK first, litellm later)
│       │   ├── streaming.py       # Async streaming helpers
│       │   ├── models.py          # Model registry and resolution
│       │   └── cost.py            # Token counting and cost calculation
│       │
│       ├── agent/                 # Agent loop
│       │   ├── __init__.py
│       │   ├── loop.py            # The core agent loop (~200-300 lines)
│       │   ├── messages.py        # Message types (user, assistant, tool_result)
│       │   └── events.py          # Event types (agent_start, tool_call, etc.)
│       │
│       ├── tools/                 # Tool implementations
│       │   ├── __init__.py
│       │   ├── base.py            # Tool base class and registry
│       │   ├── read.py            # File reading
│       │   ├── write.py           # File writing
│       │   ├── edit.py            # Find/replace editing
│       │   ├── bash.py            # Shell command execution
│       │   ├── grep.py            # Content search (optional)
│       │   └── find.py            # File search (optional)
│       │
│       ├── session/               # Session persistence
│       │   ├── __init__.py
│       │   ├── store.py           # JSONL read/write
│       │   ├── manager.py         # Session lifecycle (create, load, list)
│       │   └── compaction.py      # Context summarization (Phase 2+)
│       │
│       ├── orchestrator/          # Workflow orchestration
│       │   ├── __init__.py
│       │   ├── orchestrator.py    # Main orchestrator class
│       │   ├── state.py           # ACTIVE.toml, registry.toml management
│       │   ├── context_builder.py # Build ACTIVE.toml context from history
│       │   ├── history.py         # History recording and querying
│       │   └── doctor.py          # Pure Python audit/validation
│       │
│       ├── multiplexer/           # Terminal multiplexer integration
│       │   ├── __init__.py
│       │   ├── base.py            # Abstract multiplexer interface
│       │   ├── cmux.py            # cmux socket API integration (primary)
│       │   ├── tmux.py            # tmux fallback
│       │   └── inline.py          # No-multiplexer fallback (sequential)
│       │
│       ├── tui/                   # Terminal UI
│       │   ├── __init__.py
│       │   ├── app.py             # Main textual app (orchestrator TUI)
│       │   ├── agent_app.py       # Agent TUI (runs in spawned panes)
│       │   ├── components/        # Reusable UI components
│       │   │   ├── __init__.py
│       │   │   ├── chat.py        # Chat message display
│       │   │   ├── markdown.py    # Custom streaming markdown renderer
│       │   │   ├── editor.py      # Input editor
│       │   │   ├── sidebar.py     # Status sidebar
│       │   │   ├── tool_output.py # Tool execution display
│       │   │   └── status_bar.py  # Footer with stats
│       │   └── themes/            # Theme definitions
│       │       ├── __init__.py
│       │       └── default.py     # Default dark/light themes
│       │
│       ├── prompt/                # System prompt construction
│       │   ├── __init__.py
│       │   ├── builder.py         # Assemble system prompt from parts
│       │   └── context_files.py   # Discover AGENTS.md walking up from cwd
│       │
│       ├── config/                # Configuration
│       │   ├── __init__.py
│       │   ├── settings.py        # pydantic-settings models
│       │   └── paths.py           # App directory paths (~/.config/orch/, .workflow/)
│       │
│       └── utils/                 # Shared utilities
│           ├── __init__.py
│           ├── toml_io.py         # TOML read/write helpers
│           ├── git.py             # Git state detection (branch, status)
│           └── tokens.py          # Token estimation
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Shared fixtures
│   ├── test_agent_loop.py
│   ├── test_tools/
│   │   ├── test_read.py
│   │   ├── test_bash.py
│   │   ├── test_edit.py
│   │   └── test_write.py
│   ├── test_session.py
│   ├── test_orchestrator.py
│   └── test_config.py
│
└── resources/                     # Static resources
    └── prompts/
        └── base_system.md         # Base system prompt template
```

---

## pyproject.toml

```toml
[project]
name = "orch"
version = "0.1.0"
description = "Context-centric AI coding agent CLI"
requires-python = ">=3.12"
dependencies = [
    # CLI
    "click>=8.1",
    "rich>=13.0",

    # LLM
    "anthropic>=0.30",

    # TUI
    "textual>=0.60",

    # Data
    "pydantic>=2.7",
    "pydantic-settings>=2.0",

    # Async
    "aiofiles>=24.0",

    # Utils
    "tiktoken>=0.7",
    "orjson>=3.10",
    "tomli-w>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
]
litellm = [
    "litellm>=1.40",
]

[project.scripts]
orch = "orch.cli:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/orch"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Notes**:
- litellm is an optional dependency (install with `pip install orch[litellm]`)
- `tomli-w` needed because stdlib `tomllib` only reads TOML, can't write
- anthropic SDK is the only required LLM dependency

---

## CLI Commands

```
orch chat                    # Interactive chat (default mode)
orch ask "prompt"            # One-shot question, print response
orch init                    # Initialize .workflow/ in current project
orch plan <milestone>        # Spawn planning agent
orch research <phase>        # Spawn research agent
orch execute <phase>         # Spawn coding agent
orch validate <phase>        # Spawn validation agent
orch auto <milestone>        # Auto-execute all phases
orch quick "prompt"          # One-off task, no milestone
orch status                  # Show all work items
orch doctor                  # Audit .workflow/ integrity
orch shelve <work-id>        # Pause current work
orch resume <work-id>        # Resume paused work
orch history                 # Show completed work log
orch agents                  # List running agent panes
orch stop <work-id>          # Kill a running agent
orch focus <work-id>         # Switch to agent's pane
```

---

## Build Order & Tracking

Each step produces something runnable. Steps are grouped into milestones.

### Milestone 1: Foundation (Steps 1-4)

Goal: Talk to Claude, get a response, call a tool. No TUI yet, just CLI output.

| Step | Files | Command | You Learn | Status |
|------|-------|---------|-----------|--------|
| 1 | pyproject.toml, __init__.py, __main__.py, cli.py | `orch hello` | Python packaging, click, entry points | |
| 2 | ai/provider.py, ai/models.py | `orch ask "What is Python?"` | Anthropic SDK, async/await, API keys | |
| 3 | ai/streaming.py | `orch ask` streams tokens live | Async iterators, `async for` | |
| 4 | tools/base.py, tools/bash.py, agent/messages.py | `orch ask "List files here"` calls bash | Tool schemas, JSON Schema, pydantic | |

**Milestone 1 deliverable**: You can ask Claude questions and it can run bash commands.

---

### Milestone 2: Agent Loop (Steps 5-6)

Goal: Multi-turn interactive conversation with all core tools.

| Step | Files | Command | You Learn | Status |
|------|-------|---------|-----------|--------|
| 5 | agent/loop.py, agent/events.py | `orch chat` interactive mode | The core loop, conversation state, events | |
| 6 | tools/read.py, tools/write.py, tools/edit.py | Claude reads/writes/edits files | File I/O, pathlib, difflib | |

**Milestone 2 deliverable**: A working coding agent in the terminal. No persistence, no TUI, but functional.

---

### Milestone 3: Persistence & Context (Steps 7-9)

Goal: Conversations survive restarts. Claude knows about your project. Settings work.

| Step | Files | Command | You Learn | Status |
|------|-------|---------|-----------|--------|
| 7 | session/store.py, session/manager.py | `orch chat` remembers history | JSONL, serialization, pathlib | |
| 8 | prompt/builder.py, prompt/context_files.py | Claude reads AGENTS.md context | Prompt engineering, directory walking | |
| 9 | config/settings.py, config/paths.py, utils/toml_io.py | `~/.config/orch/settings.toml` | Pydantic-settings, TOML, env vars | |

**Milestone 3 deliverable**: A persistent, context-aware coding agent with configuration.

---

### Milestone 4: TUI (Steps 10-11)

Goal: Pretty terminal UI with streaming markdown and basic orchestrator.

| Step | Files | Command | You Learn | Status |
|------|-------|---------|-----------|--------|
| 10 | tui/components/markdown.py, tui/agent_app.py | Agent output renders as markdown | Incremental parsing, state machines, rich/textual | |
| 11 | tui/app.py, tui/components/chat.py, editor.py, status_bar.py | `orch chat` in full TUI | Textual apps, CSS layouts, widgets, reactive UI | |

**Milestone 4 deliverable**: Beautiful terminal UI for the coding agent.

---

### Milestone 5: Orchestrator (Steps 12-14)

Goal: Full orchestrator with workflow management, multiplexer integration, and multi-agent support.

| Step | Files | Command | You Learn | Status |
|------|-------|---------|-----------|--------|
| 12 | orchestrator/state.py, orchestrator/orchestrator.py, orchestrator/history.py | `orch init`, `orch quick` | State management, TOML schemas, workflow | |
| 13 | multiplexer/base.py, cmux.py, tmux.py, inline.py | `orch execute` spawns pane | Subprocess, ABC, cmux/tmux APIs | |
| 14 | orchestrator/context_builder.py, doctor.py + full TUI sidebar | `orch plan`, `orch auto`, `orch status` | Complex state, async coordination, full TUI | |

**Milestone 5 deliverable**: Full orchestrator managing agents in cmux/tmux panes.

---

## What's NOT Built Yet (Future Milestones)

| Feature | When |
|---------|------|
| Compaction (context summarization) | After Milestone 3 if context gets too long |
| litellm integration (multi-provider) | After Milestone 2 if you want non-Anthropic models |
| Extension system | After Milestone 5 |
| TUI sidebar stats (tokens, cost, context viz) | During or after Milestone 5 |
| Web UI / RPC mode | Way later |
| Image support | Way later |
| OAuth | Way later |

---

## Quick Reference: Key Concepts Per Step

| Step | Key Python Concept | Key Library |
|------|-------------------|-------------|
| 1 | Packages, modules, entry points | click |
| 2 | async/await, environment variables | anthropic |
| 3 | AsyncIterator, yield, async for | anthropic streaming |
| 4 | Pydantic models, JSON Schema | pydantic |
| 5 | while loops, match/case, queues | asyncio |
| 6 | pathlib, subprocess, difflib | stdlib |
| 7 | File I/O, JSON serialization | orjson, pathlib |
| 8 | String formatting, Path traversal | pathlib |
| 9 | Settings, TOML, type validation | pydantic-settings, tomllib |
| 10 | State machines, text parsing | rich, textual |
| 11 | Widget composition, CSS, events | textual |
| 12 | Dataclasses, file management | tomli-w, pydantic |
| 13 | Abstract classes, subprocess | ABC, subprocess |
| 14 | Async tasks, polling, full app | asyncio, textual |
