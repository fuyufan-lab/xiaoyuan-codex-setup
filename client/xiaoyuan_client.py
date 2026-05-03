#!/usr/bin/env python3
"""Public Xiaoyuan client-only terminal bridge.

This file is safe for the public bootstrap repository: it only implements
configuration, diagnostics, public API calls, and invocation of the user's own
Codex / Claude Code command. Xiaoyuan core logic stays server-side/private.
"""
from __future__ import annotations

import argparse
import hashlib
import getpass
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


CLIENT_VERSION = "0.3.54"
DEFAULT_API_BASE = os.getenv("XIAOYUAN_API_BASE", "https://yh.xiaofenhe.com/api/public-v3")
CONFIG_PATH = Path(os.getenv("XIAOYUAN_CLIENT_CONFIG", str(Path.home() / ".xiaoyuan-public-v3-client.json")))
STATE_PATH = Path(os.getenv("XIAOYUAN_CLIENT_STATE", str(Path.home() / ".xiaoyuan-public-v3-client-state.json")))


def now() -> int:
    return int(time.time())


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default or {})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except Exception:
        # Windows and some mounted filesystems may not support POSIX modes.
        pass


def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def print_json_line(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), flush=True)


def api_url(config: dict[str, Any], path: str) -> str:
    base = str(config.get("api_base") or DEFAULT_API_BASE).rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def api_base_is_safe(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme == "https":
        return True
    if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        return True
    return False


def http_json(
    config: dict[str, Any],
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
    auth: bool = True,
) -> dict[str, Any]:
    body = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    token = str(config.get("session_token") or "")
    if auth and token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(api_url(config, path), data=body, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            if not text.strip():
                return {}
            return json.loads(text)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"http_{exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network_error: {exc.reason}") from exc


def detect_providers() -> dict[str, str]:
    providers: dict[str, str] = {}
    codex = shutil.which("codex")
    claude = shutil.which("claude")
    if codex:
        providers["codex"] = codex
    if claude:
        providers["claude_code"] = claude
    return providers


def provider_inventory() -> dict[str, Any]:
    providers = detect_providers()
    return {
        "providers": [
            {
                "provider_id": provider_id,
                "command_available": True,
                "command_path_redacted": True,
                "version": command_version(command),
                "execution_mode": "local_user_authenticated_cli",
            }
            for provider_id, command in sorted(providers.items())
        ],
        "supported_provider_ids": sorted(providers.keys()),
        "boundary": "xiaoyuan_can_call_local_user_authenticated_chat_cli_without_receiving_model_secrets",
    }


def load_config(required: bool = True) -> dict[str, Any]:
    config = read_json(CONFIG_PATH)
    if required and not config:
        raise SystemExit(f"missing config: run install first ({CONFIG_PATH})")
    return config


def command_version(command: str) -> str:
    for args in ([command, "--version"], [command, "-v"]):
        try:
            result = subprocess.run(args, text=True, capture_output=True, timeout=12)
            text = (result.stdout or result.stderr or "").strip()
            if text:
                return text.splitlines()[0][:240]
        except Exception:
            continue
    return "version_unavailable"


def git_changed_files(workspace: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(workspace),
            text=True,
            capture_output=True,
            timeout=20,
        )
    except Exception:
        return []
    files: list[str] = []
    for line in result.stdout.splitlines():
        item = line[3:].strip() if len(line) > 3 else line.strip()
        if item:
            files.append(item)
    return files[:200]


def build_worker_id() -> str:
    user = getpass.getuser()
    host = socket.gethostname()
    return f"pv3-{host}-{user}".replace(" ", "-")[:120]


def current_client_path() -> Path:
    return Path(__file__).resolve()


def current_client_hash() -> str:
    return file_sha256(current_client_path())


def current_stdio_command() -> str:
    command = str(current_client_path())
    if not command:
        command = "xiaoyuan"
    return command


def cursor_server_config() -> dict[str, Any]:
    return {
        "command": current_stdio_command(),
        "args": ["mcp-stdio"],
    }


def vscode_server_config() -> dict[str, Any]:
    return {
        "type": "stdio",
        "command": current_stdio_command(),
        "args": ["mcp-stdio"],
    }


def default_workspace_dir(config: dict[str, Any]) -> Path:
    return Path(str(config.get("workspace_dir") or os.getcwd())).expanduser().resolve()


def vscode_user_mcp_path() -> Path:
    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "Code" / "User" / "mcp.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "User" / "mcp.json"
    return Path.home() / ".config" / "Code" / "User" / "mcp.json"


def cursor_user_mcp_path() -> Path:
    return Path.home() / ".cursor" / "mcp.json"


def mcp_install_targets(config: dict[str, Any], target: str, scope: str, workspace_value: str = "") -> list[dict[str, Any]]:
    workspace = Path(workspace_value).expanduser().resolve() if workspace_value else default_workspace_dir(config)
    targets: list[dict[str, Any]] = []
    want_cursor = target in {"cursor", "all"}
    want_vscode = target in {"vscode", "all"}
    if want_cursor:
        if scope in {"workspace", "both"}:
            targets.append(
                {
                    "client": "cursor",
                    "scope": "workspace",
                    "path": workspace / ".cursor" / "mcp.json",
                    "server_name": "xiaoyuan-public-v3",
                    "root_key": "mcpServers",
                    "server_config": cursor_server_config(),
                }
            )
        if scope in {"user", "both"}:
            targets.append(
                {
                    "client": "cursor",
                    "scope": "user",
                    "path": cursor_user_mcp_path(),
                    "server_name": "xiaoyuan-public-v3",
                    "root_key": "mcpServers",
                    "server_config": cursor_server_config(),
                }
            )
    if want_vscode:
        if scope in {"workspace", "both"}:
            targets.append(
                {
                    "client": "vscode",
                    "scope": "workspace",
                    "path": workspace / ".vscode" / "mcp.json",
                    "server_name": "xiaoyuanPublicV3",
                    "root_key": "servers",
                    "server_config": vscode_server_config(),
                }
            )
        if scope in {"user", "both"}:
            targets.append(
                {
                    "client": "vscode",
                    "scope": "user",
                    "path": vscode_user_mcp_path(),
                    "server_name": "xiaoyuanPublicV3",
                    "root_key": "servers",
                    "server_config": vscode_server_config(),
                }
            )
    return targets


def merge_mcp_server(path: Path, root_key: str, server_name: str, server_config: dict[str, Any]) -> dict[str, Any]:
    payload = read_json_file(path)
    existing = payload.get(root_key)
    if not isinstance(existing, dict):
        existing = {}
    before = existing.get(server_name)
    existing[server_name] = server_config
    payload[root_key] = existing
    write_json(path, payload)
    changed = before != server_config
    return {
        "path": str(path),
        "root_key": root_key,
        "server_name": server_name,
        "changed": changed,
        "server_config": server_config,
    }


def workspace_is_trusted(config: dict[str, Any], workspace: Path) -> bool:
    trusted = {str(item) for item in (config.get("trusted_workspaces") or [])}
    return str(workspace.resolve()) in trusted


def client_integrity_status(config: dict[str, Any]) -> dict[str, Any]:
    expected = str(config.get("client_sha256") or "")
    actual = current_client_hash()
    return {
        "expected": expected,
        "actual": actual,
        "path": str(current_client_path()),
        "ok": not expected or expected == actual,
        "enforced": bool(expected),
    }


def enforce_client_integrity(config: dict[str, Any]) -> None:
    status = client_integrity_status(config)
    if not status["ok"]:
        raise SystemExit(
            "client integrity check failed. Reinstall from the public bootstrap repository "
            "or inspect the local bridge before running remote dispatches."
        )


def cmd_install(args: argparse.Namespace) -> int:
    providers = detect_providers()
    selected = args.provider
    if selected == "auto":
        selected = "codex" if "codex" in providers else ("claude_code" if "claude_code" in providers else "codex")
    workspace = Path(args.workspace or os.getcwd()).expanduser().resolve()
    old = read_json(CONFIG_PATH)
    config = {
        "api_base": args.api_base,
        "workspace_dir": str(workspace),
        "provider_id": selected,
        "provider_ids": [selected],
        "worker_id": args.worker_id or build_worker_id(),
        "available_provider_ids": sorted(providers.keys()),
        "provider_commands_redacted": True,
        "installed_at": now(),
        "client_version": CLIENT_VERSION,
        "client_path": str(current_client_path()),
        "client_sha256": current_client_hash(),
        "config_path": str(CONFIG_PATH),
        "state_path": str(STATE_PATH),
        "security_boundary": "client_only_no_core_source",
        "trusted_workspaces": old.get("trusted_workspaces", []),
    }
    if old.get("session_token"):
        config["session_token"] = old["session_token"]
        config["user"] = old.get("user", {})
    write_json(CONFIG_PATH, config)
    print_json({"decision": "installed", "config": config, "next": ["xiaoyuan login", "xiaoyuan doctor --strict", "xiaoyuan start"]})
    return 0


def cmd_login(args: argparse.Namespace) -> int:
    config = load_config(required=False)
    if not config:
        config = {"api_base": args.api_base or DEFAULT_API_BASE}
    if args.api_base:
        config["api_base"] = args.api_base
    username = args.username or input("username: ").strip()
    password = args.password or getpass.getpass("password: ")
    payload = {"username": username, "password": password}
    result = http_json(config, "POST", "/login", payload, auth=False)
    token = str(result.get("session_token") or result.get("token") or "")
    if not token:
        raise SystemExit(f"login did not return a session token: {result}")
    config["session_token"] = token
    config["user"] = result.get("user") or {"username": username}
    config["login_at"] = now()
    write_json(CONFIG_PATH, config)
    print_json({"decision": "logged_in", "user": config.get("user", {}), "config_path": str(CONFIG_PATH)})
    return 0


def doctor_result(config: dict[str, Any]) -> dict[str, Any]:
    providers = detect_providers()
    selected = str(config.get("provider_id") or "codex")
    workspace = Path(str(config.get("workspace_dir") or os.getcwd())).expanduser()
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: Any = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("config_exists", CONFIG_PATH.exists(), str(CONFIG_PATH))
    add("workspace_exists", workspace.exists(), str(workspace))
    add("provider_selected", bool(selected), selected)
    add(
        "provider_command_available",
        selected in providers,
        {"provider_id": selected, "available": selected in providers, "command_path_redacted": True},
    )
    for provider, command in providers.items():
        add(f"{provider}_version", True, command_version(command))
    add("session_token_present", bool(config.get("session_token")), "present" if config.get("session_token") else "missing")
    add("client_only_boundary", True, "no backend/core source is required by this client")
    integrity = client_integrity_status(config)
    add("client_integrity", bool(integrity["ok"]), integrity)
    add("api_base_safe", api_base_is_safe(str(config.get("api_base") or DEFAULT_API_BASE)), str(config.get("api_base") or DEFAULT_API_BASE))
    if os.name != "nt" and CONFIG_PATH.exists():
        mode = CONFIG_PATH.stat().st_mode & 0o777
        add("config_file_private", mode <= 0o600, oct(mode))
    api_status: dict[str, Any] = {}
    try:
        api_status = http_json(config, "GET", "/status", timeout=12, auth=bool(config.get("session_token")))
        add("api_status_reachable", True, api_status.get("decision") or api_status.get("status") or "ok")
    except Exception as exc:
        add("api_status_reachable", False, str(exc))
    failed = [item for item in checks if not item["ok"]]
    return {
        "decision": "doctor_passed" if not failed else "doctor_failed",
        "strict_ready": not failed,
        "config_path": str(CONFIG_PATH),
        "state_path": str(STATE_PATH),
        "api_base": str(config.get("api_base") or DEFAULT_API_BASE),
        "worker_id": str(config.get("worker_id") or ""),
        "checks": checks,
        "blockers": [item["name"] for item in failed],
    }


def cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config(required=False)
    result = doctor_result(config)
    print_json(result)
    if args.strict and result["blockers"]:
        return 2
    return 0


def dispatch_prompt(dispatch: dict[str, Any], workspace: Path) -> str:
    contract = dispatch.get("agent_prompt_contract") if isinstance(dispatch.get("agent_prompt_contract"), dict) else {}
    task = str(contract.get("task") or dispatch.get("task") or "")
    must_respect = contract.get("must_respect") if isinstance(contract.get("must_respect"), list) else []
    minimum = contract.get("execution_minimum_steps") if isinstance(contract.get("execution_minimum_steps"), list) else []
    return "\n".join(
        [
            "Execute this Xiaoyuan public-v3 dispatch in the current workspace.",
            f"run_id: {dispatch.get('run_id') or ''}",
            f"dispatch_id: {dispatch.get('dispatch_id') or ''}",
            f"workspace: {workspace}",
            "",
            "Task:",
            task,
            "",
            "Must respect:",
            json.dumps(must_respect, ensure_ascii=False),
            "",
            "Minimum execution steps:",
            json.dumps(minimum, ensure_ascii=False),
            "",
            "Return a concise final summary including changed files, tests run, and residual risks.",
        ]
    )


def run_provider(config: dict[str, Any], dispatch: dict[str, Any], workspace: Path, timeout: int) -> tuple[str, str, int]:
    provider = str(dispatch.get("provider_id") or config.get("provider_id") or "codex")
    providers = detect_providers()
    command = providers.get(provider)
    if not command:
        return "", f"provider command unavailable: {provider}", 127
    prompt = dispatch_prompt(dispatch, workspace)
    if provider == "codex":
        cmd = [command, "exec", "--full-auto", "--skip-git-repo-check", "-C", str(workspace), prompt]
    elif provider == "claude_code":
        cmd = [command, "--print", prompt]
    else:
        return "", f"unsupported provider: {provider}", 127
    try:
        result = subprocess.run(cmd, cwd=str(workspace), text=True, capture_output=True, timeout=timeout)
        return result.stdout[-12000:], result.stderr[-4000:], int(result.returncode)
    except subprocess.TimeoutExpired as exc:
        return exc.stdout or "", f"provider timeout after {timeout}s", 124


def cmd_providers(_: argparse.Namespace) -> int:
    print_json(provider_inventory())
    return 0


def cmd_call_provider(args: argparse.Namespace) -> int:
    config = load_config(required=True)
    result = local_provider_call(
        config,
        prompt=args.prompt,
        provider=args.provider,
        workspace_value=args.workspace,
        provider_timeout=int(args.provider_timeout),
    )
    print_json(result)
    return 0 if result.get("exit_code") == 0 else 1


def local_provider_call(
    config: dict[str, Any],
    prompt: str,
    provider: str = "",
    workspace_value: str = "",
    provider_timeout: int = 1800,
) -> dict[str, Any]:
    if not prompt.strip():
        raise ValueError("prompt is required")
    enforce_client_integrity(config)
    workspace = Path(workspace_value or config.get("workspace_dir") or os.getcwd()).expanduser().resolve()
    if not workspace_is_trusted(config, workspace):
        raise RuntimeError(
            "workspace is not trusted. Run xiaoyuan start --yes-i-trust-this-workspace once "
            "after confirming this repository is safe."
        )
    provider_id = provider or config.get("provider_id") or "codex"
    dispatch = {
        "provider_id": provider_id,
        "task": prompt,
        "run_id": "local-provider-call",
        "dispatch_id": f"local-{now()}",
        "agent_prompt_contract": {
            "task": prompt,
            "must_respect": [
                "Use the local user's already-authenticated provider session.",
                "Do not request Xiaoyuan secrets or provider API keys.",
                "Return changed files, tests run, and residual risks.",
            ],
            "execution_minimum_steps": [],
        },
    }
    stdout, stderr, code = run_provider(config, dispatch, workspace, provider_timeout)
    return {
        "decision": "provider_call_completed" if code == 0 else "provider_call_failed",
        "provider_id": provider_id,
        "workspace": str(workspace),
        "exit_code": code,
        "stdout_tail": stdout,
        "stderr_tail": stderr,
        "boundary": "local_user_authenticated_chat_cli_call",
    }


def handle_dispatch(config: dict[str, Any], item: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    dispatch = item.get("agent_dispatch") if isinstance(item.get("agent_dispatch"), dict) else {}
    run_id = str(item.get("run_id") or dispatch.get("run_id") or "")
    dispatch_id = str(dispatch.get("dispatch_id") or "")
    provider_id = str(dispatch.get("provider_id") or config.get("provider_id") or "codex")
    workspace = Path(str((dispatch.get("client_runtime_hints") or {}).get("workspace_dir") or config.get("workspace_dir") or os.getcwd())).expanduser().resolve()
    if not workspace_is_trusted(config, workspace):
        payload = {
            "run_id": run_id,
            "dispatch_id": dispatch_id,
            "provider_id": provider_id,
            "status": "failed",
            "summary": f"blocked untrusted dispatch workspace: {workspace}",
            "changed_files": [],
            "tests": [],
            "residual_risks": ["untrusted_dispatch_workspace"],
        }
        callback = http_json(config, "POST", "/agent-adapters/result", payload, timeout=30, auth=True)
        return {"run_id": run_id, "dispatch_id": dispatch_id, "provider_exit_code": 126, "callback": callback}
    before = set(git_changed_files(workspace))
    stdout, stderr, code = run_provider(config, dispatch, workspace, int(args.provider_timeout))
    after = set(git_changed_files(workspace))
    changed = sorted(after or before)
    status = "completed" if code == 0 else "failed"
    summary = (stdout.strip() or stderr.strip() or f"provider exited {code}")[-3500:]
    payload = {
        "run_id": run_id,
        "dispatch_id": dispatch_id,
        "provider_id": provider_id,
        "status": status,
        "summary": summary,
        "changed_files": changed,
        "tests": [],
        "residual_risks": [] if code == 0 else [stderr[-800:] or f"provider_exit_code={code}"],
    }
    callback = http_json(config, "POST", "/agent-adapters/result", payload, timeout=30, auth=True)
    return {"run_id": run_id, "dispatch_id": dispatch_id, "provider_exit_code": code, "callback": callback}


def runtime_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    providers = detect_providers()
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "workspace": str(config.get("workspace_dir") or ""),
        "provider_ids": sorted(providers.keys()),
        "provider_commands_redacted": True,
        "client": "xiaoyuan-codex-setup-public-client",
        "client_version": CLIENT_VERSION,
        "client_sha256": current_client_hash(),
    }


def ensure_workspace_trusted(config: dict[str, Any], workspace: Path, assume_yes: bool) -> dict[str, Any]:
    workspace_value = str(workspace)
    trusted = list(config.get("trusted_workspaces") or [])
    if workspace_value in trusted:
        return config
    if not assume_yes:
        warning = (
            "Xiaoyuan start polls remote public-v3 dispatches and executes them through "
            "your local Codex / Claude Code command in this workspace.\n"
            f"Workspace: {workspace_value}\n"
            "Only continue in a trusted repository. Type TRUST to allow this workspace: "
        )
        if not sys.stdin.isatty():
            raise SystemExit(
                "workspace is not trusted. Re-run with --yes-i-trust-this-workspace "
                "only after confirming the workspace and account are safe."
            )
        if input(warning).strip() != "TRUST":
            raise SystemExit("workspace trust not confirmed")
    trusted.append(workspace_value)
    config["trusted_workspaces"] = sorted(set(trusted))
    write_json(CONFIG_PATH, config)
    return config


def cmd_start(args: argparse.Namespace) -> int:
    config = load_config(required=True)
    if not config.get("session_token"):
        raise SystemExit("missing session token: run login first")
    enforce_client_integrity(config)
    workspace = Path(str(config.get("workspace_dir") or os.getcwd())).expanduser().resolve()
    config = ensure_workspace_trusted(config, workspace, bool(args.yes_i_trust_this_workspace))
    poll_payload = {
        "worker_id": config.get("worker_id") or build_worker_id(),
        "provider_ids": config.get("provider_ids") or [config.get("provider_id") or "codex"],
        "lease_seconds": int(args.lease_seconds),
        "limit": 1,
        "client_runtime": runtime_snapshot(config),
    }
    print_json({
        "decision": "sidecar_started",
        "worker_id": poll_payload["worker_id"],
        "workspace": str(workspace),
        "once": bool(args.once),
        "security_boundary": "remote_dispatch_executes_local_provider_in_trusted_workspace",
    })
    while True:
        poll = http_json(config, "POST", "/agent-adapters/poll", poll_payload, timeout=30, auth=True)
        dispatches = poll.get("dispatches") if isinstance(poll.get("dispatches"), list) else []
        if not dispatches:
            if args.once:
                print_json({"decision": "poll_empty", "worker_id": poll_payload["worker_id"]})
                return 0
            time.sleep(float(args.poll_interval))
            continue
        for item in dispatches:
            result = handle_dispatch(config, item, args)
            print_json({"decision": "dispatch_handled", **result})
            write_json(STATE_PATH, {"last_dispatch": result, "updated_at": now()})
        if args.once:
            return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = load_config(required=True)
    payload = {
        "task_summary": args.task,
        "workspace_dir": str(Path(args.workspace or config.get("workspace_dir") or os.getcwd()).expanduser().resolve()),
        "agent_provider": args.provider or config.get("provider_id") or "codex",
    }
    result = http_json(config, "POST", "/run", payload, timeout=30, auth=True)
    print_json(result)
    return 0


def cmd_capabilities(_: argparse.Namespace) -> int:
    config = load_config(required=False)
    result = http_json(config, "GET", "/capabilities", timeout=20, auth=False)
    print_json(result)
    return 0


def cmd_capability_route(args: argparse.Namespace) -> int:
    config = load_config(required=True)
    payload = {
        "message": args.message,
        "capability_id": args.capability_id,
    }
    result = http_json(config, "POST", "/capabilities/route", payload, timeout=30, auth=True)
    print_json(result)
    return 0


def cmd_capability_execute(args: argparse.Namespace) -> int:
    config = load_config(required=True)
    payload = {
        "capability_id": args.capability_id,
        "task_text": args.task,
        "workspace_dir": str(Path(args.workspace or config.get("workspace_dir") or os.getcwd()).expanduser().resolve()),
        "agent_provider": args.provider or config.get("provider_id") or "codex",
    }
    result = http_json(config, "POST", "/capabilities/execute", payload, timeout=30, auth=True)
    print_json(result)
    return 0


def mcp_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "xiaoyuan_doctor",
            "description": "Inspect local Xiaoyuan public-v3 client readiness, provider availability, API status, and integrity state.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "xiaoyuan_integrity",
            "description": "Check whether the local Xiaoyuan public client file still matches the installed SHA-256 hash.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "xiaoyuan_submit_run",
            "description": "Submit a Xiaoyuan public-v3 run to be routed to the developer terminal sidecar.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_summary": {"type": "string"},
                    "workspace_dir": {"type": "string"},
                    "agent_provider": {"type": "string", "enum": ["codex", "claude_code"]},
                },
                "required": ["task_summary"],
                "additionalProperties": False,
            },
        },
        {
            "name": "xiaoyuan_run_status",
            "description": "Fetch current status for a Xiaoyuan public-v3 run.",
            "inputSchema": {
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "xiaoyuan_run_events",
            "description": "Fetch event history for a Xiaoyuan public-v3 run.",
            "inputSchema": {
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "xiaoyuan_runtime_status",
            "description": "Fetch public-v3 runtime status from the Xiaoyuan API.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "xiaoyuan_capabilities",
            "description": "Fetch the public Xiaoyuan capability catalog without exposing backend internals.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "xiaoyuan_capability_route",
            "description": "Route a user request to a public Xiaoyuan capability without exposing backend internals.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "capability_id": {"type": "string"},
                },
                "required": ["message"],
                "additionalProperties": False,
            },
        },
        {
            "name": "xiaoyuan_capability_execute",
            "description": "Execute a request through the public capability proxy and public-v3 run queue.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_text": {"type": "string"},
                    "capability_id": {"type": "string"},
                    "workspace_dir": {"type": "string"},
                    "agent_provider": {"type": "string", "enum": ["codex", "claude_code"]},
                },
                "required": ["task_text"],
                "additionalProperties": False,
            },
        },
        {
            "name": "xiaoyuan_recovery_prompt",
            "description": "Return the standard recovery prompt for fixing Codex / Claude Code terminal compatibility.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "xiaoyuan_provider_inventory",
            "description": "List local user-authenticated chat/agent CLIs that Xiaoyuan can call through this terminal bridge.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "xiaoyuan_call_provider",
            "description": "Call a local user-authenticated chat/agent CLI from a trusted workspace through the MCP local provider bridge.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "provider": {"type": "string", "enum": ["codex", "claude_code"]},
                    "workspace": {"type": "string"},
                    "provider_timeout": {"type": "integer", "minimum": 1, "maximum": 7200},
                },
                "required": ["prompt"],
                "additionalProperties": False,
            },
        },
    ]


