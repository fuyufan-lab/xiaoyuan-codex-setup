#!/usr/bin/env sh
set -eu

INSTALL_DIR="${XIAOYUAN_INSTALL_DIR:-"$HOME/.xiaoyuan-codex-setup"}"
BRANCH="${XIAOYUAN_SETUP_BRANCH:-main}"
REPO="https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/$BRANCH"
CLIENT_DIR="$INSTALL_DIR/client"
MANIFEST_URL="$REPO/releases/xiaoyuan/windows/latest.json"
MANIFEST_PATH="$INSTALL_DIR/latest.json"
mkdir -p "$CLIENT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "Python 3 is required. Install Python or ask Codex to follow CODEX_COMPATIBILITY_RECOVERY.md." >&2
  exit 1
fi

download() {
  url="$1"
  output="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$output"
  else
    "$PYTHON" - "$url" "$output" <<'PY'
import sys, urllib.request
urllib.request.urlretrieve(sys.argv[1], sys.argv[2])
PY
  fi
}

download "$MANIFEST_URL" "$MANIFEST_PATH"
download "$REPO/client/xiaoyuan_client.py" "$CLIENT_DIR/xiaoyuan_client.py"

EXPECTED_CLIENT_SHA256="$("$PYTHON" - "$MANIFEST_PATH" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
print((data.get("installable_payload") or {}).get("client_python_sha256") or "")
PY
)"
if [ -n "$EXPECTED_CLIENT_SHA256" ]; then
  ACTUAL_CLIENT_SHA256="$("$PYTHON" - "$CLIENT_DIR/xiaoyuan_client.py" <<'PY'
import hashlib, sys
h = hashlib.sha256()
with open(sys.argv[1], "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)
print(h.hexdigest())
PY
)"
  if [ "$ACTUAL_CLIENT_SHA256" != "$EXPECTED_CLIENT_SHA256" ]; then
    echo "Downloaded Xiaoyuan client hash mismatch. Refusing to install." >&2
    echo "expected: $EXPECTED_CLIENT_SHA256" >&2
    echo "actual:   $ACTUAL_CLIENT_SHA256" >&2
    exit 1
  fi
else
  echo "Manifest did not include client_python_sha256. Refusing to install." >&2
  exit 1
fi

cat > "$INSTALL_DIR/xiaoyuan" <<EOF
#!/usr/bin/env sh
exec $PYTHON "$CLIENT_DIR/xiaoyuan_client.py" "\$@"
EOF
chmod +x "$INSTALL_DIR/xiaoyuan"

echo "Xiaoyuan public client installed: $INSTALL_DIR"
echo "Add this directory to PATH if needed: $INSTALL_DIR"
echo "Next:"
echo "  $INSTALL_DIR/xiaoyuan install"
echo "  $INSTALL_DIR/xiaoyuan login"
echo "  $INSTALL_DIR/xiaoyuan doctor --strict"
echo "  $INSTALL_DIR/xiaoyuan start"
