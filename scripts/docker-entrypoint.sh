#!/usr/bin/env bash
# docker-entrypoint.sh — 컨테이너 안에서 4 진입점 라우팅.
# CMD 환경변수로 진입점 전환 (api | mcp-http | mcp-stdio | dashboard | cli).
set -e

# v0.7.19+: vault path 정합성 보장
# - Python code는 $WIKI_VAULTS_DIR 환경변수 사용 (registry.py:4, 10, 34)
# - entrypoint에서 export → 자식 프로세스 (python -m raven.*) 에게 상속
# - 환경변수 override 가능 (사용자 .env에 WIKI_VAULTS_DIR 설정)
# - RAVEN_VAULTS_DIR도 alias로 인정 (Docker compose 호환)
# - v0.7.19+: default 경로 = $HOME/Raven (컨테이너 안, bind mount로 호스트 ~/Raven에 연결)
WIKI_VAULTS_DIR="${WIKI_VAULTS_DIR:-${RAVEN_VAULTS_DIR:-$HOME/Raven}}"
RAVEN_VAULTS_DIR="$WIKI_VAULTS_DIR"
export WIKI_VAULTS_DIR RAVEN_VAULTS_DIR

# v0.7.19+: vault 폴더 검증 (bind mount가 호스트 폴더 보장)
# - 정상: 호스트 ~/Raven 존재 → 컨테이너 안 $WIKI_VAULTS_DIR mount → 즉시 사용 가능
# - 비정상: 호스트 폴더 없음 → mount는 빈 디렉토리 → registry.json 없음 → vault 0건
#   → 사용자 안내 (mkdir 권장)
if [ ! -d "$WIKI_VAULTS_DIR" ]; then
    echo "⚠️  vault 폴더 없음: $WIKI_VAULTS_DIR"
    echo "   권장: mkdir -p \"$WIKI_VAULTS_DIR\" (호스트에서 실행)"
fi

case "$1" in
    api)
        exec python -m raven.api --host "$HOST" --port "$PORT_API"
        ;;
    mcp-http)
        exec python -m raven.mcp.cli --transport http --host "$HOST" --port "$PORT_MCP_HTTP"
        ;;
    mcp-stdio)
        exec python -m raven.mcp.cli --transport stdio
        ;;
    dashboard)
        # 정적 dashboard 서빙은 nginx 같은 reverse proxy가 더 적합하지만
        # 단순화: Vite preview 또는 정적 http.server
        # 컨테이너 환경에선 단순 python http.server 사용
        cd /app/dashboard/dist
        exec python -m http.server "$PORT_DASHBOARD" --bind "$HOST"
        ;;
    cli)
        # CLI는 대화형 — exec로 사용자에게 위임
        shift
        exec python -m raven.cli "$@"
        ;;
    *)
        echo "Usage: docker-entrypoint.sh {api|mcp-http|mcp-stdio|dashboard|cli} [args...]"
        exit 1
        ;;
esac
