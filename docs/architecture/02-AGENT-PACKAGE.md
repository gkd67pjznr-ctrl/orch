# Package: @mariozechner/pi-agent-core — Agent Runtime

## Overview

The `agent` package provides the core agent loop: the cycle of prompting an LLM, streaming the response, executing tool calls, and feeding results back. It's a clean abstraction with ~1,900 lines that sits between the AI layer and the coding-agent UI.

**Location**: `packages/agent/`
**Size**: ~1,900 lines across 4 source files

---

## Architecture

```
Application (coding-agent, mom, web-ui)
    |
    v
Agent class (high-level, stateful)
    |
    v
agentLoop / agentLoopContinue (low-level, functional)
    |
    v
streamAssistantResponse (LLM call)
    |
    +---> transformContext (optional pruning/injection)
    +---> convertToLlm (AgentMessage -> Message)
    +---> streamFn (pi-ai streaming)
    |
    v
executeToolCalls (sequential or parallel)
    |
    +---> prepareToolCall (validate + beforeToolCall hook)
    +---> tool.execute() (actual work)
    +---> finalizeToolCall (afterToolCall hook)
```

---

## Key Distinction: AgentMessage vs Message

- **Message** (from pi-ai): Only `user`, `assistant`, `toolResult` roles that LLMs understand
- **AgentMessage**: Extends Message with custom app-specific types via TypeScript declaration merging

```typescript
// Apps extend this interface:
declare module "@mariozechner/pi-agent-core" {
  interface CustomAgentMessages {
    notification: { role: "notification"; text: string };
  }
}

type AgentMessage = Message | CustomAgentMessages[keyof CustomAgentMessages];
```

The two-stage conversion pipeline handles this:
```
AgentMessage[] → transformContext() → AgentMessage[] → convertToLlm() → Message[] → LLM
```

---

## Agent Class (`src/agent.ts`)

### State

```typescript
interface AgentState {
  systemPrompt: string;
  model: Model<any>;
  thinkingLevel: ThinkingLevel;
  tools: AgentTool<any>[];
  messages: AgentMessage[];
  isStreaming: boolean;
  streamMessage: AgentMessage | null;  // Current partial during streaming
  pendingToolCalls: Set<string>;       // Tool IDs in flight
  error?: string;
}
```

### Core Methods

```typescript
// Prompting
prompt(message: AgentMessage | string, images?: ImageContent[]): Promise<void>
continue(): Promise<void>

// Steering (interrupt current work)
steer(message: AgentMessage): void
clearSteeringQueue(): void

// Follow-up (queue for after current work)
followUp(message: AgentMessage): void
clearFollowUpQueue(): void

// Control
abort(): void
waitForIdle(): Promise<void>
reset(): void

// Events
subscribe(fn: (event: AgentEvent) => void): () => void
```

### Queue Modes

Both steering and follow-up queues support two modes:
- `"one-at-a-time"` (default): Dequeue single message per turn
- `"all"`: Dequeue and process all messages at once

---

## Agent Loop (`src/agent-loop.ts`)

### Two-Level Nested Loop

```
Outer loop: Process follow-up messages
  while (true):
    Inner loop: Tool calls + steering
      while (hasMoreToolCalls || pendingMessages):
        1. Inject pending messages into context
        2. Stream assistant response from LLM
        3. If error/abort → emit turn_end, agent_end, return
        4. Extract tool calls from response
        5. If tool calls → execute them, add results to context
        6. emit turn_end
        7. Check steering queue → if messages, continue inner loop

    Check follow-up queue → if messages, continue outer loop
    Otherwise → break

  emit agent_end
```

### Steering vs Follow-up Injection Points

- **Steering**: Checked after each `turn_end` when tools finish. Interrupts before next LLM call.
- **Follow-up**: Checked only when no more tool calls AND no steering messages. Starts new work after agent would normally stop.

---

## Tool Execution

### Sequential Mode

Process tool calls one by one. Each tool runs to completion before next starts.

### Parallel Mode (default)

