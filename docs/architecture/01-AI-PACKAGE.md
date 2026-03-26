# Package: @mariozechner/pi-ai — Unified Multi-Provider LLM API

## Overview

The `ai` package is the foundational LLM abstraction layer. It provides a single streaming API that works across 20+ providers (Anthropic, OpenAI, Google, Mistral, Bedrock, etc.) with automatic model discovery, tool calling, thinking/reasoning support, token tracking, cost calculation, and cross-provider message transformation.

**Location**: `packages/ai/`
**Version**: 0.62.0
**Entry**: `./dist/index.js`
**Size**: ~15,000+ lines of TypeScript

---

## Core Type System (`src/types.ts`)

### API Identifiers (KnownApi)

Each provider uses one of these wire protocol styles:

| Api ID | Description | Providers Using It |
|--------|-------------|--------------------|
| `openai-completions` | OpenAI ChatCompletions | OpenAI, Groq, xAI, Cerebras, OpenRouter, many compatibles |
| `openai-responses` | OpenAI Responses API | OpenAI (o1/o3/gpt-5.x models) |
| `azure-openai-responses` | Azure wrapper for Responses | Azure OpenAI |
| `openai-codex-responses` | OpenAI Codex (Copilot) | GitHub Copilot, OpenAI Codex |
| `anthropic-messages` | Anthropic Messages API | Anthropic, GitHub Copilot (Claude) |
| `bedrock-converse-stream` | AWS Bedrock Converse | Amazon Bedrock |
| `google-generative-ai` | Google Generative AI | Google Gemini |
| `google-gemini-cli` | Cloud Code Assist | Google Gemini CLI, Antigravity |
| `google-vertex` | Vertex AI | Google Vertex |
| `mistral-conversations` | Mistral Chat API | Mistral |

### Known Providers (20+)

amazon-bedrock, anthropic, google, google-gemini-cli, google-antigravity, google-vertex, openai, azure-openai-responses, openai-codex, github-copilot, xai, groq, cerebras, openrouter, vercel-ai-gateway, zai, mistral, minimax, minimax-cn, huggingface, opencode, opencode-go, kimi-coding

### Message Types

**UserMessage**: `{ role: "user", content: string | (TextContent | ImageContent)[], timestamp }`

**AssistantMessage**: `{ role: "assistant", content: (TextContent | ThinkingContent | ToolCall)[], api, provider, model, responseId?, usage, stopReason, errorMessage?, timestamp }`

**ToolResultMessage**: `{ role: "toolResult", toolCallId, toolName, content: (TextContent | ImageContent)[], details?, isError, timestamp }`

### Content Types

- **TextContent**: `{ type: "text", text, textSignature? }` — textSignature is OpenAI Responses replay ID
- **ThinkingContent**: `{ type: "thinking", thinking, thinkingSignature?, redacted? }` — reasoning blocks
- **ImageContent**: `{ type: "image", data (base64), mimeType }`
- **ToolCall**: `{ type: "toolCall", id, name, arguments, thoughtSignature? }` — Google Gemini opaque context

### Model Interface

```typescript
interface Model<TApi> {
  id: string;              // e.g., "claude-sonnet-4-5-20250514"
  name: string;            // e.g., "Claude Sonnet 4.5"
  api: TApi;               // Wire protocol
  provider: Provider;      // Provider name
  baseUrl: string;         // API endpoint
  reasoning: boolean;      // Supports thinking
  input: ("text"|"image")[];
  cost: { input, output, cacheRead, cacheWrite };  // $/million tokens
  contextWindow: number;   // Max context
  maxTokens: number;       // Max generation
  headers?: Record<string, string>;
  compat?: OpenAICompletionsCompat | OpenAIResponsesCompat;  // Provider quirks
}
```

### Usage Tracking

```typescript
interface Usage {
  input: number;
  output: number;
  cacheRead: number;
  cacheWrite: number;
  totalTokens: number;
  cost: { input, output, cacheRead, cacheWrite, total };  // Dollars
}
```

### Thinking Levels

`"minimal" | "low" | "medium" | "high" | "xhigh"`

