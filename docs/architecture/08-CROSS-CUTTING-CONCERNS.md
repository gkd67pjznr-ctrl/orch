# Cross-Cutting Concerns & Patterns for Python Rebuild

## Data Flow: End-to-End Request

```
User types prompt in TUI editor
    |
    v
Interactive Mode processes input
    - Expand prompt templates (/templateName)
    - Parse skill blocks (<skill>...</skill>)
    - Handle @file references (load file contents)
    - Handle !command (run bash, inject output)
    |
    v
AgentSession.prompt(message, options)
    - Build system prompt (tools + guidelines + context files + skills)
    - Append user message to session
    - Persist to session JSONL
    |
    v
Agent.prompt(message)
    - Validate not already streaming
    - Set isStreaming = true
    - Call _runLoop(messages)
    |
    v
agentLoop (inner loop)
    |
    +---> transformContext(messages)     [optional: prune, compact, inject]
    +---> convertToLlm(messages)        [filter custom types → LLM messages]
    +---> streamSimple(model, context)  [call LLM via pi-ai]
    |         |
    |         +---> Lazy-load provider module
    |         +---> Build provider-specific request
    |         +---> HTTP stream (SSE / WebSocket)
    |         +---> Parse events → AssistantMessageEvent stream
    |
    +---> Yield events to subscribers
    |         - TUI renders streaming text
    |         - Session persists message updates
    |
    +---> If response has tool calls:
    |         |
    |         +---> prepareToolCall (validate args, beforeToolCall hook)
    |         +---> tool.execute(id, args, signal, onUpdate)
    |         |         - read: read file, return content
    |         |         - bash: spawn process, capture output
    |         |         - edit: find/replace in file
    |         |         - write: create/overwrite file
    |         +---> finalizeToolCall (afterToolCall hook)
    |         +---> Create ToolResultMessage
    |         +---> Persist tool result to session
    |         +---> Loop back to LLM with tool results
    |
    +---> Check steering queue (user interrupted)
    +---> Check follow-up queue (user queued more work)
    +---> If queues empty and no more tool calls → agent_end
```

---

## Session File Format (JSONL)

This is critical for your Python rebuild. The session format IS the persistence layer.

### File Location

`~/.pi/agent/sessions/<encoded-cwd>/session.jsonl`

Where `<encoded-cwd>` is the working directory with `/` replaced by `--`.

### Entry Structure

Every entry has: `{ type, id, parentId, timestamp }`

The `id/parentId` fields create a tree structure within a single file. This enables branching and forking without multiple files.

### Entry Types

```json
// Session header (first entry)
{"type":"session","version":3,"id":"abc123","timestamp":"2025-01-01T00:00:00Z","cwd":"/home/user/project"}

// User message
{"type":"message","id":"msg1","parentId":"abc123","timestamp":"...","message":{"role":"user","content":"Fix the bug","timestamp":1234567890}}

// Assistant message
{"type":"message","id":"msg2","parentId":"msg1","timestamp":"...","message":{"role":"assistant","content":[{"type":"text","text":"I'll fix that..."}],"api":"anthropic-messages","provider":"anthropic","model":"claude-sonnet-4-5","usage":{"input":500,"output":200,"cacheRead":0,"cacheWrite":0,"totalTokens":700,"cost":{"input":0.001,"output":0.002,"total":0.003}},"stopReason":"toolUse","timestamp":1234567891}}

// Tool result
{"type":"message","id":"msg3","parentId":"msg2","timestamp":"...","message":{"role":"toolResult","toolCallId":"tc_123","toolName":"read","content":[{"type":"text","text":"file contents..."}],"isError":false,"timestamp":1234567892}}

// Compaction (summarizes older entries)
{"type":"compaction","id":"comp1","parentId":"msg3","timestamp":"...","summary":"User asked to fix bug in auth.py...","firstKeptEntryId":"msg10","tokensBefore":50000}

// Model change
{"type":"modelChange","id":"mc1","parentId":"msg3","timestamp":"...","model":{"id":"gpt-4o","provider":"openai"}}

// Thinking level change
{"type":"thinkingLevelChange","id":"tc1","parentId":"msg3","timestamp":"...","thinkingLevel":"high"}

// Branch summary (when forking)
{"type":"branchSummary","id":"bs1","parentId":"msg3","timestamp":"...","summary":"Explored approach A..."}

// Label (bookmark)
{"type":"label","id":"lb1","parentId":"msg3","timestamp":"...","label":"working solution"}
```

### Reading a Session

To reconstruct current conversation:
1. Read all entries
2. Follow parentId chain from latest entry back to session header
3. Build messages array from message entries on that path
4. Apply compaction entries (replace older messages with summary)
5. Use latest model/thinking level from change entries

---

## Extension System Architecture

For your Python rebuild, this is the plugin system you'd replicate:

### Extension Discovery

```
~/.pi/agent/extensions/*.ts      (global)
.pi/extensions/*.ts               (project-local)
installed packages                 (npm/git)
--extension <path>                 (CLI override)
```

### Extension API Surface

```python
# Python equivalent of what extensions can do:

class Extension:
    def register_tool(self, name, description, params, execute_fn): ...
    def register_command(self, name, description, handler_fn): ...
    def on(self, event_type, handler_fn): ...  # Subscribe to events
    def register_shortcut(self, key, handler_fn): ...

    # UI operations (interactive mode only)
    def set_widget(self, key, content): ...
    def set_header(self, factory): ...
    def notify(self, message, type): ...
    def select(self, title, options): ...
    def confirm(self, title, message): ...
    def input(self, title, placeholder): ...

    # Editor operations
    def set_editor_text(self, text): ...
    def get_editor_text(self): ...

    # CLI flags
    def register_flag(self, name, description, type): ...
    def get_flag_value(self, name): ...
```

