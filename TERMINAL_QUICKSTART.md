# Terminal Quickstart

This is the intended public-v3 developer terminal usage path.

## 1. Security Boundary

This public repository must not ship Xiaoyuan core source or full control-panel source archives.

Use this repo for configuration, diagnostics, Codex recovery instructions, and the public client-only terminal bridge. The client bridge does not include backend/core logic.

Important: `xiaoyuan start` polls Xiaoyuan public-v3 and can execute server-dispatched work through your local Codex / Claude Code command. Run it only in a trusted repository. The first start for a workspace requires explicit trust confirmation.

## 2. Install The Client-Only Bridge

Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -UseBasicParsing https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/install.ps1 -OutFile $env:TEMP\xiaoyuan-install.ps1; powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\xiaoyuan-install.ps1"
```

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/install.sh | sh
```

## 3. Open Your Shell

Open the same shell where `codex` or `claude` already works.

Windows PowerShell:

```powershell
& "$env:USERPROFILE\.xiaoyuan-codex-setup\xiaoyuan.ps1" install
& "$env:USERPROFILE\.xiaoyuan-codex-setup\xiaoyuan.ps1" login --username <your-user>
& "$env:USERPROFILE\.xiaoyuan-codex-setup\xiaoyuan.ps1" doctor --strict
& "$env:USERPROFILE\.xiaoyuan-codex-setup\xiaoyuan.ps1" start
```

macOS / Linux:

```bash
~/.xiaoyuan-codex-setup/xiaoyuan install
~/.xiaoyuan-codex-setup/xiaoyuan login --username <your-user>
~/.xiaoyuan-codex-setup/xiaoyuan doctor --strict
~/.xiaoyuan-codex-setup/xiaoyuan start
```

MCP clients:

```bash
~/.xiaoyuan-codex-setup/xiaoyuan mcp-stdio
```

Use this command as the stdio MCP server command in ChatGPT/Claude/Cursor/VS Code/Codex-compatible clients that support MCP. The MCP bridge is a thin public adapter and does not include Xiaoyuan core source.

MCP tools include `xiaoyuan_submit_run` for sending work into Xiaoyuan, `xiaoyuan_capabilities` / `xiaoyuan_capability_route` / `xiaoyuan_capability_execute` for the public capability layer, and `xiaoyuan_call_provider` for calling the user's local Codex / Claude Code session from a trusted workspace.

To print ready-to-use local stdio MCP config snippets:

```bash
~/.xiaoyuan-codex-setup/xiaoyuan mcp-config
```

Use the generated snippets like this:

- Cursor: paste `cursor_style` into `.cursor/mcp.json`
- VS Code: paste `vscode_style` into `.vscode/mcp.json` or your user-profile `mcp.json`

Or let the client write them:

```bash
~/.xiaoyuan-codex-setup/xiaoyuan mcp-install --target all --scope workspace
```

Reverse provider bridge:

```bash
~/.xiaoyuan-codex-setup/xiaoyuan providers
~/.xiaoyuan-codex-setup/xiaoyuan call-provider "Inspect this repository and summarize risks" --provider codex
~/.xiaoyuan-codex-setup/xiaoyuan capabilities
~/.xiaoyuan-codex-setup/xiaoyuan capability-route "I do not know what Xiaoyuan can do here"
```

This is how Xiaoyuan can call the user's local Codex / Claude Code session without receiving provider secrets.

## 4. Keep Using Codex / Claude Code Normally

Users continue working in terminal with their own:

- Codex login
- Claude Code login
- repository workspace
- local permissions

Xiaoyuan public-v3 should route, verify, isolate, and write back results without replacing the user's working Codex / Claude Code environment.

For non-interactive automation, use `xiaoyuan start --yes-i-trust-this-workspace` only after the workspace, account, and API base are verified.

## 5. Confirm It Is Configured

Use [CONFIGURATION_COMPLETE.md](CONFIGURATION_COMPLETE.md) as the hard checklist.

Minimum confirmation:

- `xiaoyuan doctor --strict` passes.
- `xiaoyuan integrity` passes.
- The terminal agent can see the local Codex / Claude Code command.
- The active workspace has been explicitly trusted.
- MCP clients can list `xiaoyuan_*` tools if `mcp-stdio` is used.
- `xiaoyuan providers` lists local chat/agent provider availability for local provider calls.
- A public-v3 run reaches the local terminal sidecar.
- The result is written back with real execution evidence.

## 6. If It Does Not Work

Keep using Codex normally and ask it to follow [CODEX_COMPATIBILITY_RECOVERY.md](CODEX_COMPATIBILITY_RECOVERY.md). The expected recovery path is to inspect the local shell, PATH, install root, scheduled tasks, manifest URL, and doctor output, then make the smallest local configuration fix.
