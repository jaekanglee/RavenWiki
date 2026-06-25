#!/usr/bin/env bash
# deploy.sh — 로컬 변경사항을 VPS에 배포
# -----------------------------------------------------------
# 사용법:
#   VPS=user@100.x.x.x ./scripts/deploy.sh
#   VPS=user@wiki.example.com BRANCH=main ./scripts/deploy.sh
#
# 환경변수:
#   VPS       — 필수. ssh 접속 대상 (user@host)
#   BRANCH    — git 브랜치 (기본: main)
#   VAULT     — VPS 내 vault 경로 (기본: ~/wiki)
#   SKIP_PUSH — 1이면 git push 건너뜀
#
# 흐름:
#   1. 로컬에서 git push
#   2. VPS에서 git pull
#   3. Python 의존성 갱신
#   4. Dashboard 재빌드
#   5. DB + 정적 export 재실행
#   6. systemd 서비스 재시작

set -euo pipefail

# ── 인자 검증 ─────────────────────────────────────────────────────
: "${VPS:?VPS 환경변수 필요 (예: VPS=user@100.x.x.x)}"

VAULT_LOCAL="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH="${BRANCH:-main}"
REMOTE_VAULT="${VAULT:-~/wiki}"
SKIP_PUSH="${SKIP_PUSH:-0}"

echo "🚀 Wiki Deploy"
echo "──────────────────────────────────────"
echo "📁 Local:  $VAULT_LOCAL"
echo "🌐 VPS:    $VPS"
echo "📂 Remote: $REMOTE_VAULT"
echo "🌿 Branch: $BRANCH"
echo ""

# ── 1. 로컬 git push ──────────────────────────────────────────────
if [[ "$SKIP_PUSH" != "1" ]]; then
    echo "📤 git push origin $BRANCH..."
    if ! git push origin "$BRANCH"; then
        echo "❌ git push 실패"
        echo "   팁: SKIP_PUSH=1 로 로컬 변경 없이 강제 배포 가능"
        exit 1
    fi
else
    echo "⏭️  git push 건너뜀 (SKIP_PUSH=1)"
fi

# ── 2. VPS에서 pull + rebuild + restart ───────────────────────────
echo ""
echo "🌐 VPS 작업 시작..."
ssh "$VPS" "REMOTE_VAULT=$REMOTE_VAULT BRANCH=$BRANCH" << 'REMOTE_EOF'
set -e
REMOTE_VAULT="${REMOTE_VAULT:-~/wiki}"
BRANCH="${BRANCH:-main}"

cd "$REMOTE_VAULT" || { echo "❌ $REMOTE_VAULT 없음"; exit 1; }

echo "📥 git pull origin $BRANCH..."
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "🐍 Python 의존성 갱신..."
scripts/.venv/bin/pip install -e "scripts[dev]" --quiet

echo "📦 Dashboard 재빌드..."
cd dashboard
npm install --silent
npm run build
cd ..

echo "📊 Data rebuild..."
scripts/.venv/bin/python scripts/build_db.py
scripts/.venv/bin/python scripts/export_static.py

echo "💾 백업..."
scripts/.venv/bin/python scripts/backup_db.py

# systemd가 있을 때만 재시작 (개발 환경엔 없을 수 있음)
if command -v systemctl &> /dev/null; then
    echo "🔄 Services restart..."
    sudo systemctl restart wiki-dashboard.service wiki-mcp.service
    echo "📋 상태: sudo systemctl status wiki-dashboard"
else
    echo "⚠️  systemctl 없음 — 수동 재시작 필요"
fi

echo "✅ VPS 작업 완료"
REMOTE_EOF

echo ""
echo "──────────────────────────────────────"
echo "✅ Deploy 완료"
echo "🌐 Dashboard: http://${VPS#*@}:5173"
echo "📋 로그 확인: ssh $VPS 'sudo journalctl -u wiki-dashboard -n 50'"
