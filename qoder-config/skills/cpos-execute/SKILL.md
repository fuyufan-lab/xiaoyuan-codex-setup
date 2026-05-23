# CPOS Execute Skill

Execute code tasks through the Xiaoyuan CPOS ESC Cognitive Wheel on the remote server.

## Overview

This skill invokes the Xiaoyuan V3 CPOS runtime via the live-ops API to execute a programming task through the full ESC (Evidence-Safety-Correction) cognitive wheel:
DISCOVER -> SPEC -> PLAN -> EXECUTE -> VERIFY -> REPAIR -> ACCEPT -> WRITEBACK

## When to Use

Use this skill when the user:
- Wants to execute a code task through the CPOS server infrastructure
- Asks to \ run through CPOS\, \execute via XiaoYuan\, or \use the ESC wheel\
- Needs server-side code generation with verification evidence

## API Configuration

- **Base URL**: https://yh.xiaofenhe.com/xiaoyuan-live-ops/v1/xiaoyuan
- **Auth Header**: Set CPOS_EXECUTE_TOKEN in your environment or .qoder/cpos/execute_token
- **Content-Type**: pplication/json

### Setting Your Token

**Windows (PowerShell):**
`powershell
 = \your-token-here\
`

**macOS/Linux:**
`ash
export CPOS_EXECUTE_TOKEN=\your-token-here\
`

Or create a file ~/.qoder/cpos/execute_token containing your token (one line, no newline).

## Execution Flow

### Step 1: Generate OS Record
`ash
curl -s -X POST \https://yh.xiaofenhe.com/xiaoyuan-live-ops/v1/xiaoyuan/xiaoyuan-os/generate\ \
  -H \Authorization: Bearer \ \
  -H \Content-Type: application/json\ \
  -d \'{
    \payload\: {
      \record_id\: \<unique-task-id>\,
      \user_intent\: \<task description>\,
      \essential_need\: \<core requirement>\,
      \hidden_requirements\: [\<req1>\, \<req2>\],
      \frontend_required\: false,
      \risk_level\: \low\
    }
  }\'
`

### Step 2: Start Task Runtime Loop
`ash
curl -s -X POST \https://yh.xiaofenhe.com/xiaoyuan-live-ops/v1/xiaoyuan/task-runtime-loop/start\ \
  -H \Authorization: Bearer \ \
  -H \Content-Type: application/json\ \
  -d \'{
    \payload\: {
      \loop_id\: \task-loop-<unique-task-id>\,
      \user_intent\: \<task description>\,
      \essential_need\: \<core requirement>\,
      \hidden_requirements\: [\<req1>\],
      \success_criteria\: [\<criterion1>\, \<criterion2>\],
      \max_iterations\: 8,
      \auto_continue\: true
    }
  }\'
`

### Step 3: Run Worker (execute the loop)
`ash
curl -s -X POST \https://yh.xiaofenhe.com/xiaoyuan-live-ops/v1/xiaoyuan/task-runtime-loop/worker/run\ \
  -H \Authorization: Bearer \ \
  -H \Content-Type: application/json\ \
  -d \'{
    \payload\: {
      \max_loops\: 10,
      \max_steps_per_loop\: 4,
      \dry_run\: false
    }
  }\'
`

### Step 4: Check State / Evidence
`ash
curl -s \https://yh.xiaofenhe.com/xiaoyuan-live-ops/v1/xiaoyuan/state\ \
  -H \Authorization: Bearer \
`

## Task ID Generation

Generate unique task IDs using: cpos-task-{timestamp}-{random_hex_6}
Example: cpos-task-20260505-a3f2b1

Loop ID is derived: 	ask-loop-{task_id}

## Result Interpretation

After execution, the state endpoint returns:
- evidence_ledger: Records of all evidence generated during execution
- usage_metrics: Runtime usage statistics
- unified_runtime.lab_root: Path to the lab directory on server
- unified_runtime.available: Whether the runtime service is reachable

## Important Notes

1. **Token Required**: All endpoints require the bearer token. Set via env var or token file.
2. **Dry Run**: Set \dry_run\: true in worker payload to simulate without execution
3. **Auto Continue**: When uto_continue is true, the worker will automatically advance through phases
4. **Max Steps**: Each loop can run up to max_steps_per_loop steps per worker invocation
5. **Evidence Boundary**: All claims have explicit claim boundaries -- CPOS proves local execution evidence, not global correctness

## Claim Boundary

> This skill calls the live-ops CPOS API which delegates to the xiaoyuan-finetune-lab RuntimeService. It proves API connectivity and task loop orchestration. The actual code execution evidence (cell-codex-result.json) resides in the server\'s 
uns/ directory and must be verified separately for correctness.
