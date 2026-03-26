# Architecture Design Decisions — Conversation Log

## Context

This document records the architectural decision-making process for rebuilding pi-mono's coding agent CLI in Python. The goal is both a learning project and a functional rebuild with a different philosophy: **context-centric rather than tool-centric**.

---

## Decision 1: Project Structure

**Decided**: Single package with internal modules (not monorepo)

Pi uses a 7-package npm monorepo because each package is independently published. We're building one product. Internal modules (ai/, agent/, tui/, tools/) stay in one package. Avoids all the monorepo overhead (strict build order, lockstep versioning, sync-versions.js).

## Decision 2: CLI Framework

**Decided**: click

Typer is built on click and infers behavior from type annotations (less boilerplate). Click is more explicit — you see every piece. For a learning project, explicit wins. Can always switch to typer later since typer IS click underneath.

## Decision 3: LLM Provider Layer

**Decided**: Hybrid (litellm + direct anthropic SDK)

litellm for unified interface across 100+ providers. Direct anthropic SDK for Anthropic-specific features (extended thinking, prompt caching, tool_choice). Thin wrapper tries direct SDK first, falls back to litellm.

## Decision 4: Agent Loop

**Decided**: Custom, thin

The agent loop is the heart — write it yourself for learning. Pi's loop is ~1,900 lines with ~800 lines of hook infrastructure. The actual loop logic is ~400 lines. Our thin Python loop: ~200-300 lines. Start with simple function parameters for extensibility, not a hook framework.

Key insight: Pi's loop is generic because it serves multiple agent types (coding agent, Slack bot). We're building one thing. Put coding-specific logic directly in the loop and tools.

### Thin Loop vs Pi's Full Loop

Pi has 14+ hook points (transformContext, convertToLlm, beforeToolCall, afterToolCall, getSteeringMessages, getFollowUpMessages, getApiKey, plus 7+ extension events). Analysis of each:

- **transformContext**: Used for compaction. Move outside the loop instead.
- **convertToLlm**: Used for custom message type filtering. We don't have custom types.
- **beforeToolCall**: Used for permission prompts. Put safety checks in the tool itself.
- **afterToolCall**: Used for result modification. Put in the tool's execute function.
- **steering/follow-up queues**: Important for UX (user interrupts). Implement as asyncio.Queue, not hooks.
- **parallel tool execution**: Start sequential, add parallel later (20-line change).

Strategy: Start thin, add parameters when real need arises. `before_tool_call: Callable | None = None` is not a framework — it's a function parameter.

## Decision 5: TUI Framework

**Decided**: textual + rich

Textual uses rich internally. Both come together.

## Decision 6: Session Persistence

**Decided**: JSONL (start simple)

Considered SQLite (better querying, transactions, crash-safe) vs JSONL (simpler, human-readable, git-friendly, zero deps). JSONL lets us focus on the agent loop first. Can add SQLite metadata index later for session listing.

## Decision 7: Tool Validation

**Decided**: pydantic

Python's equivalent of TypeBox. Validates tool arguments with type-safe schemas.

## Decision 8: Extension/Plugin System

**Decided**: importlib + directory scanning (later, not MVP)

Three options analyzed:
- pluggy (hook-based, powers pytest) — overkill for 5-10 hook points
- importlib + directory scanning — closest to pi's model, most educational
- entry points via pyproject.toml — requires extensions be installed packages

importlib is simplest, most transparent, and works for local extensions (drop a .py file in a directory).

## Decision 9: Async Strategy

**Decided**: asyncio throughout

LLM streaming and tool execution are naturally async.

## Decision 10: Configuration

**Decided**: TOML + pydantic-settings

