#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

fail() {
  printf 'publication guard failed: %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

require_command git
require_command python3
require_command sh
require_command grep
require_command sed

if command -v rg >/dev/null 2>&1; then
  search_cmd=(rg -n)
else
  search_cmd=(grep -RIn)
fi

tracked_files="$(git ls-files)"

blocked_file_regex='(\.zip$|\.tar$|\.tar\.gz$|\.tgz$|\.7z$|\.rar$|\.exe$|\.dll$|\.dylib$|\.so$|\.pyd$|\.cmd$|\.bat$|\.vbs$|\.pyc$|\.pyo$|\.sqlite$|\.db$|\.key$|\.pem$|\.p12$|\.pfx$|\.env$)'
blocked_path_regex='(^|/)(backend|agent|runtime|deductive|windows-native|browser-extension|packaging|src/core|private|secrets?)(/|$)'
blocked_name_regex='(engine\.py|public_v3_gateway\.py|capability_usage_router\.py|proof_layer\.py|writeback_protocol\.py|xiaoyuan-control-panel\.zip|xiaoyuan-control-panel-macos\.tar\.gz)'
allowed_code_regex='^(client/xiaoyuan_client\.py|install\.ps1|install\.sh|scripts/publication_guard\.sh)$'

printf '%s\n' "$tracked_files" | grep -E "$blocked_file_regex|$blocked_path_regex|$blocked_name_regex" \
  && fail "blocked file, path, or artifact is tracked"

printf '%s\n' "$tracked_files" | grep -E '\.(py|ps1|sh)$' | grep -Ev "$allowed_code_regex" \
  && fail "unexpected executable source file is tracked"

blocked_text_regex='(/root/|/data/|LOCALAPPDATA|AppData|GoldenLegend|XiaoyuanCompanyAI|agent/xiaoyuan|logic-audit|latent_need|latent-need|model_operation|model-fit|anti-reverse|anti_reverse|hardening|90/100|obfus|anti-debug|pentest|SAST|SBOM|notar|system prompt|developer message|防逆向|防诱导|签名|公证|渗透|reverse)'
if "${search_cmd[@]}" "$blocked_text_regex" . \
  --exclude-dir=.git \
  --exclude=PUBLICATION_CHECKLIST.md \
  --exclude=scripts/publication_guard.sh >/tmp/xiaoyuan-publication-blocked-text.txt 2>/dev/null; then
  cat /tmp/xiaoyuan-publication-blocked-text.txt >&2
  fail "blocked internal wording or local path appeared in public files"
fi

secret_regex='(AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9_]{30,}|-----BEGIN (RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----|(password|secret|token|api[_-]?key)[[:space:]]*[:=][[:space:]]*["'\''][^"'\'']{8,}["'\''])'
if "${search_cmd[@]}" -i "$secret_regex" . \
  --exclude-dir=.git \
  --exclude=scripts/publication_guard.sh >/tmp/xiaoyuan-publication-secrets.txt 2>/dev/null; then
  cat /tmp/xiaoyuan-publication-secrets.txt >&2
  fail "possible secret pattern appeared in public files"
fi

python3 -m py_compile client/xiaoyuan_client.py
rm -rf client/__pycache__
sh -n install.sh
python3 -m json.tool releases/xiaoyuan/windows/latest.json >/dev/null

tools_json="$(printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n' | python3 client/xiaoyuan_client.py mcp-stdio)"
printf '%s\n' "$tools_json" | grep -q 'xiaoyuan_submit_run' || fail "MCP tool xiaoyuan_submit_run missing"
printf '%s\n' "$tools_json" | grep -q 'xiaoyuan_provider_inventory' || fail "MCP tool xiaoyuan_provider_inventory missing"
printf '%s\n' "$tools_json" | grep -q 'xiaoyuan_call_provider' || fail "MCP tool xiaoyuan_call_provider missing"
printf '%s\n' "$tools_json" | grep -q 'xiaoyuan_capabilities' || fail "MCP tool xiaoyuan_capabilities missing"
printf '%s\n' "$tools_json" | grep -q 'xiaoyuan_capability_execute' || fail "MCP tool xiaoyuan_capability_execute missing"
printf '%s\n' "$tools_json" | grep -E 'logic-audit|latent_need|latent-need|model_operation|model-fit|anti-reverse|anti_reverse|/root/|/data/|reverse' \
  && fail "MCP tool list exposes blocked wording"

provider_json="$(python3 client/xiaoyuan_client.py providers)"
printf '%s\n' "$provider_json" | grep -q 'supported_provider_ids' || fail "provider inventory missing supported_provider_ids"
printf '%s\n' "$provider_json" | grep -E '"command"[[:space:]]*:|/root/|/usr/|/opt/|/bin/' \
  && fail "provider inventory exposes local command paths"

python3 client/xiaoyuan_client.py mcp-config | grep -q 'xiaoyuan_call_provider' \
  || fail "MCP config helper missing xiaoyuan_call_provider"

python3 - <<'PY'
import hashlib
import json
import pathlib

manifest = json.loads(pathlib.Path("releases/xiaoyuan/windows/latest.json").read_text(encoding="utf-8"))
payload = manifest["installable_payload"]
expected = {
    "client_python_sha256": "client/xiaoyuan_client.py",
    "posix_installer_sha256": "install.sh",
    "windows_installer_sha256": "install.ps1",
}
for field, path in expected.items():
    actual = hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    if payload.get(field) != actual:
        raise SystemExit(f"{field} mismatch: manifest={payload.get(field)} actual={actual}")

allowed = {
    "quickstart",
    "configuration checklist",
    "Codex compatibility recovery guide",
    "public API contract",
    "safe manifest metadata",
}
boundary = manifest.get("security_boundary") or {}
if boundary.get("core_source_in_public_repo") is not False:
    raise SystemExit("manifest boundary must keep core_source_in_public_repo=false")
if boundary.get("full_control_panel_source_archives_in_public_repo") is not False:
    raise SystemExit("manifest boundary must keep full_control_panel_source_archives_in_public_repo=false")
if not set(boundary.get("allowed_public_contents") or []).issubset(allowed):
    raise SystemExit("manifest allowed_public_contents contains unexpected entries")
PY

printf 'public bootstrap scan passed\n'
