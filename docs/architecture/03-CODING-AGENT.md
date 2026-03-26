# Package: @mariozechner/pi-coding-agent — The CLI Product

## Overview

The coding-agent is the main product — an interactive CLI coding agent. It provides three modes: interactive TUI, print (single-shot), and RPC (for web-ui). The architecture is aggressively extensible with a minimal core.

**Location**: `packages/coding-agent/`
**Binary**: `pi` (compiled with Bun for 5 platforms)
**Size**: ~15,000+ lines

---

## Startup Sequence (`src/main.ts`)

### Phase 1: Package Commands (early exit)
`pi install/remove/list/config` — Package management commands exit before agent initialization.

### Phase 2: First Argument Parse
Parse known CLI flags only. Extract `--extension` paths for early loading.

### Phase 3: Resource Loading
Create `DefaultResourceLoader`, call `reload()`. Extensions loaded here can register custom providers and CLI flags.

### Phase 4: Second Argument Parse
Re-parse args with extension-registered flags now known. Two-pass design lets extensions add `--custom-flag` options.

### Phase 5: Early Checks
`--version`, `--help`, `--list-models`, `--export` all exit early.

### Phase 6: Session Preparation
Handle `--no-session`, `--session <id>`, `--fork <id>`, `--continue`, `--resume`.

### Phase 7: Model Resolution
Precedence: CLI `--model` > scoped models from `--models` > first scoped model > error.
Thinking level: CLI `--thinking` > model `:thinking` suffix > default.

### Phase 8: Mode Selection
- **RPC mode**: `--mode rpc` → stdin/stdout JSONL protocol for web-ui
- **Interactive mode**: Full TUI with chat, editor, overlays
- **Print mode**: `-p` flag or piped stdin → single-shot output

---

## Three Operating Modes

### Interactive Mode (`src/modes/interactive/`)

Full TUI with:
- Chat message display (markdown rendered)
- Multi-line editor with @file autocomplete
- Keyboard shortcuts (fully customizable)
- Slash commands (`/model`, `/tree`, `/fork`, `/compact`, `/export`, etc.)
- Model cycling (Ctrl+P)
- Thinking level cycling (Shift+Tab)
- Tool output collapse/expand (Ctrl+O, Ctrl+T)
- Session tree navigation (double-Escape)
- Image paste (Ctrl+V)
- Bash shortcuts (`!command` sends output to LLM, `!!command` runs silently)

### Print Mode (`src/modes/print-mode.ts`)

Single-shot: send prompt, get response, exit.
- `pi -p "prompt"` — text output
- `pi --mode json "prompt"` — JSON event stream
- Can continue sessions with `-c`/`--continue`

### RPC Mode (`src/modes/rpc/`)

JSONL over stdin/stdout for web-ui integration:

```typescript
// Commands:
{ type: "prompt"; text: string; images?: ImageContent[] }
{ type: "slash_command"; name: string; args?: string }
{ type: "get_session_state" }
{ type: "shutdown" }
{ type: "extension_ui_response"; id: string; ... }

// Responses:
{ type: "response"; command: string; success: boolean; data?; error? }

// Events streamed as they occur:
// conversation events, tool execution, compaction, model changes, extension UI requests
```

---

## Tool System (`src/core/tools/`)

### Default Tools (4 core tools)

| Tool | Purpose |
|------|---------|
| **read** | Read file contents (line range, regex search, byte offset) |
| **bash** | Execute shell commands (with timeout, signal) |
| **edit** | Find/replace in files (structured diff) |
| **write** | Create/overwrite files (creates parent dirs) |

### Optional Tools

| Tool | Purpose |
|------|---------|
| **grep** | Search file contents (respects .gitignore) |
| **find** | Find files by glob pattern |
| **ls** | List directory contents |

### Tool Selection

- `--tools read,bash,edit,write` (comma-separated)
- `--no-tools` disables all built-in (extensions still work)
- Extensions can register additional tools

---

## Extension System (`src/core/extensions/`)

### Extension Discovery Order