TOML supports comments (JSON doesn't), pydantic-settings gives type validation, env var override, and default values for free. Supports global + project-level config hierarchy.

## Decision 11: Markdown Rendering

**Decided**: Custom streaming renderer from the start

rich.markdown re-parses entire string each render. With streaming LLM responses growing token by token across multiple sessions, this is obviously bad from the start. Build incremental markdown renderer early.

## Decision 12: System Prompt & Architecture Philosophy

**Decided**: Minimal prompt + rich context engine

### Key Insight: Context Quality >>> Behavior Constraints

Pi invests heavily in constraining LLM behavior (heavy system prompts, rigid tool schemas, 14+ hooks for behavior modification). Our thesis: the real value is in **enriching the LLM's context**, not constraining its behavior.

**High value (context enrichment)**:
- Session persistence (Claude can't remember natively)
- Compaction (smart summarization of old context)
- Project context files (AGENTS.md, codebase knowledge)
- File/dependency tracking
- Git state awareness

**Debatable value (behavior shaping)**:
- Heavy system prompts (eat context window, may conflict with training)
- Rigid tool schemas (prevent Claude from taking correct shortcuts)
- Forced workflows (Claude already tends to read before editing)

**Our architecture emphasis**:
```
Context Engine (rich) → Agent Loop (thin) → Tool Execution (minimal) → LLM
   ├── Session history with smart retrieval
   ├── Project knowledge base
   ├── File dependency tracking
   ├── Git state awareness
   └── Domain-aware compaction
```

---

## Final Decision Table

| # | Decision | Pick | Rationale |
|---|----------|------|-----------|
| 1 | Structure | Single package | One product, not a framework |
| 2 | CLI | click | Explicit > magic for learning |
| 3 | LLM | Hybrid litellm + anthropic | Best of both worlds |
| 4 | Agent loop | Custom, thin (~200-300 lines) | Learn by building, add hooks when needed |
| 5 | TUI | textual + rich | Rich comes with textual |
| 6 | Sessions | JSONL | Simple first, SQLite metadata later |
| 7 | Validation | pydantic | Python's TypeBox |
| 8 | Extensions | importlib (Phase 3) | Not MVP |
| 9 | Async | asyncio | Natural fit for streaming |
| 10 | Config | TOML + pydantic-settings | Type-safe, comments, env var override |
| 11 | Markdown | Custom streaming renderer | Avoid re-parse per token from day 1 |
| 12 | System prompt | Minimal + rich context | Context quality over behavior constraints |

---

## Decision 13: Workflow Orchestration Architecture

**Decided**: Hybrid (Approach C) — Programmatic skeleton, LLM flesh

### Three Approaches Analyzed

**Approach A — Skills calling skills**: Skills are markdown prompts. A skill "calls" another by outputting trigger text. LLM orchestrates.
- Pro: Dead simple, user-editable markdown, no code needed
- Con: LLM is unreliable as orchestrator. Skips steps, hallucinates completion, loses track after compaction.

**Approach B — Direct agent loop injection**: Python code calls agent.prompt() in sequence with restricted tool sets per phase.
- Pro: Hard guarantees on execution order, programmatic state tracking, easy debugging
- Con: Rigid, plan parsing fragile, fights LLM's strength (adapting, improvising)

**Approach C — Hybrid (chosen)**: Python controls WHAT happens and WHEN. LLM controls HOW each step is done.
- Orchestrator writes context (ACTIVE.toml) before agent starts
- Agent reads ACTIVE.toml, does work, writes code
- Orchestrator updates tracking after agent finishes
- Agent never updates tracking files — separation of concerns

### Key Principle: Agent Context Is Precious

Every tracking file the agent reads/writes is context NOT spent on understanding code. The orchestrator is cheap (Python, infinite "context", never hallucinates). The agent's context window is expensive.

### Separation of Concerns

| Responsibility | Who Does It |
|---------------|-------------|
| What phase to work on next | Orchestrator (Python) |
| Writing ACTIVE.toml context | Orchestrator |
| Understanding the codebase | Agent (LLM) |
| Writing/editing code | Agent |
| Running tests | Agent |
| Recording completion to history/ | Orchestrator |
| Aggregating project status | Orchestrator |
| Doctor/audit checks | Orchestrator (pure Python, no LLM) |

### What GSD Does That We Don't Need

| GSD Feature | Why We Cut It |
|------------|---------------|
| Nested tracking dirs per phase | ACTIVE.toml + history/ covers it |
| Agents updating tracking files | Orchestrator handles all tracking |
| STATE.md per phase | ACTIVE.toml is the only agent-facing state |
| DECISIONS.md + KNOWLEDGE.md per phase | Embedded in ACTIVE.toml context and history summaries |
| Doctor that uses LLM to audit | Doctor is pure Python (deterministic, fast) |
| Skills calling skills | Orchestrator calls agent loop directly |
| Phase directory trees | Flat history/ with timestamps |

### Workflow Commands Map To Orchestrator Calls

Each CLI command (plan-milestone, research-phase, execute-phase, validate-phase, auto-mode) calls the orchestrator, which:
1. Writes ACTIVE.toml with focused context for the agent
2. Calls agent.prompt() with a simple instruction
3. Records results to history/
4. Updates tracking

Auto-mode = orchestrator loops through phases, calling agent per phase, checking validation between phases.

Multi-terminal subagents = orchestrator spawns separate agent loops in tmux panes, monitors via state files.

---

## Decision 14: Workflow State Architecture

**Decided**: Single ACTIVE.toml + shelving for context switching + process-level parallelism

### Analysis: Do We Need Multiple Active Items?

Concurrency scenarios analyzed:
- Two milestones active simultaneously → User SWITCHES between them, not concurrent. Need fast switching (shelve/resume).
- Research in parallel with execution → Process-level: two separate agent processes, each reads its own copy of ACTIVE.toml.
- Doctor running alongside coding → Doctor is pure Python, doesn't use ACTIVE.toml or the agent.
- Ad-hoc quick fixes → Context switch: shelve current → quick fix → restore.

**Conclusion**: Single ACTIVE.toml is sufficient. Concurrency is at the process level (multiple agent processes), not the file level. Shelving handles context switching.

### File Structure

```
.workflow/
├── PROJECT.toml       # Project goals, milestones (user-maintained)
├── PLAN.toml          # Current milestone phases (agent writes once, orchestrator manages)
├── ACTIVE.toml        # What agent works on NOW (orchestrator writes before each agent run)
├── registry.toml      # All work items across project (orchestrator maintains)
├── history/           # Completed work summaries (append-only markdown)
├── completions/       # Agent completion markers (transient, orchestrator processes)
├── sessions/          # Agent session JSONL files
└── shelved/           # Paused ACTIVE.toml snapshots for context switching
```

### Key Principle: Depth Doesn't Improve Agent Output

6 nesting levels (Project→Milestone→Task→Plan→Phase→Step) = 6 files loaded, ~20KB context, most irrelevant.
Our approach: 1 file (ACTIVE.toml), ~1KB, 100% relevant.
The orchestrator distills history/ into focused ACTIVE.toml context. Agent doesn't navigate — orchestrator curates.

---

## Decision 15: Orchestrator + Multi-Terminal Agent Architecture

**Decided**: Orchestrator runs in main pane, spawns agents in separate cmux/tmux panes

### Primary: cmux Integration

cmux (manaflow-ai/cmux) is a Ghostty-based macOS terminal built specifically for AI coding agents. Features:
- Socket API for programmatic pane control (new-pane, focus-pane, list-panes)
- Native notification system (OSC 9/99/777 escape sequences + `cmux notify` CLI)
- Vertical tabs showing git branch, PR status, working directory, latest notification
- Notification rings around panes, unread badges in sidebar, macOS desktop notifications

### Fallback Chain

1. cmux (primary) — socket API + native notifications
2. tmux (fallback) — split-window + BEL character notifications
3. inline (no multiplexer) — sequential execution in same terminal

### Architecture

- Orchestrator = conversational TUI in main pane. Parses commands, manages state, spawns agents.
- Each agent = separate Python process in its own pane with its own TUI showing streaming output.
- Multiplexer notifications alert user when agents need attention or complete.
- Abstract multiplexer interface: `create_pane`, `kill_pane`, `notify`, `list_panes`, `focus_pane`

### Agent Lifecycle

1. User gives command in orchestrator ("execute auth-2")
2. Orchestrator writes ACTIVE.toml with focused context
3. Orchestrator spawns `python -m gsd agent --work-id auth-2` in new pane
4. Agent reads ACTIVE.toml, does work, writes code
5. Agent writes completion marker to .workflow/completions/
6. Agent sends notification via multiplexer
7. Orchestrator detects completion, records to history/, updates registry

### Agent Independence

Each agent:
- Has its own process, session file, context window
- Reads ACTIVE.toml once at start (orchestrator wrote it fresh)
- Never updates tracking files (only writes code and completion marker)
- Can request user input via its own TUI (notification alerts user to switch pane)

### CLI Commands

Project: init
Workflow: plan, research, execute, validate, auto, quick
State: status, doctor, shelve, resume, history
Agents: agents (list), stop, focus

### Auto Mode

Orchestrator loops through plan phases: research → execute → validate per phase.
Stops on validation failure. Supports --parallel flag for concurrent agent limit.

---

## Decision 16: TUI Layout

### Orchestrator TUI (main pane)

Sidebar (collapsible): active agents, their status, token usage
Main area: command input + orchestrator responses
Sub-pages: stats view (token usage, estimated cost, context size visualization per agent)

Decision: Start with just input + chat display. Add sidebar and sub-pages incrementally.
Future discussion: Whether orchestrator should accept natural language (LLM interprets) or just CLI commands. Start with CLI commands.

### Agent TUI (spawned panes)

Header: agent name, model, token count
Main area: streaming markdown output, tool execution display
Footer: status (working, needs input, done)
Input: only shown when agent needs user response

Decision: Simpler than orchestrator. Primarily read-only streaming display.

---

## Decision 17: Context Building Strategy

For building ACTIVE.toml context from history:

Phase 1 (MVP): Load all history entries for the current milestone. Simple and correct.
Phase 2: Keyword extraction from current phase description, grep history for matches.
Phase 3 (maybe never): Embeddings/vector search for relevance scoring.

History entries must be concise (~20-30 lines each) for keyword grep to work well.
Orchestrator writes ACTIVE.toml fresh before each agent spawn — agent gets pre-curated context.

---

## Decision 18: Project Name

**Decided**: `orch`

Short for orchestrator. 4 letters, fast to type, not taken on PyPI. CLI command: `orch`.

---

## Decision 19: Project Skeleton & Build Order

Full skeleton documented in docs/architecture/10-PROJECT-SKELETON.md

5 milestones, 14 steps. Each step produces something runnable.

### Milestone 1: Foundation (Steps 1-4)
Talk to Claude, get a response, call a tool. CLI output only.
1. Hello World CLI — `orch hello` (packaging, click)
2. Talk to Claude — `orch ask "question"` (anthropic SDK, async)
3. Streaming output — tokens stream live (async iterators)
4. Tool calling — Claude calls bash tool (pydantic, JSON Schema)

### Milestone 2: Agent Loop (Steps 5-6)
Multi-turn interactive conversation with all core tools.
5. Agent loop — `orch chat` interactive mode (the core loop)
6. All core tools — read, write, edit (file I/O, pathlib, difflib)

### Milestone 3: Persistence & Context (Steps 7-9)
Sessions survive restarts. Claude knows your project.
7. Sessions — JSONL persistence (serialization)
8. System prompt — AGENTS.md context discovery (prompt engineering)
9. Configuration — TOML settings (pydantic-settings)

### Milestone 4: TUI (Steps 10-11)
Beautiful terminal UI with streaming markdown.
10. Custom markdown renderer (incremental parsing, state machines)
11. Full TUI — textual app with chat, editor, status bar

### Milestone 5: Orchestrator (Steps 12-14)
Full workflow management with cmux/tmux integration.
12. Orchestrator MVP — ACTIVE.toml, init, quick (state management)
13. Multiplexer — cmux/tmux pane spawning (subprocess, ABC)
14. Full orchestrator — plan, auto, history, shelving, doctor, TUI sidebar

User codes. Claude guides step by step. User is new to coding.

---

## Open Questions

- Edit tool approach (find/replace vs unified diff vs line-based)
- Incremental markdown parsing strategy (mistune tokenizer vs custom state machine)
- Whether orchestrator should also be an LLM chat interface or pure CLI commands
- How agent requests user input (custom prompt? textual Input widget? simple stdin?)
- Testing strategy for orchestrator + agent integration
- How to handle agent crashes mid-work (recovery from completion markers)
