# Public Repository Security Boundary

This repository is public. It must not contain Xiaoyuan core design or backend implementation.

This repository is not the product frontend repository. It is a developer terminal bridge and public bootstrap entry.

Allowed:

- Public quickstart documentation.
- Public API contract.
- Configuration completion checklist.
- Codex compatibility recovery guide.
- Safe release manifest metadata.
- Client-only terminal bridge source under `client/`.
- Client-only installer scripts `install.ps1` and `install.sh`.

Not allowed:

- `xiaoyuan-control-panel.zip` source payloads.
- macOS tar/app archives containing control-panel source.
- Backend source files.
- Core reasoning, governance, memory, proof, routing, or self-evolution implementation.
- Private runtime state, secrets, tokens, keys, or internal evidence stores.

Public install artifacts must be client-only packages or signed binaries that do not expose backend/core logic. If a package cannot meet that boundary, it must not be published here.

Runtime boundary:

- The client may call public-v3 APIs and the user's own local Codex / Claude Code command.
- Public capability calls may discover, route, and execute public capability IDs only. They must not expose backend function names, internal tool handles, private runtime source, or cross-tenant state.
- The client must not contain private routing, proof, memory, governance, or self-evolution logic.
- `xiaoyuan start` can execute server-dispatched work locally. Users must run it only from trusted repositories and trusted account sessions.
- `xiaoyuan mcp-stdio` exposes only client-safe public-v3 tools. It must not expose raw filesystem write primitives, raw shell execution primitives, backend internals, or private capability logic.
- Local provider calls use local user-authenticated CLIs only. The public bridge must not store or transmit Codex, Claude Code, ChatGPT, Gemini, or other provider secrets.
- Local provider calls must remain bounded by trusted workspace, client integrity, local provider availability, and server-side dispatch authorization.
- MCP-side local provider calls must reuse the same provider whitelist, workspace trust, client integrity, and timeout boundaries as `xiaoyuan call-provider`.
- Local session tokens are stored in the user's client config file and should be treated as credentials.
- Installer scripts verify the downloaded client hash from the public manifest before writing the launcher.
- The client stores its installed SHA-256 hash and blocks `start` if the local bridge file changes unexpectedly.
- These checks are public-client integrity and boundary checks. A public Python bridge must assume the source can be read.

Advanced security controls are out of scope for this public Python bridge. They belong in private clients, private release operations, and server-side policy gates.