1. `~/.pi/agent/extensions/` (global)
2. `.pi/extensions/` (project-local)
3. Installed packages (npm/git)
4. CLI `--extension <path>` flags

### Extension Factory

```typescript
// Extensions must export default function:
export default function(pi: ExtensionRuntime) {
  pi.registerTool({ name: "my-tool", ... });
  pi.registerCommand("my-command", { ... });
  pi.on("tool_call", async (event, ctx) => { ... });
}
```

### Extension Capabilities

- **Tools**: Register custom tools available to the agent
- **Commands**: Register slash commands (`/mycommand`)
- **Shortcuts**: Register keyboard shortcuts
- **Handlers**: Subscribe to events (agent_start, tool_call, tool_result, etc.)
- **UI Widgets**: Set header, footer, inline widgets
- **Dialogs**: select(), confirm(), input(), notify()
- **Editor**: setEditorText(), getEditorText(), pasteToEditor()
- **Theme**: Access and modify theme
- **Flags**: Register CLI flags consumed by the extension

### Event Types

agent_start, agent_end, turn_start, turn_end, tool_call, tool_result, input, user_bash, context_event, before_agent_start, before_provider_request, session_start, session_switch, session_fork, session_tree, session_compact

### Virtual Modules (for Bun binary)

Pre-bundled packages available to extensions without installation:
- `@sinclair/typebox`, `@mariozechner/pi-agent-core`, `@mariozechner/pi-tui`
- `@mariozechner/pi-ai`, `@mariozechner/pi-ai/oauth`, `@mariozechner/pi-coding-agent`

---

## Session Management (`src/core/session-manager.ts`)

### Session File Format

JSONL (JSON Lines) with tree structure via `id/parentId`:

**Location**: `~/.pi/agent/sessions/<encoded-cwd>/session.jsonl`

### Entry Types

| Type | Purpose |
|------|---------|
| `session` | Header: version, ID, timestamp, cwd, parentSession |
| `message` | LLM message (user/assistant/toolResult) |
| `thinkingLevelChange` | When thinking level changed |
| `modelChange` | When model switched |
| `compaction` | Summarized context (summary, tokensBefore, firstKeptEntryId) |
| `branchSummary` | Summary when branching/forking |
| `custom` | Extension-specific data (NOT in LLM context) |
| `customMessage` | Extension message injected INTO LLM context |
| `label` | User bookmarks on entries |
| `sessionInfo` | Metadata (e.g., display name) |

### Tree Navigation

- `/tree` — Visual tree browser
- `/fork` — Create new session from branch point
- `--fork <id>` — Fork from CLI
- All history kept in single JSONL file; only displayed subset changes

---

## Context Compaction (`src/core/compaction/`)

### Triggers

- **Manual**: `/compact` or `/compact <instructions>`
- **Automatic threshold**: Proactive when approaching context limit
- **Overflow**: Reactive when context exceeded
- **Retry**: Auto-retry with compaction if LLM request fails

### Algorithm

1. Find cut point (oldest messages to summarize)
2. Extract context up to cut point
3. Use LLM to generate summary
4. Create CompactionEntry with summary + file tracking (readFiles, modifiedFiles)
5. Reload session with compaction replacing old messages

### Settings

```json
{
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000
  }
}
```

---

## System Prompt Construction (`src/core/system-prompt.ts`)

### Default Structure

1. Opening: "You are an expert coding assistant operating inside pi..."
2. Available tools section (filtered by selectedTools)
3. Guidelines (file exploration preference, conciseness)
4. Pi documentation references (only if read tool available)
5. Project context (AGENTS.md / CLAUDE.md files)
6. Skills section (one-line per skill)
7. Current date and working directory (always last)

### Context File Discovery

Walks up directory tree from cwd looking for `AGENTS.md` or `CLAUDE.md`. Also loads from `~/.pi/agent/`. First per-directory file wins.

### System Prompt Override

- `.pi/SYSTEM.md` (project) or `~/.pi/agent/SYSTEM.md` (global) — replaces entire default
- `.pi/APPEND_SYSTEM.md` — appends without replacing

