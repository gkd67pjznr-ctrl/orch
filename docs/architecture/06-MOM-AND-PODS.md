# Package: @mariozechner/pi-mom — Slack Bot

## Overview

Mom ("Master of Mischief") is a stateful, conversation-aware Slack bot that delegates tasks to Claude Sonnet 4.5 via the pi-agent-core. It maintains persistent workspace storage and executes commands in Docker containers.

**Location**: `packages/mom/`
**Size**: ~3,000 lines

---

## Message Flow

```
Slack Socket Mode → SlackClient → ChannelQueue (FIFO per channel)
    → Agent Runner → pi-agent-core → Claude Sonnet 4.5
    → Tool execution (in Docker sandbox)
    → Response → Slack API → Channel
```

### Key Design

1. **Messages logged BEFORE processing** (durability first)
2. **One agent runner per channel** (cached, reused)
3. **Sequential queue per channel** (no race conditions)
4. **"stop" command bypasses queue** (immediate abort)
5. **Two-file persistence**: `log.jsonl` (source of truth) + `context.jsonl` (LLM context with tool results)

---

## File Storage Per Channel

```
data/
├── MEMORY.md                 # Global memory
├── settings.json             # Agent settings
├── skills/                   # Global skills
├── events/                   # Scheduled events
└── C123ABC/                  # Per-channel
    ├── MEMORY.md             # Channel-specific memory
    ├── log.jsonl             # All messages (immutable, append-only)
    ├── context.jsonl         # LLM context (mutable, includes tool results)
    ├── attachments/          # Downloaded Slack files
    └── skills/               # Channel-specific skills
```

---

## Tools

| Tool | Purpose |
|------|---------|
| bash | Execute commands (Docker or host) |
| read | Read files |
| write | Create files |
| edit | Surgical file edits |
| attach | Upload files to Slack |

---

## Events System

Three event types in `/workspace/events/`:

| Type | Trigger | Persistence |
|------|---------|-------------|
| **immediate** | Instantly when detected | Auto-deleted |
| **one-shot** | At specific ISO 8601 timestamp | Auto-deleted |
| **periodic** | Cron schedule with timezone | Until manually deleted |

**Silent completion**: If response is exactly `[SILENT]`, deletes message instead of posting.

---

## Key Quirks

1. **Tool results NOT in log.jsonl**: Only final bot text logged. Tool details in context.jsonl only.
2. **Message truncation**: 35K for main, 20K for threads (Slack 40K limit)
3. **Context sync on every run**: `syncLogToSessionManager()` picks up channel chatter between runs
4. **Skills reloaded every run**: No caching, new skills available immediately
5. **Attachment download timing**: Message logged before download completes — may see partial data
6. **Startup message filtering**: Messages older than `startupTs` logged but not processed

---

# Package: @mariozechner/pi — vLLM Deployment CLI

## Overview

CLI for managing vLLM deployments on GPU pods. Sets up fresh Ubuntu pods, manages models, tracks GPU allocation.

**Location**: `packages/pods/`
**Size**: ~2,000 lines

---

## Core Concepts

```
pi pods setup <name> <ssh>     # Initialize pod with vLLM
pi start <model> --name <n>    # Start model on pod
pi stop <name>                 # Stop running model
pi list                        # List pods/models
pi prompt                      # Interactive agent shell
```

### Pod Configuration

Stored in `~/.pi/pods.json`:

```typescript
interface Pod {
  ssh: string;                      // "ssh root@1.2.3.4"
  gpus: GPU[];                      // Detected via nvidia-smi
  models: Record<string, Model>;    // Running models
  modelsPath?: string;              // HF model cache path
  vllmVersion?: "release"|"nightly"|"gpt-oss";
}
```

---

## GPU Management

### Allocation Strategy

Round-robin: sort GPUs by usage count (least first), assign top N:
```
4 GPUs, all free:
  Model A (2 GPUs) → GPUs 0,1
  Model B (2 GPUs) → GPUs 2,3
  Model C (1 GPU)  → GPU 0  (least used, tie broken by lower ID)
```

### Port Assignment

Sequential from 8001, gaps NOT filled. Model on 8001 dies but not removed → next gets 8002.

---

## Predefined Model Configs

| Model | GPUs | Parser |
|-------|------|--------|
| Qwen2.5-Coder-32B | 1-2 | hermes |
| Qwen3-Coder-30B | 1-2 | qwen3_coder |
| Qwen3-Coder-480B | 8 | qwen3_coder |
| GPT-OSS-20B | 1 | /v1/responses API |
| GPT-OSS-120B | 1-8 | /v1/responses API |
| GLM-4.5 | 8-16 | glm45 |
| GLM-4.5-Air | 1-2 | glm45 |

---

## Key Quirks

1. **Models path from mount**: Extracts last arg from mount command — fragile parsing
2. **PID tracking stale on reboot**: Kill fails if process restarted, must manually clean config
3. **No health checks**: Model crash = still listed as running
4. **API keys in ENV, not config**: Not portable across machines
5. **GPU usage stale**: Manual kill without `pi stop` leaves phantom usage
6. **SSH command parsing fragile**: Expects `ssh [flags] [user@]host` format
