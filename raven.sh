#!/usr/bin/env bash
# raven.sh — Control script for starting, stopping, and restarting the Raven local host stack.
#
# v0.7.83+: API → 8765 (그대로), MCP → 8766, Dashboard → 5173 (v0.7.81+ HTTP only).
# MCP lifecycle 통합 — silent stale 방지 (v0.7.82 hotfix). 운영자가 lifecycle
# 수동 관리 안 해도 `make restart-all` / `./raven.sh restart`가 자동 처리.
#
# 포트 매트릭스 (v0.7.83+):
#   API:       8765 (RAVEN_API_PORT) — Dashboard가 Vite proxy로 호출
#   MCP:       8766 (RAVEN_MCP_PORT, v0.7.81+ HTTP only 정책)
#   Dashboard: 5173 (RAVEN_DASHBOARD_PORT, Vite dev)
#
# Exit on error
set -e

# Directory where this script resides
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

PID_DIR="tmp"
API_PID="$PID_DIR/api.pid"
DASHBOARD_PID="$PID_DIR/dashboard.pid"
MCP_PID="$PID_DIR/mcp.pid"

API_PORT="${RAVEN_API_PORT:-8765}"
MCP_PORT="${RAVEN_MCP_PORT:-8766}"
MCP_MODE="${RAVEN_MCP_MODE:-read}"
DASHBOARD_PORT="${RAVEN_DASHBOARD_PORT:-5173}"

mkdir -p "$PID_DIR"

# Find python runner
if [ -d "scripts/.venv" ]; then
  PY="scripts/.venv/bin/python"
elif command -v uv &> /dev/null; then
  PY="uv run python"
else
  PY="python3"
fi

# status() helper: PID의 process args에서 --mode 값을 추출 (env 의존 0).
# silent hotfix (v0.7.85+): status() 호출 시 RAVEN_MCP_MODE env가 export되지 않으면
# $MCP_MODE가 fallback(read)로 표시되는 버그. 실제 process args에서 직접 파싱.
mcp_mode_from_pid() {
  local pid="$1"
  if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
    echo ""
    return
  fi
  # macOS ps: -o args= 형식 / Linux ps: -o cmd= 형식 모두 호환
  ps -p "$pid" -o args= 2>/dev/null | tr " " "\n" | grep -A1 "^--mode$" | tail -1
}

status() {
  local api_running=false
  local db_running=false
  local mcp_running=false
  local mcp_mode_display=""

  if [ -f "$API_PID" ] && kill -0 $(cat "$API_PID") 2>/dev/null; then
    api_running=true
  fi
  if [ -f "$DASHBOARD_PID" ] && kill -0 $(cat "$DASHBOARD_PID") 2>/dev/null; then
    db_running=true
  fi
  if [ -f "$MCP_PID" ] && kill -0 $(cat "$MCP_PID") 2>/dev/null; then
    mcp_running=true
    mcp_mode_display="$(mcp_mode_from_pid "$(cat "$MCP_PID")")"
  fi

  if $api_running && $db_running && $mcp_running; then
    echo "🟢 Raven is RUNNING"
    echo "   • API PID: $(cat "$API_PID")       Url: http://127.0.0.1:$API_PORT"
    echo "   • Dashboard PID: $(cat "$DASHBOARD_PID") Url: http://localhost:$DASHBOARD_PORT"
    echo "   • MCP PID: $(cat "$MCP_PID")          Url: http://127.0.0.1:$MCP_PORT/mcp (mode=${mcp_mode_display:-?})"
    return 0
  elif $api_running || $db_running || $mcp_running; then
    echo "🟡 Raven is PARTIALLY RUNNING (API: $api_running, Dashboard: $db_running, MCP: $mcp_running)"
    return 1
  else
    echo "🔴 Raven is STOPPED"
    return 2
  fi
}

start() {
  # API (8765)
  if [ -f "$API_PID" ] && kill -0 $(cat "$API_PID") 2>/dev/null; then
    echo "⚠️  API server is already running (PID: $(cat "$API_PID"))"
  else
    echo "🚀 Starting API server in background on port $API_PORT..."
    PYTHONPATH=. $PY -m raven.api > tmp/api.log 2>&1 &
    echo $! > "$API_PID"
  fi

  # MCP (8766, HTTP only, v0.7.81+)
  if [ -f "$MCP_PID" ] && kill -0 $(cat "$MCP_PID") 2>/dev/null; then
    echo "⚠️  MCP server is already running (PID: $(cat "$MCP_PID"))"
  else
    echo "🚀 Starting MCP server in background on port $MCP_PORT (mode=$MCP_MODE)..."
    PYTHONPATH=. $PY -m raven.mcp.cli \
      --transport http --host 127.0.0.1 --port "$MCP_PORT" --mode "$MCP_MODE" > tmp/mcp.log 2>&1 &
    echo $! > "$MCP_PID"
  fi

  # Dashboard (5173)
  if [ -f "$DASHBOARD_PID" ] && kill -0 $(cat "$DASHBOARD_PID") 2>/dev/null; then
    echo "⚠️  Dashboard is already running (PID: $(cat "$DASHBOARD_PID"))"
  else
    echo "🚀 Starting Dashboard Vite dev server in background on port $DASHBOARD_PORT..."
    cd dashboard
    npm run dev > ../tmp/dashboard.log 2>&1 &
    echo $! > "../$DASHBOARD_PID"
    cd ..
  fi

  sleep 2
  status
}

stop() {
  echo "🛑 Stopping Raven local host stack..."
  if [ -f "$API_PID" ]; then
    local pid=$(cat "$API_PID")
    echo "   Stopping API (PID: $pid)..."
    kill "$pid" 2>/dev/null || true
    rm -f "$API_PID"
  fi
  if [ -f "$MCP_PID" ]; then
    local pid=$(cat "$MCP_PID")
    echo "   Stopping MCP (PID: $pid)..."
    kill "$pid" 2>/dev/null || true
    rm -f "$MCP_PID"
  fi
  if [ -f "$DASHBOARD_PID" ]; then
    local pid=$(cat "$DASHBOARD_PID")
    echo "   Stopping Dashboard (PID: $pid)..."
    kill "$pid" 2>/dev/null || true
    rm -f "$DASHBOARD_PID"
  fi
  echo "🔴 Stopped."
}

restart() {
  stop
  sleep 1
  start
}

case "$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart)
    restart
    ;;
  status)
    status
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac