#!/usr/bin/env bash
# macOS install branch — invoked by ./install.sh when OSTYPE=darwin*
set -euo pipefail

echo "🍎 macOS 설치 시작"
echo ""

# 1. Homebrew 확인
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew 미설치. 설치 명령어:"
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi
echo "✅ Homebrew 발견"

# 2. 시스템 패키지
echo "📦 Brew 패키지 설치..."
brew install python@3.11 node git

# 3. Tailscale (선택)
if ! command -v tailscale &> /dev/null; then
    echo "📦 Tailscale 설치 (외부 접근용)..."
    brew install --cask tailscale
    echo "🔐 Tailscale 로그인 필요: 메뉴바 → Tailscale → Log In"
fi

# 4. vault clone
if [[ ! -d "$VAULT" ]]; then
    echo "📥 Vault clone: $REPO → $VAULT"
    git clone "$REPO" "$VAULT"
else
    echo "✅ Vault 이미 존재: $VAULT"
fi

cd "$VAULT"

# 5. Python venv
if [[ ! -d scripts/.venv ]]; then
    echo "🐍 Python venv 생성..."
    python3 -m venv scripts/.venv
    scripts/.venv/bin/pip install --upgrade pip
    scripts/.venv/bin/pip install -e "scripts[dev]"
else
    echo "✅ venv 이미 존재"
fi

# 6. dashboard 의존성 + 빌드
echo "📦 Dashboard 의존성 설치 + 빌드..."
cd dashboard
if [[ ! -d node_modules ]]; then
    npm install
fi
npm run build
cd ..

# 7. 데이터 export
echo "📊 데이터 빌드 + export..."
scripts/.venv/bin/python scripts/build_db.py
scripts/.venv/bin/python scripts/export_static.py

# 8. 초기 백업
echo "💾 초기 백업..."
scripts/.venv/bin/python scripts/backup_db.py

# 9. LaunchAgent 등록
echo "🚀 LaunchAgent 등록..."
LAUNCH_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_DIR" "$VAULT/logs"

PLIST_TEMPLATE="$VAULT/deploy/launchd/com.wiki.dashboard.plist"
PLIST_TARGET="$LAUNCH_DIR/com.wiki.dashboard.plist"

if [[ ! -f "$PLIST_TEMPLATE" ]]; then
    echo "❌ plist 템플릿 없음: $PLIST_TEMPLATE"
    exit 1
fi

# {{VAULT}} → 절대경로 치환
sed "s|{{VAULT}}|$VAULT|g" "$PLIST_TEMPLATE" > "$PLIST_TARGET"

launchctl unload "$PLIST_TARGET" 2>/dev/null || true
launchctl load "$PLIST_TARGET"

echo ""
echo "✅ macOS 설치 완료"
echo "🌐 Dashboard: http://localhost:5173"
echo "📊 MCP stdio: cd $VAULT && scripts/.venv/bin/python -m mcp.cli"
echo "📋 Logs:      $VAULT/logs/dashboard.log"
