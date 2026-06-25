#!/usr/bin/env bash
# Linux install branch — invoked by ./install.sh when OSTYPE=linux*
# Supports: apt (Debian/Ubuntu) or dnf (Fedora/RHEL)
set -euo pipefail

echo "🐧 Linux 설치 시작"
echo ""

# ─── 1. 시스템 패키지 ─────────────────────────────────────────────
if command -v apt &> /dev/null; then
    echo "📦 apt (Debian/Ubuntu) 감지"
    SUDO=""
    [[ $EUID -ne 0 ]] && SUDO="sudo"
    $SUDO apt update
    $SUDO apt install -y python3.11 python3-venv python3-pip nodejs npm git curl
elif command -v dnf &> /dev/null; then
    echo "📦 dnf (Fedora/RHEL) 감지"
    SUDO=""
    [[ $EUID -ne 0 ]] && SUDO="sudo"
    $SUDO dnf install -y python3.11 nodejs npm git curl
else
    echo "❌ apt/dnf 모두 없음. 수동 설치 필요."
    echo "   Debian/Ubuntu: apt install python3 python3-venv nodejs npm git curl"
    echo "   Fedora/RHEL:   dnf install python3 nodejs npm git curl"
    exit 1
fi

# ─── 2. Tailscale (선택) ──────────────────────────────────────────
if ! command -v tailscale &> /dev/null; then
    echo "📦 Tailscale 설치 (외부 접근용)..."
    curl -fsSL https://tailscale.com/install.sh | $SUDO sh
    echo "🔐 Tailscale 로그인: sudo tailscale up"
fi

# ─── 3. vault clone ───────────────────────────────────────────────
if [[ ! -d "$VAULT" ]]; then
    echo "📥 Vault clone: $REPO → $VAULT"
    git clone "$REPO" "$VAULT"
else
    echo "✅ Vault 이미 존재: $VAULT"
fi

cd "$VAULT"

# ─── 4. Python venv ───────────────────────────────────────────────
echo "🐍 Python venv..."
python3 -m venv scripts/.venv
scripts/.venv/bin/pip install --upgrade pip
scripts/.venv/bin/pip install -e "scripts[dev]"

# ─── 5. Dashboard 빌드 ────────────────────────────────────────────
echo "📦 Dashboard 의존성 + 빌드..."
cd dashboard
npm install
npm run build
cd ..

# ─── 6. 데이터 export ─────────────────────────────────────────────
echo "📊 데이터 빌드 + export..."
scripts/.venv/bin/python scripts/build_db.py
scripts/.venv/bin/python scripts/export_static.py

# ─── 7. 초기 백업 ─────────────────────────────────────────────────
echo "💾 초기 백업..."
scripts/.venv/bin/python scripts/backup_db.py

# ─── 8. systemd 등록 ──────────────────────────────────────────────
echo "🚀 systemd 등록..."
$SUDO mkdir -p /etc/systemd/system
$SUDO cp deploy/systemd/wiki-dashboard.service   /etc/systemd/system/
$SUDO cp deploy/systemd/wiki-mcp.service         /etc/systemd/system/
$SUDO cp deploy/systemd/wiki-backup.service      /etc/systemd/system/
$SUDO cp deploy/systemd/wiki-backup.timer        /etc/systemd/system/ 2>/dev/null || true

$SUDO systemctl daemon-reload
$SUDO systemctl enable --now wiki-dashboard.service wiki-mcp.service
$SUDO systemctl enable --now wiki-backup.timer   2>/dev/null || true

# ─── 9. 로그 디렉토리 ─────────────────────────────────────────────
mkdir -p "$VAULT/logs"

echo ""
echo "✅ Linux 설치 완료"
echo "🌐 Dashboard: http://localhost:5173"
echo "📊 MCP http:  scripts/.venv/bin/python -m mcp.cli --transport http --port 8765"
echo "📋 상태 확인: sudo systemctl status wiki-dashboard wiki-mcp"
echo "📋 백업 로그: sudo journalctl -u wiki-backup.service"
