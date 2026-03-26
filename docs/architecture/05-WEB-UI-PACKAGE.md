# Package: @mariozechner/pi-web-ui — Web Components for AI Chat

## Overview

Reusable web UI components for building AI chat interfaces in the browser. Uses Mini-Lit (lightweight Lit) + Tailwind CSS v4. Connects to the agent via direct API or RPC mode.

**Location**: `packages/web-ui/`
**Framework**: Mini-Lit (Lit-based web components) + Tailwind CSS v4
**Size**: ~8,000+ lines

---

## Core Components

### ChatPanel (`<pi-chat-panel>`)

High-level wrapper that combines chat interface and artifacts panel:
- Responsive: side-by-side on desktop (>800px), overlay on mobile
- `setAgent(agent, config)` wires up the full UI
- Automatic artifact reconstruction from message history

### AgentInterface (`<agent-interface>`)

The core chat UI:
- Messages area (stable, no re-render during streaming)
- Streaming message container (real-time updates via requestAnimationFrame)
- Message editor (input field with attachments)
- Stats line (token counts, costs)
- Auto-scroll with ResizeObserver detection

### MessageEditor (`<message-editor>`)

Input field with:
- Enter to send, Shift+Enter for newline, Escape to abort
- Paste image support (auto-load from clipboard)
- Drag-and-drop file support
- File validation (20MB max, 10 files max)
- Model selector, thinking level selector, abort button

---

## Message System

### Custom Message Types (via declaration merging)

```typescript
declare module "@mariozechner/pi-agent-core" {
  interface CustomAgentMessages {
    "user-with-attachments": UserMessageWithAttachments;
    artifact: ArtifactMessage;
  }
}
```

### defaultConvertToLlm

Transforms AgentMessages → LLM-compatible Messages:
- UserMessageWithAttachments → user message with image/text blocks
- ArtifactMessage → filtered out (UI-only)
- Standard messages → passed through

### Custom Message Renderers

```typescript
registerMessageRenderer('system-notification', {
  render: (msg) => html`<div class="alert">${msg.message}</div>`,
});
```

---

## Artifact System

### ArtifactsPanel (`<artifacts-panel>`)

File manager for AI-generated content with built-in tool:

```typescript
// Artifact tool schema:
{
  command: "create"|"update"|"rewrite"|"get"|"delete"|"logs",
  filename: string,
  content?: string,
  old_str?: string,  // for update
  new_str?: string,  // for update
}
```

### Artifact Types (auto-detected by extension)

| Extension | Component | Rendering |
|-----------|-----------|-----------|
| .html | HtmlArtifact | Sandboxed iframe with runtime providers |
| .svg | SvgArtifact | Preview + code view |
| .md | MarkdownArtifact | markdown-block rendering |
| .pdf | PdfArtifact | pdfjs rendering |
| .xlsx/.xls | ExcelArtifact | XLSX parsing, sheet view |
| .docx | DocxArtifact | docx-preview |
| .png/.jpg/etc | ImageArtifact | Image display |
| Others | TextArtifact | Syntax highlighted (52 languages) |

---

## Sandbox Execution System

### SandboxedIframe (`<sandbox-iframe>`)

Isolated execution environment for HTML artifacts and JavaScript REPL:
- Each execution gets unique sandboxId
- Content injected via srcdoc (CSP compliant)
- Runtime providers inject globals and handle bidirectional communication

### Runtime Message Router (singleton)

Central message routing between sandboxes and host:
```
Sandbox → postMessage({sandboxId, messageId, type, ...})
    → RUNTIME_MESSAGE_ROUTER.messageListener
    → Provider.handleMessage() or Consumer broadcast
    → respond() → postMessage({type: "runtime-response", ...})
```

### Runtime Providers

| Provider | Globals Injected | Purpose |
|----------|-----------------|---------|
| ConsoleRuntimeProvider | console.log/error/warn/info override | Capture console output |
| ArtifactsRuntimeProvider | listArtifacts, getArtifact, createOrUpdateArtifact, deleteArtifact | CRUD artifacts from sandbox |
| AttachmentsRuntimeProvider | listAttachments, readTextAttachment, readBinaryAttachment | Access user-uploaded files |
| FileDownloadRuntimeProvider | returnFile, returnFiles | Download files from sandbox |

**Key constraint**: `getRuntime()` is `.toString()`'d — must be pure, self-contained JavaScript with no external references.

---

## Tools

### JavaScript REPL (`src/tools/javascript-repl.ts`)

Executes JavaScript in sandbox, collects console output and returned files.

### Extract Document (`src/tools/extract-document.ts`)

Fetches and extracts text from PDF, DOCX, XLSX, PPTX URLs. CORS proxy support.

### Tool Renderer Registry

```typescript
registerToolRenderer("bash", new BashRenderer());
registerToolRenderer("artifacts", new ArtifactsToolRenderer());
// Custom renderers can be registered for any tool name
```

---

## Storage System

### Architecture

```
AppStorage (facade)
    ├── SettingsStore      (key-value)
    ├── ProviderKeysStore  (API keys by provider)
    ├── SessionsStore      (chat sessions with metadata)
    └── CustomProvidersStore (Ollama, LM Studio, vLLM configs)
         |
         v
    IndexedDBStorageBackend (with transactions)
```

### Session Persistence

```typescript
interface SessionData {
  id: string;
  title: string;
  model: Model;
  thinkingLevel: ThinkingLevel;
  messages: AgentMessage[];
  createdAt: string;
  lastModified: string;
}
```

---

## Design Patterns

1. **Light DOM**: `createRenderRoot() { return this; }` — no shadow DOM, shared Tailwind styles
2. **Agent as external dependency**: Components receive Agent instance, don't own it
3. **Streaming optimization**: requestAnimationFrame batching, separate stable vs streaming containers
4. **Storage abstraction**: IndexedDB default, swappable backend interface
5. **CORS proxy**: Opt-in, provider-based decision (always for zai/codex, OAuth-only for anthropic, never for local providers)
6. **i18n**: Mini-lit i18n system with `translations.de = {...}` pattern

---

## Key Quirks

1. **PersistentStorageDialog currently broken** (noted in README)
2. **HTML artifacts must use fixed dimensions** (800x600, not window.innerWidth)
3. **No persistence between REPL calls** — global scope reset on each execution
4. **Artifacts can't see each other's runtime** — read-only access only in HTML artifacts
5. **Browser extension CSP** — requires sandboxUrlProvider for strict CSP environments
