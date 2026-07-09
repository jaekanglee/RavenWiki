#!/usr/bin/env bash
# Linux install branch — invoked by ./_meta/install.sh when OSTYPE=linux*
set -euo pipefail

echo "🐧 Linux Raven 설치 시작"
echo ""

SUDO=""
[[ $EUID -ne 0 ]] && SUDO="sudo"

if command -v apt &> /dev/null; then
    echo "📦 apt (Debian/Ubuntu) 감지"
    $SUDO apt update
    $SUDO apt install -y python3 git curl make docker.io docker-compose-plugin
elif command -v dnf &> /dev/null; then
    echo "📦 dnf (Fedora/RHEL) 감지"
    $SUDO dnf install -y python3 git curl make docker docker-compose-plugin
else
    echo "❌ apt/dnf 모두 없음. 수동 설치 필요."
    echo "   Debian/Ubuntu: apt install python3 git curl make docker.io docker-compose-plugin"
    echo "   Fedora/RHEL:   dnf install python3 git curl make docker docker-compose-plugin"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker CLI 설치 실패"
    exit 1
fi

if command -v systemctl &> /dev/null; then
    $SUDO systemctl enable --now docker >/dev/null 2>&1 || true
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
    echo "📥 Raven repo clone: $REPO → $APP_DIR"
    git clone "$REPO" "$APP_DIR"
else
    echo "✅ repo 이미 존재: $APP_DIR"
fi

mkdir -p "$RAVEN_VAULTS_DIR"
echo "✅ vault root 준비: $RAVEN_VAULTS_DIR"

cd "$APP_DIR"

if [[ ! -f .env ]]; then
    cp .env.example.house .env
    echo "✅ .env 생성 (집/개인 프로필 기준 — 팀과 함께 쓰는 사내망이면 .env.example.company 참고해 직접 조정할 것)"
fi

python3 - "$APP_DIR/.env" "$RAVEN_VAULTS_DIR" <<'PY'
from pathlib import Path
import sys

env_path = Path(sys.argv[1])
vault_dir = sys.argv[2]
lines = env_path.read_text().splitlines()
out = []
found = False
for line in lines:
    if line.startswith("RAVEN_VAULTS_DIR="):
        out.append(f"RAVEN_VAULTS_DIR={vault_dir}")
        found = True
    else:
        out.append(line)
if not found:
    out.append(f"RAVEN_VAULTS_DIR={vault_dir}")
env_path.write_text("\n".join(out) + "\n")
PY
echo "✅ .env의 RAVEN_VAULTS_DIR 설정 완료"

echo "🐳 Docker daemon 확인..."
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker daemon이 실행 중이 아닙니다."
    echo "   필요시: sudo systemctl start docker"
    exit 1
fi

echo "🔨 Raven 이미지 빌드 + 기동..."
make rebuild

echo ""
echo "✅ Linux 설치 완료"
echo "🌐 Dashboard: http://localhost:5173"
echo "🔌 API:       http://localhost:8765/api/vaults"
echo "🧠 MCP HTTP:  http://localhost:8766/mcp"
echo "📋 상태 확인: cd $APP_DIR && docker compose ps"
