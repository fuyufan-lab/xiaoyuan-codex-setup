#!/bin/bash
# ============================================
#  Xiaoyuan x Qoder CPOS Pipeline Setup
#  macOS / Linux one-command install:
#    curl -fsSL https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/qoder-config/install.sh | bash
# ============================================

set -e

REPO="https://raw.githubusercontent.com/fuyufan-lab/xiaoyuan-codex-setup/main/qoder-config"
QODER_DIR="${HOME}/.qoder"

echo ""
echo "============================================"
echo "  Xiaoyuan x Qoder CPOS Pipeline Setup"
echo "============================================"
echo ""

# 创建目录
mkdir -p "${QODER_DIR}/rules"
mkdir -p "${QODER_DIR}/skills/cpos-pipeline"
mkdir -p "${QODER_DIR}/skills/swarm-dispatch"
mkdir -p "${QODER_DIR}/skills/cpos-execute"
mkdir -p "${QODER_DIR}/agents"
mkdir -p "${QODER_DIR}/cpos"

declare -A FILES=(
    ["rules/always-cpos.md"]="${QODER_DIR}/rules/always-cpos.md"
    ["skills/cpos-pipeline/SKILL.md"]="${QODER_DIR}/skills/cpos-pipeline/SKILL.md"
    ["skills/swarm-dispatch/SKILL.md"]="${QODER_DIR}/skills/swarm-dispatch/SKILL.md"
    ["skills/cpos-execute/SKILL.md"]="${QODER_DIR}/skills/cpos-execute/SKILL.md"
    ["agents/coder.md"]="${QODER_DIR}/agents/coder.md"
    ["cpos/runner.py"]="${QODER_DIR}/cpos/runner.py"
)

ok=0
fail=0

for src in "${!FILES[@]}"; do
    dst="${FILES[$src]}"
    url="${REPO}/${src}"
    printf "  [..] %s ..." "${src}"
    if curl -fsSL --connect-timeout 15 --max-time 30 "${url}" -o "${dst}" 2>/dev/null; then
        echo " OK"
        ((ok++))
    else
        echo " FAIL"
        ((fail++))
    fi
done

echo ""
echo "============================================"
echo "  Result: ${ok} ok, ${fail} failed"
echo "  Installed to: ${QODER_DIR}"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Restart Qoder (Yuan) IDE"
echo "  2. Open any project, CPOS pipeline activates automatically"
echo "  3. You should see [CPOS: ...] header in responses"
echo ""
echo "Docs: https://github.com/fuyufan-lab/xiaoyuan-codex-setup/tree/main/qoder-config"