Default token budgets: minimal=1024, low=2048, medium=8192, high=16384. xhigh only supported by specific models (GPT-5.2+, Opus-4.6).

---

## Streaming Architecture (`src/stream.ts`)

### Four Entry Points

| Function | Options Type | Use Case |
|----------|-------------|----------|
| `stream()` | ProviderStreamOptions | Full control with provider-specific options |
| `complete()` | ProviderStreamOptions | Same but awaits final message |
| `streamSimple()` | SimpleStreamOptions | Unified reasoning interface (recommended) |
| `completeSimple()` | SimpleStreamOptions | Same but awaits final message |

### Event Protocol (AssistantMessageEvent)

Every event carries a `partial: AssistantMessage` reflecting accumulated state:

```
start                    → Stream begins, initial empty message
text_start(idx)          → New text block at contentIndex
text_delta(idx, delta)   → Append delta to text block
text_end(idx, content)   → Text block complete
thinking_start(idx)      → New thinking block
thinking_delta(idx, d)   → Append to thinking
thinking_end(idx, c)     → Thinking block complete
toolcall_start(idx)      → New tool call block
toolcall_delta(idx, d)   → Partial JSON argument delta
toolcall_end(idx, tc)    → Tool call complete with parsed args
done(reason, message)    → Stream complete ("stop"|"length"|"toolUse")
error(reason, message)   → Stream failed ("error"|"aborted")
```

### AssistantMessageEventStream

Extends `EventStream<AssistantMessageEvent, AssistantMessage>` — an async iterable queue:
- Provider pushes events synchronously
- Consumer iterates with `for await (const event of stream)`
- Final message via `await stream.result()`

---

## Provider Registration & Lazy Loading

### API Registry (`src/api-registry.ts`)

```typescript
registerApiProvider({ api, stream, streamSimple })
getApiProvider(api)
getApiProviders()
unregisterApiProviders(sourceId)
```

### Lazy Loading Pattern (`src/providers/register-builtins.ts`)

Providers are NOT imported at startup. Instead, lazy wrappers defer the `import()` until first use:

```typescript
let modulePromise: Promise<Module> | undefined;
function loadModule() {
  modulePromise ||= import("./anthropic.js");
  return modulePromise;
}

// createLazyStream wraps this into a synchronous stream creation
// that starts async forwarding internally
```

This keeps startup fast — only the provider you actually use gets loaded.

---

## Provider Implementations

### Anthropic (`src/providers/anthropic.ts`, ~905 lines)

- **API**: anthropic-messages (Anthropic Messages API)
- **Thinking**: Adaptive effort for Opus-4.6/Sonnet-4.6 ("low"|"medium"|"high"|"max"); Budget-based for older models
- **Tool calling**: Full support with `tool_choice` (auto/any/none/specific)
- **Cache**: Ephemeral cache with 1h TTL on api.anthropic.com + long retention
- **OAuth**: Detects `sk-ant-oat` prefix, disables fine-grained streaming beta
- **Quirk - Claude Code Stealth**: Tool names normalized to exact CC canonical casing (Read, Write, Edit, Bash) for OAuth tokens
- **Streaming**: Uses @anthropic-ai/sdk with message_start, content_block_start/delta/stop, message_delta events

### OpenAI Completions (`src/providers/openai-completions.ts`)

- **API**: openai-completions (ChatCompletions API)
- **Thinking**: `reasoning_effort` parameter (minimal/low/medium/high/xhigh)
- **Compatibility System**: `OpenAICompletionsCompat` object auto-detects provider capabilities from baseUrl:
  - `supportsStore`, `supportsDeveloperRole`, `supportsReasoningEffort`
  - `maxTokensField` ("max_completion_tokens" vs "max_tokens")
  - `requiresToolResultName`, `requiresAssistantAfterToolResult`
  - `thinkingFormat` ("openai"|"openrouter"|"zai"|"qwen"|"qwen-chat-template")
- **Provider detection**: api.openai.com (full features), api.openrouter.ai (custom routing), api.vercel.com (gateway), others (generic compat)
- **Tool call IDs**: Normalized via shortHash for cross-provider compat

### OpenAI Responses (`src/providers/openai-responses.ts`)

