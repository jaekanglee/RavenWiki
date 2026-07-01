#!/usr/bin/env bash
# Raven System Installer
# ---------------------
# Current standard: repo clone + Docker-first bootstrap.
# This installer intentionally does NOT provision legacy launchd/systemd services.
#
# Usage:
#   ./_meta/install.sh
#   APP_DIR=/path/to/Raven ./_meta/install.sh
#   REPO=git@github.com:me/Raven.git ./_meta/install.sh
#   RAVEN_VAULTS_DIR=/data/Raven ./_meta/install.sh
#
# Env vars:
#   APP_DIR          — repo checkout path (default: $HOME/Raven-app)
#   REPO             — git URL of the Raven repo
#   RAVEN_VAULTS_DIR — vault root path (default: $HOME/Raven)

set -euo pipefail

APP_DIR="${APP_DIR:-${VAULT:-$HOME/Raven-app}}"
REPO="${REPO:-https://github.com/<user>/Raven.git}"
RAVEN_VAULTS_DIR="${RAVEN_VAULTS_DIR:-$HOME/Raven}"
SERVICE_USER="${SUDO_USER:-$USER}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

export APP_DIR REPO RAVEN_VAULTS_DIR SERVICE_USER

echo "🚀 Raven System Installer"
echo "────────────────────────"
echo "📦 Repo:         $REPO"
echo "📁 App dir:      $APP_DIR"
echo "🗂  Vault root:   $RAVEN_VAULTS_DIR"
echo "👤 Service user: $SERVICE_USER"
echo "🖥  OS:          ${OSTYPE}"
echo ""
echo "ℹ️  This installer bootstraps the current Docker-first Raven stack."
echo "   Legacy launchd/systemd service templates are not installed here."
echo ""

if [[ "${OSTYPE}" == "darwin"* ]]; then
    source "$SCRIPT_DIR/../install/macos.sh"
elif [[ "${OSTYPE}" == "linux-gnu"* ]] || [[ "${OSTYPE}" == "linux"* ]]; then
    source "$SCRIPT_DIR/../install/linux.sh"
else
    echo "❌ Unsupported OS: $OSTYPE"
    echo "   Supported: macOS (darwin*), Linux (linux*)"
    exit 1
fi

echo ""
echo "✅ Raven install complete"
echo "🌐 Dashboard: http://localhost:5173"
echo "🔌 API:       http://localhost:8765/api/vaults"
echo "🧠 MCP HTTP:  http://localhost:8766/mcp"
echo "💻 CLI:       docker compose exec api docker-entrypoint.sh cli <args>"
