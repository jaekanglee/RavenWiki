#!/usr/bin/env bash
# raven.sh — Control script for starting, stopping, and restarting the Raven local host stack.

# Exit on error
set -e

# Directory where this script resides
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

PID_DIR="tmp"
API_PID="$PID_DIR/api.pid"
DASHBOARD_PID="$PID_DIR/dashboard.pid"

mkdir -p "$PID_DIR"

# Find python runner
if [ -d "scripts/.venv" ]; then
  PY="scripts/.venv/bin/python"
elif command -v uv &> /dev/null; then
  PY="uv run python"
else
  PY="python3"
fi

status() {
  local api_running=false
  local db_running=false
  
  if [ -f "$API_PID" ] && kill -0 $(cat "$API_PID") 2>/dev/null; then
    api_running=true
  fi
  if [ -f "$DASHBOARD_PID" ] && kill -0 $(cat "$DASHBOARD_PID") 2>/dev/null; then
    db_running=true
  fi
  
  if $api_running && $db_running; then
    echo "🟢 Raven is RUNNING"
    echo "   • API PID: $(cat "$API_PID")"
    echo "   • Dashboard PID: $(cat "$DASHBOARD_PID")"
    echo "   • API Url: http://127.0.0.1:8765"
    echo "   • Dashboard Url: http://localhost:5173"
    return 0
  elif $api_running || $db_running; then
    echo "🟡 Raven is PARTIALLY RUNNING (API: $api_running, Dashboard: $db_running)"
    return 1
  else
    echo "🔴 Raven is STOPPED"
    return 2
  fi
}

start() {
  if [ -f "$API_PID" ] && kill -0 $(cat "$API_PID") 2>/dev/null; then
    echo "⚠️  API server is already running (PID: $(cat "$API_PID"))"
  else
    echo "🚀 Starting API server in background..."
    PYTHONPATH=. $PY -m raven.api > tmp/api.log 2>&1 &
    echo $! > "$API_PID"
  fi
  
  if [ -f "$DASHBOARD_PID" ] && kill -0 $(cat "$DASHBOARD_PID") 2>/dev/null; then
    echo "⚠️  Dashboard is already running (PID: $(cat "$DASHBOARD_PID"))"
  else
    echo "🚀 Starting Dashboard Vite dev server in background..."
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
