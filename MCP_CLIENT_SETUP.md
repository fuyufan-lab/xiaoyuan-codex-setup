# MCP Client Setup

This repository exposes Xiaoyuan public-v3 as a local stdio MCP server.

Use it only in MCP clients that support local stdio servers.

## Generate Config

After installing the public bridge:

```bash
~/.xiaoyuan-codex-setup/xiaoyuan mcp-config
```

This prints the command, args, tool list, and ready-to-copy JSON snippets for
common local stdio MCP clients.

## Minimal Stdio Config

```json
{
  "command": "/absolute/path/to/xiaoyuan_client.py",
  "args": ["mcp-stdio"]
}
```

If installed through the public installer, use:

```bash
~/.xiaoyuan-codex-setup/xiaoyuan mcp-stdio
```

## Cursor Style

Cursor uses an `mcpServers` object. A common project-level location is
`.cursor/mcp.json`.

```json
{
  "mcpServers": {
    "xiaoyuan-public-v3": {
      "command": "/absolute/path/to/xiaoyuan",
      "args": ["mcp-stdio"]
    }
  }
}
```

## VS Code Style

VS Code stores MCP config in `mcp.json`, either in the workspace at
`.vscode/mcp.json` or in the user profile. VS Code's official format uses a
top-level `servers` object and a `type` field for stdio servers.

```json
{
  "servers": {
    "xiaoyuanPublicV3": {
      "type": "stdio",
      "command": "/absolute/path/to/xiaoyuan_client.py",
      "args": ["mcp-stdio"]
    }
  }
}
```

`xiaoyuan mcp-config` now prints both `cursor_style` and `vscode_style`
snippets so you can paste the right shape directly.

## Automatic Install

You can also ask the client to write these files directly:

```bash
xiaoyuan mcp-install --target all --scope workspace
```

Common variants:

- `xiaoyuan mcp-install --target cursor --scope workspace`
- `xiaoyuan mcp-install --target vscode --scope workspace`
- `xiaoyuan mcp-install --target all --scope user`
- `xiaoyuan mcp-install --target all --scope both`

The installer merges into existing JSON where possible and only updates the
Xiaoyuan server entry.

## Tools Exposed

- `xiaoyuan_doctor`: local readiness and API checks.
- `xiaoyuan_integrity`: local client SHA-256 verification.
- `xiaoyuan_submit_run`: submit a Xiaoyuan public-v3 run.
- `xiaoyuan_run_status`: fetch a run status.
- `xiaoyuan_run_events`: fetch run event history.
- `xiaoyuan_runtime_status`: fetch public-v3 API runtime status.
- `xiaoyuan_capabilities`: fetch the public capability catalog.
- `xiaoyuan_capability_route`: route a request to a public capability.
- `xiaoyuan_capability_execute`: execute through the public capability proxy and public-v3 run queue.
- `xiaoyuan_recovery_prompt`: return the standard terminal compatibility recovery prompt.
- `xiaoyuan_provider_inventory`: list local user-authenticated provider CLIs.
- `xiaoyuan_call_provider`: call local Codex / Claude Code from a trusted workspace.

## Local Provider Call

`xiaoyuan_call_provider` is the MCP-side local provider bridge.

It lets an MCP client ask Xiaoyuan's public bridge to call the user's existing
local provider CLI. It does not receive provider API keys or model secrets.

Required before it can run:

- `xiaoyuan install`
- `xiaoyuan integrity` passes
- target workspace is trusted through `xiaoyuan start --yes-i-trust-this-workspace`
- local provider CLI such as `codex` or `claude` is already authenticated

Example tool call:

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

## Boundary

This is a public client-only bridge. It must not contain Xiaoyuan core logic,
private routing, memory, governance, or backend source.

Do not treat this public Python bridge as a complete security product. It is a
client-only integration bridge. Advanced security controls belong in private
clients and server-side gates, not in this public repository.
