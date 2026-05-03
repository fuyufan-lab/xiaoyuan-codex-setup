# Configuration Complete

This document defines when a developer machine is actually ready to use Xiaoyuan public-v3 through the user's own Codex / Claude Code environment.

## What Complete Means

The machine is complete only when all of these are true:

- The user can already run `codex` or `claude` in their own terminal.
- The public client-only Xiaoyuan bridge from this repository is installed.
- `xiaoyuan install` has initialized local config.
- `xiaoyuan login` has a valid user session.
- `xiaoyuan doctor --strict` passes.
- `xiaoyuan integrity` passes.
- `xiaoyuan start` starts the local terminal sidecar from a trusted workspace.
- A public-v3 task can be dispatched to the local sidecar.
- The sidecar executes through the user's own Codex / Claude Code login.
- Result writeback reaches the public-v3 run status/events API.

## Windows Baseline

Current Windows baseline:

- version: `0.3.54`
- manifest: `https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/releases/xiaoyuan/windows/latest.json`
- install root: `%USERPROFILE%\.xiaoyuan-codex-setup`
- terminal sidecar: user-started `xiaoyuan start`
- default API base: `https://yh.xiaofenhe.com/api/public-v3`

Public GitHub artifact boundary:

- Full `xiaoyuan-control-panel.zip` source payloads are not allowed in this repository.
- The public install package is client-only: `client/xiaoyuan_client.py`, `install.ps1`, and `install.sh`.
- The client bridge may call the public API and the user's own Codex / Claude Code command.
- `xiaoyuan start` can execute server-dispatched work through the local provider. It must only be run from trusted repositories and account sessions.
- `xiaoyuan mcp-config` can generate local stdio MCP configuration snippets for clients that support local stdio MCP.
- Backend/core logic must stay server-side or private.

## Not Complete

These do not count as complete:

- Files are downloaded but `xiaoyuan doctor --strict` fails.
- A process exists but the employee-visible status page does not refresh.
- Codex works in one shell but the Xiaoyuan sidecar is launched from another shell where `codex` is unavailable.
- `xiaoyuan start` is launched in an untrusted or wrong repository.
- The sidecar is installed but no real task reaches it.
- A task is queued but no result writeback appears.
- A synthetic or mocked proof is used instead of real local execution.
- A public package exposes backend/core source.

## Evidence Level

This repository can provide public configuration instructions and repeatable diagnostics. A single real machine passing the full private/client-only chain is E2 evidence.

E3 requires repeated validation across multiple machines, networks, accounts, and permission profiles. E4 requires long-term real usage evidence; do not claim E4 from a single install or one probe.
