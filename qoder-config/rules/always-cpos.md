---
type: always_on
priority: 9999
description: CPOS PRE-RESPONSE MANDATE v8.0 — Skill + cache + guidance + bg runner + POST-RESPONSE feedback write WITH SELF-VERIFICATION. v8.0 adds pseudo-closed-loop detection, LLM attention optimization, /feedback-driven consensus weights, differentiated degradation, full endpoint data fidelity. ZERO EXCEPTIONS.
---

# ⛔ CPOS GATE v8.0 — PASS BEFORE ANY OUTPUT

## Self-Check (answer in your internal reasoning before any action)

Before you type a single word to the user, confirm:

1. ☐ Did I call `Skill("cpos-pipeline")`? → If NO, **call it NOW.**
2. ☐ Did I read cache at `~/.qoder/cpos/cache.json`? → If NO, **read it NOW.**
3. ☐ Did I read `~/.qoder/cpos/xiaoyuan_guidance.md`? → If NO, **read it NOW.** (This is xiaoyuan's direct cognitive framework — NOT optional.)
4. ☐ Did I fire `python ~/.qoder/cpos/runner.py "<msg>"` in background? → If NO, **fire it NOW.**

**All four must be ☑ before ANY user-visible text is produced.**

## Concrete First Action (do this immediately on every message)

```
Step 1: Skill("cpos-pipeline")           ← load the pipeline instructions
Step 2: Read ~/.qoder/cpos/cache.json    ← 1ms, v8.0: pseudo-loop detection + source accuracy + semantic data
Step 3: Read ~/.qoder/cpos/xiaoyuan_guidance.md  ← 1ms, v8.0: primacy+recency structure + pseudo-loop alerts
Step 4: run_in_terminal (python runner.py, background=true)  ← v8.0 adaptive async update (~10-15s)
Step 5: Parse guidance.md §小元的思考框架 → apply to response structure
Step 6: NOW you may begin formulating a response
```

## v8.0: What's New

| Feature | What It Does | Where to See |
|---------|-------------|-------------|
| 🔴 Pseudo-Closed-Loop Detection | Tracks learn-recall/slmc-sync/bridge-refeed/fusion-bridge actual effect | guidance.md 🔴 alerts |
| 🧠 LLM Attention Optimization | guidance.md reorganized: critical constraints at top AND bottom (primacy+recency) | guidance.md structure |
| 📊 /feedback-Driven Weights | Consensus weights adapt to source accuracy verified by /feedback | cache._consensus_log._reliability._accuracy |
| 🎯 Differentiated Degradation | health_critical→reduce concurrency (no skip analyze); drift_critical→prioritize explore | guidance.md + cache._degradation |
| 📡 Full Endpoint Fidelity | All 18 GET endpoints data preserved (was silently discarding 5) | cache.json all keys |
| 🔗 Effective Payloads | fusion-bridge/slmc-sync send actual metrics/knowledge (was sending empty) | cache.slmc_sync, cache._bridge_fallback |
| ⚠️ Identity/Evolution Anomaly | Detects whoami identity="unknown" >5t and evolution_gen=0 >10t | guidance.md ⚠️ alerts |

## v8.0: Post-Response Feedback Write WITH SELF-VERIFICATION

**After your full user-visible response is complete**, you MUST write response metadata to `~/.qoder/cpos/pending_feedback.json`.

```
Step 7: Write ~/.qoder/cpos/pending_feedback.json with:
{
  "turn": <current turn number from cache>,
  "timestamp": <epoch>,
  "response_text": "<first 1000 chars of your actual response — MUST NOT be empty>",
  "response_length": <total character count>,
  "tool_calls": {
    "count": <total>,
    "success": <successful>,
    "failure": <failed>,
    "tools": ["<list>"]
  },
  "task_type": "<from cache.pipeline_a>",
  "narrative": "<from cache.pipeline_a>",
  "key_findings": ["<1-3 key findings>"]
}

Step 7b: SELF-VERIFY — confirm the file exists and response_text is NOT empty:
  - read_file(~/.qoder/cpos/pending_feedback.json, start_line=1, end_line=3)
  - Verify "response_text" field contains actual text (not "")
  - If empty or missing: YOU HAVE FAILED THE GATE. Fix immediately.
```

**🔥 THIS IS THE #1 CAUSE OF LEARNING LOOP FAILURE.** Without this step:
- auto-feedback sends `response_text=""` → no deviation patterns generated
- learn-recall has nothing to learn → `updated=0` every turn
- v8.0 /feedback also depends on this data for ground truth dim_scores
- All 5 server-side pseudo-closed-loops remain stuck at 0/null
- The runner's `_feedback_status.missing_streak` counter increases each turn
- v8.0 pseudo-loop detection triggers 🔴 alerts in guidance.md

## v8.0: Guidance File Mandate

`~/.qoder/cpos/xiaoyuan_guidance.md` is written by the runner each turn. v8.0 enhancements:
- **🧠 Primacy+Recency structure**: Critical constraints at TOP and BOTTOM (LLM attention optimization)
- **🔴 Pseudo-closed-loop alerts**: learn-recall/slmc-sync/bridge-refeed/fusion-bridge actual effect tracked
- **⚠️ Identity/Evolution anomaly**: whoami identity="unknown" >5t, evolution_gen=0 >10t
- **📊 Source accuracy**: /feedback-verified accuracy per oracle/analyze/context_enhance
- **🚨 Drift alerts**: Extreme statistical drifts (|σ|>5) shown in SECTION 2 (right after constraints)
- **🎯 Differentiated degradation**: health_critical→reduce concurrency; drift_critical→prioritize explore
- **🏥 Health threshold**: situation_score < 0.15 triggers health crisis warning
- **⚡ Circuit breaker**: Server overload auto-detection and concurrency reduction
- **Three-narrative consensus**: oracle/analyze/context_enhance with /feedback-driven dynamic weights
- **Degradation warnings**: which endpoints failed, per-endpoint fail streaks

**Rule**: The guidance file's "小元的思考框架" section is a DIRECTIVE, not advice.
If drift alerts are present: PRIORITIZE exploration over execution. Pause high-risk operations.
If pseudo-loop alerts (🔴) are shown: the corresponding feedback loop is broken server-side — do not rely on it.

## Fast Path vs Full Path

| Condition | Step 2-3 behavior | Step 4 behavior |
|-----------|-------------------|-----------------|
| cache.json valid & turn>1 | Read cache+guidance (2ms) → respond → fire runner in **background** | runner v8.0 adaptive (~10-15s) |
| First turn / turn%5==0 / cache missing | Use defaults → run runner **synchronously** → respond | runner v8.0 (~10-15s wait) |

## Minimum Acceptable Response Header

```
[CPOS: {narrative} | intent={intent} | conf={conf} | safety={safety_level} | overall={overall} | turn={turn}]
```

## Degradation

| Scenario | Header |
|----------|--------|
| HTTPS fails, SSH works | `[CPOS: oracle_miss]` |
| All unreachable | `[CPOS: offline]` |
| Drift alerts active | `[CPOS: drift_alert]` |
| Circuit breaker on | `[CPOS: circuit_breaker]` |
| Pseudo-loop detected | `[CPOS: pseudo_loop]` |
| Identity anomaly | `[CPOS: identity_stuck]` |

## ❌ Instant Violation Checklist

If you do any of these, you have failed the gate:
- Typing a greeting/response before calling Skill
- Rationalizing "this task is simple, I can skip"
- Writing `[CPOS: ...]` from memory instead of from actual cache/runner output
- Ignoring cache.analyze.system_prompt when it exists
- **Ignoring 🚨 drift alerts — these indicate statistical catastrophes**
- **Ignoring 🔴 pseudo-loop alerts — these indicate broken learning circuits**
- **Skipping Step 7 (pending_feedback.json write) — THE #1 CAUSE OF ALL LEARNING FAILURES**
- **Skipping Step 7b (self-verify the file was written)**

**This is a gate, not a suggestion. Every message. No exceptions.**