- **API**: openai-responses (new Responses API for o1/o3/gpt-5.x)
- **Tool call IDs**: Pipe-separated format `{call_id}|{item_id}` where item_id can be 400+ chars base64
- **Text Signatures**: V1 format `{ v: 1, id: string, phase?: "commentary"|"final_answer" }` for replay
- **Cross-provider normalization**: Only openai/openai-codex/opencode preserve pipe format

### Google Generative AI (`src/providers/google.ts`)

- **API**: google-generative-ai
- **SDK**: @google/genai
- **Thinking**: `{ enabled, budgetTokens?, level? }` per GoogleThinkingLevel
- **Thought signatures**: Opaque base64 strings, validated with `/^[A-Za-z0-9+/]+={0,2}$/`
- **Sentinel**: `skip_thought_signature_validator` for Gemini 3 unsigned function calls
- **Tool call IDs**: Required for claude-* and gpt-oss-* models running on Gemini
- **Multimodal function responses**: Gemini 3+ supports images in functionResponse parts

### Google Vertex AI (`src/providers/google-vertex.ts`)

- **API**: google-vertex (same SDK, different auth)
- **Auth**: GOOGLE_CLOUD_API_KEY, Application Default Credentials (ADC), or project/location combo
- **Quirk**: ADC credential check cached once in browser, retries until fs ready in Node

### Google Gemini CLI / Antigravity (`src/providers/google-gemini-cli.ts`)

- **API**: google-gemini-cli
- **Endpoints**: cloudcode-pa.googleapis.com (prod), daily/autopush sandbox
- **Retry logic**: MAX_RETRIES=3, extracts delay from headers (Retry-After, x-ratelimit-reset) and body ("Your quota will reset after 39s")
- **Empty stream retries**: MAX_EMPTY_STREAM_RETRIES=2 for silent failures

### Mistral (`src/providers/mistral.ts`)

- **API**: mistral-conversations
- **SDK**: @mistralai/mistralai (1.14.1)
- **Tool call IDs**: 9-char max, counter-based fallback if normalization fails
- **Reasoning**: `promptMode: "reasoning"` for reasoning models
- **Error truncation**: MAX_MISTRAL_ERROR_BODY_CHARS=4000

### Amazon Bedrock (`src/providers/amazon-bedrock.ts`)

- **API**: bedrock-converse-stream (AWS Bedrock Converse)
- **SDK**: @aws-sdk/client-bedrock-runtime
- **Auth chain**: AWS_PROFILE, AccessKey+SecretKey, Bearer token, ECS credentials, IRSA
- **Cache**: CachePointType.EPHEMERAL with CacheTTL
- **Thinking**: Budget-based with level mapping
- **Request metadata**: AWS cost allocation tags (50 max)
- **Quirk**: `setBedrockProviderModule()` allows injecting custom implementation

---

## Cross-Provider Message Transformation (`src/providers/transform-messages.ts`)

### Purpose

When switching models mid-conversation (e.g., Claude -> GPT-4o -> Gemini), messages must be normalized.

### Two-Pass Algorithm

**Pass 1 — Per-message transformation**:
- Drop error/aborted assistant messages entirely
- Thinking blocks: Keep if same model + signature; convert to text if different model; drop if empty/redacted
- Tool calls: Drop thoughtSignature if cross-model; normalize IDs per target provider
- Text: Copy with optional signature handling

**Pass 2 — Orphan tool call repair**:
- Track pending tool calls after each assistant message
- When user message interrupts or next assistant arrives without results, insert synthetic error tool results: `{ isError: true, content: "No result provided" }`

### Tool Call ID Normalization Per Provider

| Provider | ID Format | Normalization |
|----------|-----------|---------------|
| Anthropic | `[a-zA-Z0-9_-]{1,64}` | Direct (already valid) |
| Google | Same as Anthropic | Validate charset |
| OpenAI Completions | Variable length | shortHash for cross-provider |
| OpenAI Responses | `{call_id}\|{item_id}` (400+ chars) | Pipe-split + normalize parts |
| Mistral | 9-char max | Truncate + counter fallback |
| Bedrock | Variable | Depends on underlying model |