---

## Resource Loading (`src/core/resource-loader.ts`)

### Discovery Order (each type)

| Resource | Paths Checked |
|----------|---------------|
| **Extensions** | ~/.pi/agent/extensions/, .pi/extensions/, packages, --extension |
| **Skills** | ~/.pi/agent/skills/, .pi/skills/, ~/.agents/skills/, packages, --skill |
| **Prompts** | ~/.pi/agent/prompts/, .pi/prompts/, packages, --prompt-template |
| **Themes** | ~/.pi/agent/themes/, .pi/themes/, packages, --theme |
| **Context** | ~/.pi/agent/AGENTS.md, walk up from cwd collecting AGENTS.md/CLAUDE.md |

### Hot-Reload

`/reload` reloads keybindings, extensions, skills, prompts, context files. Themes hot-reload on file change.

---

## Model Resolution (`src/core/model-resolver.ts`)

### Model Specification Formats

1. `--model <pattern>` — Fuzzy matching
2. `--provider openai --model gpt-4o` — Explicit
3. `--model openai/gpt-4o` — Canonical `provider/id`
4. `--model sonnet:high` — Pattern with thinking level suffix

### Scoped Models (`--models`)

Pattern syntax: `claude-sonnet`, `*sonnet*`, `anthropic/*`, `sonnet:high`
Used for Ctrl+P cycling in interactive mode.

### Default Models Per Provider

anthropic→claude-opus-4-6, openai→gpt-5.4, google→gemini-2.5-pro, etc.

---

## Package Management

```bash
pi install <source> [-l]    # Install (npm:, git:, https:, ssh:, local path)
pi remove <source> [-l]     # Remove
pi list                     # List installed
pi config                   # GUI for enabling/disabling
```

Packages can provide extensions, skills, prompts, and themes via `pi` key in package.json.

---

## Settings (`src/core/settings-manager.ts`)

### Locations

- **Global**: `~/.pi/agent/settings.json`
- **Project**: `.pi/settings.json` (overrides global)

### Key Settings

```json
{
  "defaultProvider": "anthropic",
  "defaultModel": "claude-opus-4-6",
  "defaultThinkingLevel": "off",
  "compaction": { "enabled": true, "reserveTokens": 16384, "keepRecentTokens": 20000 },
  "retry": { "enabled": true, "maxRetries": 3, "baseDelayMs": 2000 },
  "terminal": { "showImages": true },
  "images": { "autoResize": true },
  "steeringMode": "one-at-a-time",
  "followUpMode": "one-at-a-time",
  "theme": "dark",
  "shellPath": "/bin/bash",
  "doubleEscapeAction": "fork|tree|none"
}
```

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `PI_CODING_AGENT_DIR` | Override agent config directory (default: ~/.pi/agent) |
| `PI_OFFLINE=1` | Skip network operations |
| `PI_STARTUP_BENCHMARK=1` | Run startup profiling |
| `PI_CACHE_RETENTION=long` | Extended cache (Anthropic 1h, OpenAI 24h) |
| `PI_SHARE_VIEWER_URL` | Base URL for /share command |
| `VISUAL`, `EDITOR` | External editor for Ctrl+G |

---

## Key Quirks

1. **Two-pass arg parsing**: First discovers extensions, second includes their flags
2. **File mutation queue**: Preserves write order when tool execution is fast
3. **Output guard**: Prevents tool output from leaking into TUI/RPC
4. **Model fallback**: If saved model unavailable, falls back to first available with warning
5. **Auto-retry with compaction**: Overflow → compact → retry (up to 3 times)
6. **Image auto-resize**: Default 2000x2000 max
7. **Unicode space normalization**: Extension paths convert non-breaking spaces to regular
8. **Cwd-based session storage**: Sessions stored in `sessions/<encoded-cwd>/`
9. **Bash shortcuts**: `!cmd` sends output to LLM, `!!cmd` runs without sending
10. **Paste markers**: Large pastes (>10 lines) shown as `[paste #N +M lines]` in editor
