---
name: swarm-dispatch
description: CPOS swarm fast-path dispatcher. Automatically splits independent multi-file coding tasks into parallel coder subagents. Falls back to serial execution if Agent is disabled. Use when creating or modifying multiple files with no inter-dependencies.
---

# CPOS Swarm Dispatch

## Decision tree (hot-switch, no restart needed)

```
Multiple independent file ops?
    │
    ├── YES → Try Agent(type="coder") × N
    │           │
    │           ├── success → merge results, update immune memory
    │           └── "disabled" → fall back to serial (do NOT retry Agent)
    │
    └── NO  → serial execution
```

## Rules

1. **Max parallelism**: 3 coder agents at once.
2. **No overlap**: Each agent gets a disjoint set of files.
3. **One fallback attempt**: If Agent returns 40441 ("Agent disabled"), switch to serial immediately. Do not retry Agent in the same session.
4. **Result merge**: After all agents finish, verify no file conflicts, run integration check.
5. **Immune writeback**: Record dispatch outcome in CPOS immune memory after each run.

## Invocation

```python
Agent(
    subagent_type="coder",
    description="<short task label>",
    prompt="<specific single-file task with absolute paths>"
)
```

## After dispatch

- Collect all agent results.
- Run one integration verification command.
- Update immune memory with path taken (parallel or fallback).
