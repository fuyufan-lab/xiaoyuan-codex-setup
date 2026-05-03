# Publication Checklist

Run this before publishing changes to the public bootstrap repository.

```bash
blocked_regex='(\.zip$|\.tar$|\.tar\.gz$|\.tgz$|\.7z$|\.rar$|\.exe$|\.dll$|\.pyd$|\.cmd$|\.bat$|\.vbs$|\.pyc$|\.pyo$|\.sqlite$|\.db$|\.key$|\.pem$|\.env$)'
blocked_paths='(^|/)(backend|agent|runtime|deductive|windows-native|browser-extension|packaging|src/core)(/|$)'
blocked_names='(engine\.py|public_v3_gateway\.py|capability_usage_router\.py|proof_layer\.py|writeback_protocol\.py|xiaoyuan-control-panel\.zip|xiaoyuan-control-panel-macos\.tar\.gz)'
files="$(git ls-files)"
printf '%s\n' "$files" | grep -E "$blocked_regex|$blocked_paths|$blocked_names" && exit 1
printf '%s\n' "$files" | grep -E '\.py$|\.ps1$|\.sh$' | grep -Ev '^(client/xiaoyuan_client\.py|install\.ps1|install\.sh)$' && exit 1
! rg -n '(/root/|/data/|LOCALAPPDATA|AppData|GoldenLegend|XiaoyuanCompanyAI|logic-audit|latent_need|latent-need|model_operation|model-fit|anti-reverse|anti_reverse|hardening|obfus|anti-debug|system prompt|developer message|防逆向|防诱导|渗透|公证|签名)' . --glob '!PUBLICATION_CHECKLIST.md'
python3 -m py_compile client/xiaoyuan_client.py
sh -n install.sh
python3 -m json.tool releases/xiaoyuan/windows/latest.json >/dev/null
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n' | python3 client/xiaoyuan_client.py mcp-stdio | grep -q 'xiaoyuan_submit_run'
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n' | python3 client/xiaoyuan_client.py mcp-stdio | grep -q 'xiaoyuan_provider_inventory'
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n' | python3 client/xiaoyuan_client.py mcp-stdio | grep -q 'xiaoyuan_call_provider'
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n' | python3 client/xiaoyuan_client.py mcp-stdio | grep -q 'xiaoyuan_capabilities'
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n' | python3 client/xiaoyuan_client.py mcp-stdio | grep -q 'xiaoyuan_capability_execute'
python3 client/xiaoyuan_client.py mcp-config | grep -q 'xiaoyuan_call_provider'
python3 client/xiaoyuan_client.py providers | grep -q 'supported_provider_ids'
python3 - <<'PY'
import hashlib, json, pathlib
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
        raise SystemExit(f"{field} mismatch: expected manifest {payload.get(field)} actual {actual}")
PY
echo "public bootstrap scan passed"
```

The public repository may contain only docs, safe manifest metadata, and the explicit client-only bridge files listed above.

Do not publish changes unless this checklist passes from a clean worktree.
