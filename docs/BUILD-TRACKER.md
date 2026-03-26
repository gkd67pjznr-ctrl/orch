# Orch — Build Tracker

## Milestone 1: Foundation (Steps 1-4) — COMPLETE

Goal: Talk to Claude, get a response, call a tool. CLI output only.

| Step | What | Command | Learned | Status |
|------|------|---------|---------|--------|
| 1 | Hello World CLI | `orch hello` | Python packaging, click, entry points, venv | DONE |
| 2 | Talk to Claude | `orch ask "question"` | Anthropic SDK, OAuth auth_token, subprocess, json | DONE |
| 3 | Streaming output | `orch ask` streams tokens | Generators, yield, context managers (with/as), iterators | DONE |
| 4 | Tool calling | `orch ask` calls bash | Classes, inheritance, self, **kwargs, JSON Schema, pydantic | DONE |

**Deliverable**: Can ask Claude questions, it can run bash commands. ACHIEVED.

---

## Milestone 2: Agent Loop (Steps 5-6) — COMPLETE

Goal: Multi-turn interactive conversation with all core tools.

| Step | What | Command | Learned | Status |
|------|------|---------|---------|--------|
| 5 | Agent loop | `orch chat` interactive | Nested while loops, input(), try/except, conversation history | DONE |
| 6 | File tools | Claude reads/writes/edits | pathlib, Path, dict/list comprehensions, tool registry pattern | DONE |

**Deliverable**: A working coding agent in the terminal. No persistence, no TUI, but functional. ACHIEVED.

---

## Milestone 3: Persistence & Context (Steps 7-9) — COMPLETE

Goal: Conversations survive restarts. Claude knows about your project. Settings work.

| Step | What | Command | Learned | Status |
|------|------|---------|---------|--------|
| 7 | Sessions | `orch chat -r ID` resumes | JSONL, json.dumps/loads, file append mode, click options | DONE |
| 8 | System prompt | Claude reads CLAUDE.md context | Directory tree walking, tuple unpacking, content blocks | DONE |
| 9 | Configuration | `ORCH_MODEL=x orch chat` | pydantic-settings, BaseSettings, env_prefix, env vars | DONE |

**Deliverable**: A persistent, context-aware coding agent with configuration. ACHIEVED.

---

## Milestone 4: TUI (Steps 10-11) — NOT STARTED

Goal: Pretty terminal UI with streaming markdown.

| Step | What | Command | Learned | Status |
|------|------|---------|---------|--------|
| 10 | Markdown renderer | Agent output renders as markdown | Incremental parsing, state machines, rich/textual | |
| 11 | Full TUI | `orch chat` in full TUI | Textual apps, CSS layouts, widgets, reactive UI | |

**Deliverable**: Beautiful terminal UI for the coding agent.

---

## Milestone 5: Orchestrator (Steps 12-14) — NOT STARTED

Goal: Full workflow management with cmux/tmux integration.

| Step | What | Command | Learned | Status |
|------|------|---------|---------|--------|
| 12 | Orchestrator MVP | `orch init`, `orch quick` | State management, TOML schemas, workflow | |
| 13 | Multiplexer | `orch execute` spawns pane | Subprocess, ABC, cmux/tmux APIs | |
| 14 | Full orchestrator | `orch plan`, `orch auto`, `orch status` | Complex state, async coordination, full TUI | |

**Deliverable**: Full orchestrator managing agents in cmux/tmux panes.
