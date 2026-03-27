# Future Systems — Architectural Notes

Captured during Milestone 1-3 build sessions. These inform Milestone 5+ design.

---

## 1. Context Tracking & Visualization

Every API response includes `response.usage.input_tokens` and `output_tokens`. Track running totals per session.

Display: percentage of model context limit (200K for sonnet). TUI shows colored bar (green → yellow → red). Pre-TUI: status line after each response.

Trigger compaction or warn user when approaching limits. gsd-2 treats 200K as "maxed out."

---

## 2. Optional State Machine (Guardrails, Not Train Tracks)

```
IDLE → PLANNING → RESEARCHING → CODING → VALIDATING → DONE
```

Each state:
- Loads different context into system prompt
- Tracks transitions with timestamps
- Visual indication in TUI

Orchestrator decides WHEN to transition. LLM decides HOW to work within a state. The state machine IS the orchestrator's internal model — not a constraint on the LLM.

Aligns with Decision 13: "Python controls WHAT and WHEN, LLM controls HOW."

---

## 3. Scripted Orchestration via cmux

The orchestrator is pure Python. It can be scripted:

```
Orchestrator (always running in main pane)
├── reads pane output via cmux capture-pane
├── sends commands to panes via cmux send-keys
├── watches .workflow/completions/ for agent finish markers
├── detects stuck agents → spawns doctor agent
├── detects completion → updates tracking, writes next ACTIVE.toml, spawns next agent
├── detects test failures → sends nudge to responsible agent
└── all bookkeeping without any LLM calls
```

Agents never touch tracking files. Orchestrator handles all state management.

Scriptable triggers: cron jobs, GitHub webhooks, patrol loops, health checks.

---

## 4. Code Quality Loop ("The Cleaner")

Problem: Coding agents move fast and duplicate code, miss context, rewrite features unnecessarily.

Solution: periodic quality sweep, runs after every agent commit or on a timer.

```
Sweep 1: AST analysis (Python's ast module)
├── Duplicate functions across files
├── Unused imports and dead code
├── Inconsistent naming
└── No LLM needed — fast, deterministic, reliable

Sweep 2: LLM review of changed regions only
├── git diff to find what changed
├── "Here's before and after, any regressions?"
├── Small focused context = better output than "review everything"
└── Only for judgment calls the AST can't make

Sweep 3: Cross-file consistency check
├── "These 3 files all handle auth — are they consistent?"
├── Detects when an agent rewrote something that already existed elsewhere
└── Prevents the "quadruple feature" problem
```

Output options: report, auto-fix PR, nudge to responsible agent, or block merge.

Key insight: most code quality checks are mechanical. LLM only needed for judgment calls.

---

## 5. Research Divergence (Parallel Hypothesis Testing)

Problem: LLM research suffers from confirmation bias. Finds one answer, accepts it, stops looking. Real example from the build: web search said OAuth is "blocked by Anthropic," but a working implementation existed in gsd-2py on the local machine.

Solution: spawn parallel research agents with different starting constraints.

```
Research Question: "How do we do X?"

Agent A: web search only
Agent B: local codebase only (no web)
Agent C: SDK/library source code only
Agent D: reverse-engineer from working examples

Orchestrator compares results:
├── Consensus across agents = high confidence
├── Disagreement = dig deeper, spawn more agents
├── One outlier with evidence = investigate that path
└── All fail = genuinely unsolved, escalate to user
```

Divergence comes from constrained search paths, not smarter prompts. Each agent CAN'T fall into the same dead end because they're looking in different places.

This is cheap — each research agent uses minimal tokens (no code writing, just reading and summarizing). Running 3-4 in parallel costs less than one agent going down a wrong path for 20 turns.

---

## Open Design Questions

- How does the cleaner handle disagreements with agents? (Agent thinks code is right, cleaner says duplicate)
- Should research divergence be automatic or user-triggered?
- How many parallel research agents before diminishing returns? (Probably 3-4)
- Should the state machine be per-milestone, per-phase, or per-agent?
- How to detect "stuck" — time-based? output-based? token-burn-rate?
