# Codex Compatibility Recovery

Use this when Xiaoyuan is installed from this repository but does not behave like the user's normal Codex / Claude Code workflow.

The recovery principle is simple: do not replace the user's working Codex environment. Make Xiaoyuan discover and reuse it.

## Give This To Codex

Ask Codex to inspect the local machine with this goal:

```text
Make Xiaoyuan public-v3 use my existing working Codex or Claude Code terminal environment. Do not move my repository, do not replace my model login, and do not bypass local permissions. Diagnose the smallest config mismatch, fix it, then run xiaoyuan doctor --strict.
```

## Check Order

1. Confirm the user shell can run Codex / Claude Code:

```powershell
where codex
codex --version
where claude
claude --version
```

2. Confirm Xiaoyuan public client install root:

```powershell
$env:USERPROFILE + "\.xiaoyuan-codex-setup"
Test-Path "$env:USERPROFILE\.xiaoyuan-codex-setup"
```

3. Confirm Xiaoyuan config files:

```powershell
Test-Path "$env:USERPROFILE\.xiaoyuan-public-v3-client.json"
Test-Path "$env:USERPROFILE\.xiaoyuan-public-v3-client-state.json"
```

4. Run strict diagnostics from the public client:

```powershell
& "$env:USERPROFILE\.xiaoyuan-codex-setup\xiaoyuan.ps1" doctor --strict
```

5. Start or restart the terminal sidecar from the trusted workspace:

```powershell
& "$env:USERPROFILE\.xiaoyuan-codex-setup\xiaoyuan.ps1" start
```

## Common Fixes

- PATH mismatch: launch Xiaoyuan sidecar from the same shell profile where `codex` works.
- Wrong working directory: set the workspace to the user's actual repository, not the Xiaoyuan install directory.
- Manifest mismatch: reinstall using this repository's `latest.json`.
- Old release: update to `0.3.46` or later.
- Sidecar not running: start `xiaoyuan start` from the trusted workspace.
- Permission mismatch: keep execution in user space; do not require admin unless the user's workflow already requires it.

## Done Criteria

Recovery is done only when:

- `xiaoyuan doctor --strict` passes.
- The sidecar sees a real `codex` or `claude` command.
- A public-v3 run is dispatched to the local sidecar.
- The result is written back to the run status/events API.
