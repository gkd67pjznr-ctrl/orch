# Pi Mono - Complete Architecture Overview

## What Is Pi Mono?

Pi Mono is a **TypeScript monorepo** by Mario Zechner (GitHub: badlogic) that provides a complete stack for building AI coding agents. The main product is `pi` -- an interactive CLI coding agent similar to Claude Code, Cursor, or Aider. The name comes from the domain `pi.dev` and the brand "shittycodingagent.ai".

**Repository**: `github.com/badlogic/pi-mono`
**Current Version**: 0.62.0 (lockstep across all packages)
**License**: MIT
**Runtime**: Node.js >= 20, with Bun used for binary compilation

## Package Dependency Graph

```
pi-tui (Terminal UI primitives)
   |
   v
pi-ai (Multi-provider LLM API)
   |
   v
pi-agent-core (Agent runtime + tool execution)
   |
   v
pi-coding-agent (CLI product - the main deliverable)
   |
   +---> pi-mom (Slack bot using coding-agent)
   +---> pi-web-ui (Browser chat UI)
   +---> pi-pods (vLLM GPU deployment CLI)
```

Build order is strictly sequential: tui -> ai -> agent -> coding-agent -> mom -> web-ui -> pods.

## The 7 Packages

| Package | npm Name | Lines (approx) | Purpose |
|---------|----------|-----------------|---------|
| **tui** | @mariozechner/pi-tui | ~10,600 | Terminal UI framework with differential rendering |
| **ai** | @mariozechner/pi-ai | ~15,000+ | Unified LLM API for 20+ providers |
| **agent** | @mariozechner/pi-agent-core | ~1,900 | Agent loop with tool calling and state management |
| **coding-agent** | @mariozechner/pi-coding-agent | ~15,000+ | The CLI coding agent product |
| **mom** | @mariozechner/pi-mom | ~3,000 | Slack bot delegating to coding agent |
| **web-ui** | @mariozechner/pi-web-ui | ~8,000+ | Web components for AI chat interfaces |
| **pods** | @mariozechner/pi | ~2,000 | CLI for managing vLLM on GPU pods |

## Architecture Philosophy

1. **Minimal core, extensible shell**: The coding agent ships with just 4 tools (read, bash, edit, write). Everything else comes via extensions, skills, or packages.
2. **No forced workflows**: No MCP, no sub-agents, no plan mode, no permission dialogs built-in. Users add what they need.
3. **Provider-agnostic**: The AI layer abstracts 20+ LLM providers behind a unified streaming API. Cross-provider context handoff is a first-class feature.
4. **Extension-first**: Extensions can register tools, commands, keyboard shortcuts, UI widgets, and event handlers. The `.pi/` directory per project holds local extensions.
5. **Session-centric**: Tree-based session structure with in-place branching, forking, compaction, and export.

## Key Design Patterns

- **Lazy loading**: Provider modules loaded on first use (keeps startup fast)
- **Event-driven streaming**: All LLM responses are `AsyncIterable<AssistantMessageEvent>` streams
- **Two-pass arg parsing**: First pass discovers extensions, second pass includes extension-registered flags
- **Differential TUI rendering**: Three strategies (first render, full redraw, line-diff) with synchronized output
- **JSONL persistence**: Sessions stored as append-only JSONL with tree structure via id/parentId
- **Declaration merging**: Custom message types via TypeScript module augmentation

## For Your Python Rebuild

The key components you'd need to replicate:

1. **LLM abstraction** (packages/ai): Multi-provider streaming with tool calling, thinking/reasoning, and cross-provider message transformation
2. **Agent loop** (packages/agent): The core prompt->stream->tool_call->tool_result->stream cycle with steering/follow-up queues
3. **Session management** (packages/coding-agent): JSONL-based tree sessions with compaction
4. **TUI** (packages/tui): Differential terminal rendering -- or use an existing Python TUI library (textual, rich, prompt_toolkit)
5. **Tool system** (packages/coding-agent): read, bash, edit, write tools with the extension system
6. **Extension system** (packages/coding-agent): Plugin architecture for tools, commands, and event handlers

See the individual package documents for exhaustive details on each.