### Event Types

```python
EXTENSION_EVENTS = [
    "agent_start", "agent_end",
    "turn_start", "turn_end",
    "tool_call", "tool_result",
    "input", "user_bash",
    "context_event",
    "before_agent_start", "before_provider_request",
    "session_start", "session_switch", "session_fork",
    "session_tree", "session_compact",
]
```

---

## Tool Implementation Patterns

### Read Tool

```
Input: { path, startLine?, endLine?, pattern?, maxLines=10000, maxBytes=100KB }
Output: { content: file contents (with line numbers), details: { path, lines } }
Error: File not found, permission denied → throw
```

### Bash Tool

```
Input: { command, timeout? }
Output: { content: stdout + stderr, details: { exitCode, command } }
Error: Timeout, signal → throw with output captured so far
```

### Edit Tool

```
Input: { path, oldText, newText }
Output: { content: unified diff, details: { path, changes } }
Error: oldText not found, multiple matches → throw
```

### Write Tool

```
Input: { path, content }
Output: { content: confirmation, details: { path, bytes } }
Side effect: Creates parent directories
Error: Permission denied → throw
```

---

## Configuration Hierarchy

```
CLI flags (highest precedence)
    |
    v
Project settings (.pi/settings.json)
    |
    v
Global settings (~/.pi/agent/settings.json)
    |
    v
Defaults (lowest precedence)
```

### Key Settings Categories

- **Model**: defaultProvider, defaultModel, defaultThinkingLevel, enabledModels
- **Compaction**: enabled, reserveTokens, keepRecentTokens
- **Retry**: enabled, maxRetries, baseDelayMs, maxDelayMs
- **UI**: theme, hideThinkingBlock, doubleEscapeAction
- **Queue**: steeringMode, followUpMode
- **Shell**: shellPath, shellCommandPrefix
- **Images**: autoResize, blockImages, showImages

---

## Authentication Flow

### API Key Resolution Order

1. CLI `--api-key` flag (runtime only)
2. Environment variables (provider-specific)
3. OAuth token from `~/.pi/agent/auth.json`
4. Interactive login prompt

### auth.json Format

```json
{
  "anthropic": { "type": "oauth", "accessToken": "sk-ant-oat-...", "refreshToken": "...", "expiresAt": 1234567890 },
  "openai": { "type": "api_key", "apiKey": "sk-..." }
}
```

---

## System Prompt Construction

For your Python rebuild, the system prompt is assembled from:

1. **Base prompt**: "You are an expert coding assistant..."
2. **Tool descriptions**: Filtered to active tools, with parameter schemas
3. **Guidelines**: File exploration preference, conciseness rules
4. **Documentation references**: Pi docs (if read tool available)
5. **Context files**: All AGENTS.md/CLAUDE.md files found walking up from cwd
6. **Skills**: One-line descriptions of loaded skills
7. **Current state**: Date, working directory

### Override Mechanism

- `.pi/SYSTEM.md` → replaces entire default prompt
- `.pi/APPEND_SYSTEM.md` → appends to default prompt
- `--system-prompt "text"` → CLI override
- `--append-system-prompt "text"` → CLI append

---

## Compaction Strategy

When context approaches the model's limit:

1. **Estimate tokens**: Count current context size
2. **Find cut point**: Oldest messages that can be summarized
3. **Keep recent**: Always keep `keepRecentTokens` worth of recent messages
4. **Summarize**: Use same LLM to generate summary of older messages
5. **Track files**: Record which files were read/modified (for context)
6. **Replace**: Swap old messages with CompactionEntry containing summary
7. **Reserve**: Keep `reserveTokens` available for next response

### Auto-Compaction Triggers

- **Threshold**: Proactive when context > 80% of limit
- **Overflow**: Reactive when LLM returns context overflow error
- **Retry**: Combined with retry logic (compact then retry up to 3 times)

---

## Python Rebuild Recommendations

Based on this analysis, here's what matters most:

### Must Have (Core Loop)

1. **Multi-provider LLM client** with streaming (Python: litellm, or custom)
2. **Agent loop** with tool execution (sequential + parallel)
3. **JSONL session persistence** with tree structure
4. **4 core tools**: read, bash, edit, write
5. **System prompt builder** with context file discovery
6. **Compaction** for long conversations

### Should Have (Usability)

7. **Extension/plugin system** for custom tools and commands
8. **Model switching** mid-conversation with message transformation
9. **Steering and follow-up queues** for async user input
10. **Settings hierarchy** (global + project)
11. **Slash commands** for common operations

### Nice to Have (Polish)

12. **TUI with differential rendering** (Python: textual, prompt_toolkit)
13. **RPC mode** for web UI integration
14. **Package management** for extensions
15. **Session tree navigation** and forking
16. **Image support** (paste, display)

### Python Library Suggestions

| Pi Component | Python Equivalent |
|--------------|-------------------|
| pi-ai (LLM abstraction) | litellm, or custom with httpx/aiohttp |
| pi-agent-core (agent loop) | Custom (relatively small) |
| pi-tui (terminal UI) | textual, rich, prompt_toolkit |
| TypeBox (schemas) | pydantic |
| Biome (formatting) | ruff |
| Vitest (testing) | pytest |
| JSONL persistence | Custom (simple) |
| TypeScript declaration merging | Python Protocol/ABC or plugin registries |
