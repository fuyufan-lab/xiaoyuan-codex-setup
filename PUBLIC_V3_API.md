# Public V3 API

This document only describes the minimal public contract needed for terminal-first usage.

## Base

- API base: `https://yh.xiaofenhe.com/api/public-v3`

## Auth

Login returns a session token. Authenticated requests use:

```http
Authorization: Bearer <session_token>
```

## Core endpoints

### Register

`POST /register`

```json
{
  "username": "user-a",
  "password": "your-password",
  "email": "optional@example.com"
}
```

### Login

`POST /login`

```json
{
  "username": "user-a",
  "password": "your-password"
}
```

### Sessions

- `GET /sessions`
- `POST /logout`
- `POST /sessions/revoke`

Use these to inspect or revoke active sessions for the current user.

### Submit run

`POST /run`

```json
{
  "task_summary": "Fix this repository bug",
  "workspace_dir": "/path/to/repo",
  "agent_provider": "codex"
}
```

Common fields:

- `task_summary`
- `workspace_dir`
- `agent_provider`
- `preferred_agent_provider`
- `requires_model`

### Run status

- `GET /runs/status?run_id=<run_id>`
- `GET /runs/events?run_id=<run_id>`

These return current state and event history for the submitted run.

## Public Capabilities

These endpoints expose public capability contracts, not backend tool handles.

- `GET /capabilities`
- `POST /capabilities/route`
- `POST /capabilities/execute`

Route example:

```json
{
  "message": "I do not know what Xiaoyuan can do here. Show the useful possibilities."
}
```

Execute example:

```json
{
  "capability_id": "task_to_execution_plan",
  "task_text": "Turn this goal into an execution plan and queue it.",
  "workspace_dir": "/path/to/repo",
  "agent_provider": "codex"
}
```

The route response returns public routing metadata only. It must not be treated
as private reasoning, backend source, or internal tool access.

## Agent adapter contract

This is the terminal-side execution path.

### Poll work

`POST /agent-adapters/poll`

```json
{
  "worker_id": "pv3-terminal-host-01",
  "provider_ids": ["codex", "claude_code"],
  "lease_seconds": 900,
  "limit": 1
}
```

### Return result

`POST /agent-adapters/result`

```json
{
  "run_id": "run_xxx",
  "dispatch_id": "dispatch_xxx",
  "provider_id": "codex",
  "status": "completed",
  "summary": "Patched the bug and updated tests.",
  "changed_files": ["src/app.py"],
  "tests": ["pytest -q"],
  "residual_risks": []
}
```

## MCP tool bridge

The public client can run as a stdio MCP server:

```bash
xiaoyuan mcp-stdio
```

Generate local stdio MCP client config:

```bash
xiaoyuan mcp-config
```

This is the recommended universal integration path for ChatGPT Apps/Connectors, Claude, Cursor, VS Code, Codex-compatible launchers, and other MCP clients. The MCP bridge is client-only and only calls public-v3 endpoints or local diagnostics.

Tools:

- `xiaoyuan_doctor`: local readiness, provider, API, and integrity checks.
- `xiaoyuan_integrity`: local client SHA-256 verification.
- `xiaoyuan_submit_run`: submit a public-v3 run.
- `xiaoyuan_run_status`: fetch run status.
- `xiaoyuan_run_events`: fetch run event history.
- `xiaoyuan_runtime_status`: fetch API runtime status.
- `xiaoyuan_capabilities`: fetch the public capability catalog.
- `xiaoyuan_capability_route`: route a request to a public capability.
- `xiaoyuan_capability_execute`: execute through the public capability proxy.
- `xiaoyuan_recovery_prompt`: return the standard terminal compatibility recovery prompt.
- `xiaoyuan_provider_inventory`: list local user-authenticated chat/agent CLIs that Xiaoyuan can call through this terminal bridge.
- `xiaoyuan_call_provider`: call a local user-authenticated chat/agent CLI from a trusted workspace through the MCP local provider bridge.

## Local Provider Bridge

The local provider bridge means Xiaoyuan can call local user-authenticated chat/agent clients
without receiving provider API keys or model secrets. In this public bridge, the
safe local provider path is:

```text
Xiaoyuan server dispatch -> terminal bridge -> local Codex / Claude Code CLI -> result writeback
```

Local commands:

```bash
xiaoyuan providers
xiaoyuan call-provider "Inspect this repository and summarize risks" --provider codex
```

MCP-side local provider call:

```json
{
  "name": "xiaoyuan_call_provider",
  "arguments": {
    "prompt": "Inspect this repository and summarize risks",
    "provider": "codex",
    "workspace": "/path/to/trusted/repo",
    "provider_timeout": 1800
  }
}
```

Boundary:

- Xiaoyuan receives provider output and execution evidence.
- Xiaoyuan does not receive the user's Codex / Claude Code login secrets.
- The bridge only calls providers already available in the user's local terminal.
- The workspace must be explicitly trusted before provider calls can execute.
- MCP-side local provider calls reuse the same trusted workspace and client integrity checks as terminal-side calls.

## Optional runtime status

- `GET /status`
- `GET /execution/topology`
- `GET /native-store/status`
- `GET /parity/status`

These are useful for diagnostics, not required for normal shell usage.

## Boundary

This API document intentionally does not expose:

- backend source
- private inference logic
- internal execution secrets
- non-public admin routes
