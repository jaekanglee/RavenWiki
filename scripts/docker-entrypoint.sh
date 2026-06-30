#!/usr/bin/env bash
# docker-entrypoint.sh — 컨테이너 안에서 4 진입점 라우팅.
# CMD 환경변수로 진입점 전환 (api | mcp-http | mcp-stdio | dashboard | cli).
set -e

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
