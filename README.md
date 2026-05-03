# Xiaoyuan Codex Setup

This public repository is the public bootstrap entry for Xiaoyuan public-v3 developer users.

Target workflow: developers keep using Codex / Claude Code normally in their own terminal, then use this repository for public configuration, diagnostics, terminal-side dispatch, and compatibility recovery.

Security boundary: this repository must not contain Xiaoyuan backend source, core reasoning logic, private runtime logic, or full control-panel source archives. Public installable artifacts must be client-only packages or signed binaries that do not expose core design.

Included:

- release manifests
- client-only terminal bridge
- installer scripts for the client-only bridge
- terminal-first quickstart docs
- configuration completion docs
- Codex compatibility recovery docs
- public API contract

Not included:

- frontend source
- backend source
- full control-panel source zip/tar payloads
- private runtime logic
- secrets or execution keys

Primary path:

1. Open the same terminal where Codex / Claude Code already works.
2. Install the public client-only bridge from this repository.
3. Run `xiaoyuan doctor --strict`.
4. Run `xiaoyuan start` from a trusted workspace only.
5. If the local environment is incompatible, ask Codex to follow `CODEX_COMPATIBILITY_RECOVERY.md`.

MCP path for chat/agent clients:

```bash
~/.xiaoyuan-codex-setup/xiaoyuan mcp-stdio
```

This exposes a client-only MCP server for ChatGPT Apps/Connectors, Claude, Cursor, VS Code, Codex-compatible launchers, and other MCP clients. It does not expose Xiaoyuan core logic; it only offers public-v3 tools such as doctor, integrity, submit run, run status, run events, runtime status, public capability discovery/routing/execution, and recovery prompt.
It also exposes `xiaoyuan_call_provider`: a local MCP client can ask the bridge to call the user's already-authenticated Codex / Claude Code CLI from a trusted workspace.

Local provider path:

```bash
~/.xiaoyuan-codex-setup/xiaoyuan providers
~/.xiaoyuan-codex-setup/xiaoyuan call-provider "Inspect this repository and summarize risks" --provider codex
```

This lets Xiaoyuan call local user-authenticated chat/agent CLIs without receiving provider secrets. Xiaoyuan can route work to Codex / Claude Code through the terminal bridge, while model credentials stay local.

Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -UseBasicParsing https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/install.ps1 -OutFile $env:TEMP\xiaoyuan-install.ps1; powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\xiaoyuan-install.ps1"
```

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/install.sh | sh
```

Docs:

- [TERMINAL_QUICKSTART.md](TERMINAL_QUICKSTART.md)
- [MCP_CLIENT_SETUP.md](MCP_CLIENT_SETUP.md)
- [PUBLIC_V3_API.md](PUBLIC_V3_API.md)
- [CONFIGURATION_COMPLETE.md](CONFIGURATION_COMPLETE.md)
- [CODEX_COMPATIBILITY_RECOVERY.md](CODEX_COMPATIBILITY_RECOVERY.md)
- [SECURITY_BOUNDARY.md](SECURITY_BOUNDARY.md)
- [SECURITY_RELEASE_GATES.md](SECURITY_RELEASE_GATES.md)
- [PUBLICATION_CHECKLIST.md](PUBLICATION_CHECKLIST.md)

Editor integration:

- Cursor project config: `.cursor/mcp.json`
- VS Code workspace config: `.vscode/mcp.json`
- `xiaoyuan mcp-config` prints ready-to-copy `cursor_style` and `vscode_style` snippets
- `xiaoyuan mcp-install --target all --scope workspace` writes both files directly

Recommended public manifest:

- Windows manifest: `https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/releases/xiaoyuan/windows/latest.json`

This repository intentionally does not publish full source payload zips. It publishes only a client-only bridge that calls the public API and the user's own Codex / Claude Code command.

Runtime boundary:

- `xiaoyuan start` is a developer terminal sidecar. It can execute server-dispatched work through the local Codex / Claude Code command.
- `xiaoyuan capabilities`, `xiaoyuan capability-route`, and `xiaoyuan capability-execute` use public capability IDs and the public-v3 run queue; they do not expose backend tool handles.
- Run it only inside a trusted repository and account session.
- The first `start` for a workspace requires explicit trust confirmation, or `--yes-i-trust-this-workspace` in non-interactive automation.
- Installers verify the downloaded client SHA-256 from the public manifest.
- `xiaoyuan doctor` and `xiaoyuan integrity` report whether the local client file still matches the installed hash.
- `xiaoyuan mcp-stdio` is a thin MCP adapter over the same public client boundary.
- `xiaoyuan providers`, `xiaoyuan call-provider`, and MCP tool `xiaoyuan_call_provider` expose the local provider bridge for user-authenticated Chat/Agent CLIs.