def mcp_text(payload: Any) -> dict[str, Any]:
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2)
    return {"content": [{"type": "text", "text": text}]}


def mcp_call_tool(config: dict[str, Any], name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    args = arguments or {}
    if name == "xiaoyuan_doctor":
        return mcp_text(doctor_result(config))
    if name == "xiaoyuan_integrity":
        return mcp_text(client_integrity_status(config))
    if name == "xiaoyuan_submit_run":
        payload = {
            "task_summary": str(args.get("task_summary") or ""),
            "workspace_dir": str(args.get("workspace_dir") or config.get("workspace_dir") or os.getcwd()),
            "agent_provider": str(args.get("agent_provider") or config.get("provider_id") or "codex"),
        }
        if not payload["task_summary"].strip():
            raise ValueError("task_summary is required")
        return mcp_text(http_json(config, "POST", "/run", payload, timeout=30, auth=True))
    if name == "xiaoyuan_run_status":
        run_id = str(args.get("run_id") or "").strip()
        if not run_id:
            raise ValueError("run_id is required")
        return mcp_text(http_json(config, "GET", f"/runs/status?run_id={urllib.parse.quote(run_id)}", timeout=30, auth=True))
    if name == "xiaoyuan_run_events":
        run_id = str(args.get("run_id") or "").strip()
        if not run_id:
            raise ValueError("run_id is required")
        return mcp_text(http_json(config, "GET", f"/runs/events?run_id={urllib.parse.quote(run_id)}", timeout=30, auth=True))
    if name == "xiaoyuan_runtime_status":
        return mcp_text(http_json(config, "GET", "/status", timeout=12, auth=bool(config.get("session_token"))))
    if name == "xiaoyuan_capabilities":
        return mcp_text(http_json(config, "GET", "/capabilities", timeout=20, auth=False))
    if name == "xiaoyuan_capability_route":
        payload = {
            "message": str(args.get("message") or ""),
            "capability_id": str(args.get("capability_id") or ""),
        }
        if not payload["message"].strip():
            raise ValueError("message is required")
        return mcp_text(http_json(config, "POST", "/capabilities/route", payload, timeout=30, auth=True))
    if name == "xiaoyuan_capability_execute":
        payload = {
            "task_text": str(args.get("task_text") or ""),
            "capability_id": str(args.get("capability_id") or ""),
            "workspace_dir": str(args.get("workspace_dir") or config.get("workspace_dir") or os.getcwd()),
            "agent_provider": str(args.get("agent_provider") or config.get("provider_id") or "codex"),
        }
        if not payload["task_text"].strip():
            raise ValueError("task_text is required")
        return mcp_text(http_json(config, "POST", "/capabilities/execute", payload, timeout=30, auth=True))
    if name == "xiaoyuan_recovery_prompt":
        return mcp_text(
            "Make Xiaoyuan public-v3 use my existing working Codex or Claude Code terminal environment. "
            "Do not move my repository, do not replace my model login, and do not bypass local permissions. "
            "Diagnose the smallest config mismatch, fix it, then run xiaoyuan doctor --strict."
        )
    if name == "xiaoyuan_provider_inventory":
        return mcp_text(provider_inventory())
    if name == "xiaoyuan_call_provider":
        installed = load_config(required=True)
        return mcp_text(
            local_provider_call(
                installed,
                prompt=str(args.get("prompt") or ""),
                provider=str(args.get("provider") or ""),
                workspace_value=str(args.get("workspace") or ""),
                provider_timeout=int(args.get("provider_timeout") or 1800),
            )
        )
    raise ValueError(f"unknown tool: {name}")


def mcp_response(message_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def mcp_error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def cmd_mcp_stdio(_: argparse.Namespace) -> int:
    config = load_config(required=False)
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        message_id = None
        try:
            request = json.loads(raw_line)
            message_id = request.get("id")
            method = str(request.get("method") or "")
            params = request.get("params") if isinstance(request.get("params"), dict) else {}
            if method == "initialize":
                print_json_line(
                    mcp_response(
                        message_id,
                        {
                            "protocolVersion": "2025-06-18",
                            "serverInfo": {"name": "xiaoyuan-public-v3", "version": CLIENT_VERSION},
                            "capabilities": {"tools": {}},
                        },
                    )
                )
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                print_json_line(mcp_response(message_id, {"tools": mcp_tools()}))
            elif method == "tools/call":
                name = str(params.get("name") or "")
                arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
                print_json_line(mcp_response(message_id, mcp_call_tool(config, name, arguments)))
            else:
                print_json_line(mcp_error(message_id, -32601, f"method not found: {method}"))
        except Exception as exc:
            print_json_line(mcp_error(message_id, -32000, str(exc)))
    return 0


def cmd_recovery_prompt(_: argparse.Namespace) -> int:
    print(
        "Make Xiaoyuan public-v3 use my existing working Codex or Claude Code terminal environment. "
        "Do not move my repository, do not replace my model login, and do not bypass local permissions. "
        "Diagnose the smallest config mismatch, fix it, then run xiaoyuan doctor --strict."
    )
    return 0


def cmd_integrity(_: argparse.Namespace) -> int:
    config = load_config(required=False)
    status = client_integrity_status(config)
    print_json({"decision": "integrity_passed" if status["ok"] else "integrity_failed", "client_integrity": status})
    return 0 if status["ok"] else 2


def cmd_mcp_config(_: argparse.Namespace) -> int:
    config = load_config(required=False)
    command = current_stdio_command()
    stdio_args = ["mcp-stdio"]
    cursor_server = cursor_server_config()
    vscode_server = vscode_server_config()
    workspace = default_workspace_dir(config)
    payload = {
        "decision": "mcp_config_generated",
        "server_name": "xiaoyuan-public-v3",
        "command": command,
        "args": stdio_args,
        "tools": [tool["name"] for tool in mcp_tools()],
        "generic_stdio_mcp": {
            "command": command,
            "args": stdio_args,
        },
        "claude_desktop_style": {
            "mcpServers": {
                "xiaoyuan-public-v3": cursor_server
            }
        },
        "cursor_style": {
            "mcpServers": {
                "xiaoyuan-public-v3": cursor_server
            }
        },
        "cursor_paths": {
            "project": str(workspace / ".cursor" / "mcp.json"),
            "global": str(cursor_user_mcp_path()),
        },
        "vscode_style": {
            "servers": {
                "xiaoyuanPublicV3": vscode_server
            }
        },
        "vscode_paths": {
            "workspace": str(workspace / ".vscode" / "mcp.json"),
            "user_profile": str(vscode_user_mcp_path()),
        },
        "mcp_install_examples": {
            "workspace_all": "xiaoyuan mcp-install --target all --scope workspace",
            "user_all": "xiaoyuan mcp-install --target all --scope user",
            "both_all": "xiaoyuan mcp-install --target all --scope both",
        },
        "local_provider_ready": {
            "tool": "xiaoyuan_call_provider",
            "requires": [
                "xiaoyuan install",
                "xiaoyuan login when public-v3 API calls are needed",
                "xiaoyuan integrity passes",
                "workspace trusted through xiaoyuan start --yes-i-trust-this-workspace",
                "local provider CLI such as codex or claude is already authenticated",
            ],
        },
        "boundary": "local_stdio_mcp_only_for_clients_that_support_local_stdio_mcp",
        "config_path": str(CONFIG_PATH),
        "installed_workspace": str(config.get("workspace_dir") or "") if config else "",
    }
    print_json(payload)
    return 0


def cmd_mcp_install(args: argparse.Namespace) -> int:
    config = load_config(required=False)
    writes = []
    for item in mcp_install_targets(config, args.target, args.scope, args.workspace):
        result = merge_mcp_server(
            path=Path(str(item["path"])),
            root_key=str(item["root_key"]),
            server_name=str(item["server_name"]),
            server_config=dict(item["server_config"]),
        )
        result["client"] = item["client"]
        result["scope"] = item["scope"]
        writes.append(result)
    print_json(
        {
            "decision": "mcp_install_completed",
            "target": args.target,
            "scope": args.scope,
            "writes": writes,
            "next": [
                "Open the target editor and reload MCP servers if it was already running.",
                "Run xiaoyuan mcp-config to inspect the generated snippets and paths.",
            ],
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xiaoyuan", description="Public Xiaoyuan client-only terminal bridge")
    sub = parser.add_subparsers(dest="command", required=True)
    install = sub.add_parser("install")
    install.add_argument("--api-base", default=DEFAULT_API_BASE)
    install.add_argument("--workspace", default=os.getcwd())
    install.add_argument("--provider", default="auto", choices=["auto", "codex", "claude_code"])
    install.add_argument("--worker-id", default="")
    install.set_defaults(func=cmd_install)

    login = sub.add_parser("login")
    login.add_argument("--api-base", default="")
    login.add_argument("--username", default="")
    login.add_argument("--password", default="")
    login.set_defaults(func=cmd_login)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--strict", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    start = sub.add_parser("start")
    start.add_argument("--once", action="store_true")
    start.add_argument("--poll-interval", default=5.0, type=float)
    start.add_argument("--lease-seconds", default=900, type=int)
    start.add_argument("--provider-timeout", default=1800, type=int)
    start.add_argument("--yes-i-trust-this-workspace", action="store_true")
    start.set_defaults(func=cmd_start)
    providers = sub.add_parser("providers")
    providers.set_defaults(func=cmd_providers)
    call_provider = sub.add_parser("call-provider")
    call_provider.add_argument("prompt")
    call_provider.add_argument("--provider", default="")
    call_provider.add_argument("--workspace", default="")
    call_provider.add_argument("--provider-timeout", default=1800, type=int)
    call_provider.set_defaults(func=cmd_call_provider)

    run = sub.add_parser("run")
    run.add_argument("task")
    run.add_argument("--workspace", default="")
    run.add_argument("--provider", default="")
    run.set_defaults(func=cmd_run)

    capabilities = sub.add_parser("capabilities")
    capabilities.set_defaults(func=cmd_capabilities)
    capability_route = sub.add_parser("capability-route")
    capability_route.add_argument("message")
    capability_route.add_argument("--capability-id", default="")
    capability_route.set_defaults(func=cmd_capability_route)
    capability_execute = sub.add_parser("capability-execute")
    capability_execute.add_argument("task")
    capability_execute.add_argument("--capability-id", default="")
    capability_execute.add_argument("--workspace", default="")
    capability_execute.add_argument("--provider", default="")
    capability_execute.set_defaults(func=cmd_capability_execute)
    recovery = sub.add_parser("recovery-prompt")
    recovery.set_defaults(func=cmd_recovery_prompt)
    integrity = sub.add_parser("integrity")
    integrity.set_defaults(func=cmd_integrity)
    mcp_config = sub.add_parser("mcp-config")
    mcp_config.set_defaults(func=cmd_mcp_config)
    mcp_install = sub.add_parser("mcp-install")
    mcp_install.add_argument("--target", default="all", choices=["cursor", "vscode", "all"])
    mcp_install.add_argument("--scope", default="workspace", choices=["workspace", "user", "both"])
    mcp_install.add_argument("--workspace", default="")
    mcp_install.set_defaults(func=cmd_mcp_install)
    mcp = sub.add_parser("mcp-stdio")
    mcp.set_defaults(func=cmd_mcp_stdio)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print_json({"decision": "error", "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