Two-phase:
1. **Sequential preflight**: Validate each tool, call `beforeToolCall` hook sequentially
2. **Concurrent execution**: All validated tools execute simultaneously
3. **Ordered results**: Await results in assistant source order (deterministic output)

### Tool Lifecycle

```
prepareToolCall()
  1. Look up tool by name → error if not found
  2. Validate arguments with AJV → error if invalid
  3. Call beforeToolCall hook → block if returns { block: true }
  4. Return prepared tool call

executePreparedToolCall()
  1. Call tool.execute(toolCallId, args, signal, onUpdate)
  2. Collect onUpdate partial results as events
  3. Catch errors → convert to error tool result

finalizeToolCall()
  1. Call afterToolCall hook (field-by-field replacement, no deep merge)
  2. Emit tool_execution_end event
  3. Create ToolResultMessage
```

### Tool Interface

```typescript
interface AgentTool<TParams, TDetails> extends Tool<TParams> {
  label: string;  // Human-readable for UI
  execute: (
    toolCallId: string,
    params: Static<TParams>,
    signal?: AbortSignal,
    onUpdate?: AgentToolUpdateCallback<TDetails>,
  ) => Promise<AgentToolResult<TDetails>>;
}

interface AgentToolResult<T> {
  content: (TextContent | ImageContent)[];  // Shown to LLM
  details: T;                                // Structured metadata for UI
}
```

**Contract**: Tools must `throw` on error (not return error messages).

---

## Event System

```typescript
type AgentEvent =
  | { type: "agent_start" }
  | { type: "agent_end"; messages: AgentMessage[] }
  | { type: "turn_start" }
  | { type: "turn_end"; message: AgentMessage; toolResults: ToolResultMessage[] }
  | { type: "message_start"; message: AgentMessage }
  | { type: "message_update"; message: AgentMessage; assistantMessageEvent }
  | { type: "message_end"; message: AgentMessage }
  | { type: "tool_execution_start"; toolCallId, toolName, args }
  | { type: "tool_execution_update"; toolCallId, toolName, args, partialResult }
  | { type: "tool_execution_end"; toolCallId, toolName, result, isError }
```

### Event Flow: Simple Prompt (No Tools)
```
agent_start → turn_start → message_start(user) → message_end(user)
→ message_start(assistant) → message_update* → message_end(assistant)
→ turn_end → agent_end
```

### Event Flow: With Tool Calls
```
agent_start → turn_start → message_start(user) → message_end(user)
→ message_start(assistant) → message_update* → message_end(assistant)
→ tool_execution_start → tool_execution_end → message_start(toolResult) → message_end(toolResult)
→ turn_end
→ turn_start  (next turn: LLM responds to tool results)
→ message_start(assistant) → message_update* → message_end(assistant)
→ turn_end → agent_end
```

---

## Proxy Support (`src/proxy.ts`)

`streamProxy()` enables browser/backend-proxied agents to call LLM through a server:

```typescript
const response = await fetch(`${proxyUrl}/api/stream`, {
  method: "POST",
  headers: { Authorization: `Bearer ${authToken}` },
  body: JSON.stringify({ model, context, options }),
});
```

Server sends compressed event stream. Client reconstructs full `AssistantMessageEvent` with `partial` field.

---

## Key Quirks

1. **convertToLlm must not throw**: Errors interrupt the loop without proper event sequence
2. **transformContext must not throw**: Return original messages as fallback
3. **Messages updated in-place during streaming**: `context.messages[last]` mutated for reactivity
4. **afterToolCall has no deep merge**: Field-by-field replacement only
5. **continue() requires non-assistant last message**: Must have steering/follow-up queued first
6. **beforeToolCall sees context with assistant message**: Post-message_end state
7. **Parallel execution maintains source order**: Results awaited in order despite concurrent execution
8. **Error tool results don't stop the loop**: LLM sees them and can adapt
9. **Only one active prompt allowed**: Concurrent calls throw; use steer()/followUp() instead
10. **streamMessage is null between messages**: Only non-null during active streaming