---

## Environment & API Key Resolution (`src/env-api-keys.ts`)

`getEnvApiKey(provider)` resolves API keys from environment variables:

| Provider | Env Vars (in precedence order) |
|----------|-------------------------------|
| anthropic | ANTHROPIC_OAUTH_TOKEN, ANTHROPIC_API_KEY |
| openai | OPENAI_API_KEY |
| google | GEMINI_API_KEY |
| google-vertex | GOOGLE_CLOUD_API_KEY, or ADC detection (`"<authenticated>"` sentinel) |
| amazon-bedrock | AWS_PROFILE, AWS_ACCESS_KEY_ID+SECRET, AWS_BEARER_TOKEN_BEDROCK, ECS/IRSA (`"<authenticated>"` sentinel) |
| github-copilot | COPILOT_GITHUB_TOKEN, GH_TOKEN, GITHUB_TOKEN |
| groq | GROQ_API_KEY |
| xai | XAI_API_KEY |
| mistral | MISTRAL_API_KEY |

Dynamic Node.js module loading (fs, os, path) avoids breaking browser/Vite builds.

---

## Model Registry (`src/models.ts`, `src/models.generated.ts`)

### Functions

- `getModel(provider, modelId)` — Lookup specific model
- `getProviders()` — List all known providers
- `getModels(provider)` — List all models for a provider
- `calculateCost(model, usage)` — Compute dollar costs
- `supportsXhigh(model)` — Check xhigh thinking support
- `modelsAreEqual(a, b)` — Compare models

### Generated Models

Auto-generated by `scripts/generate-models.ts`. Contains full Model definitions for every provider with costs, context windows, and capabilities.

---

## Utilities

### JSON Streaming Parser (`src/utils/json-parse.ts`)
`parseStreamingJson(partialJson)` — Tries JSON.parse first, falls back to `partial-json` library for incomplete tool call arguments.

### Unicode Sanitization (`src/utils/sanitize-unicode.ts`)
`sanitizeSurrogates(text)` — Removes unpaired UTF-16 surrogates that break JSON serialization.

### Context Overflow Detection (`src/utils/overflow.ts`)
`isContextOverflow(message, contextWindow?)` — Provider-specific pattern matching on error messages to detect context exceeded.

### Tool Validation (`src/utils/validation.ts`)
`validateToolCall(tools, toolCall)` / `validateToolArguments(tool, toolCall)` — AJV-based JSON Schema validation of tool arguments.

### Fast Hashing (`src/utils/hash.ts`)
`shortHash(str)` — MurmurHash-like, outputs base-36 string. Used to shorten 400+ char OpenAI Responses IDs.

### TypeBox Enum Helper (`src/utils/typebox-helpers.ts`)
`StringEnum(values)` — Creates `{ type: "string", enum: [...] }` schema compatible with Google APIs (which don't support anyOf/const).

---

## OAuth System (`src/utils/oauth/`)

OAuth providers for:
- Anthropic (Claude Pro/Max)
- GitHub Copilot (browser + code flow)
- Google Antigravity
- Google Gemini CLI (OIDC)
- OpenAI Codex

CLI command: `pi-ai login [provider]`

---

## Key Quirks Summary

1. **Anthropic Claude Code Stealth**: OAuth tokens trigger tool name normalization to CC canonical casing
2. **Thinking budget allocation**: Budget comes from maxTokens; ensures minimum 1024 output tokens remain
3. **Empty thinking blocks dropped**: Both thinking and text must have content
4. **Redacted thinking**: Encrypted by provider, only replayable by same model
5. **Google thought signatures**: Must be valid base64, sentinel for unsigned Gemini 3 calls
6. **Opus-4.6/Sonnet-4.6 adaptive thinking**: Ignores budget, uses effort levels instead
7. **OpenAI Responses pipe IDs**: Only preserved for openai/openai-codex/opencode providers
8. **Vertex ADC caching**: Once in browser (definitive), retries in Node until fs ready
9. **Cache retention**: Provider-specific (Anthropic 1h, OpenAI 24h, others may ignore)
10. **Overflow detection unreliable**: z.ai sometimes silent, Ollama silently truncates
