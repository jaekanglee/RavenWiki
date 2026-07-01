#!/usr/bin/env bash
# Wiki System Installer
# ----------------------
# macOS  → brew + LaunchAgent
# Linux  → apt/dnf + systemd
#
# Usage:
#   ./install.sh                    # install to $HOME/wiki
#   VAULT=/path ./install.sh        # install to custom path
#   REPO=git@github.com:me/wiki.git ./install.sh
#
# Env vars:
#   VAULT        — target install path (default: $HOME/wiki)
#   REPO         — git URL of the vault (default: GitHub placeholder)
#   SERVICE_USER — user to run services as (default: $SUDO_USER or $USER)

set -euo pipefail

VAULT="${VAULT:-$HOME/wiki}"
REPO="${REPO:-https://github.com/<user>/wiki.git}"
SERVICE_USER="${SUDO_USER:-$USER}"

# Resolve script directory (works when called via curl-pipe too)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

echo "🚀 Wiki System Installer"
echo "─────────────────────────"
echo "📁 Vault:        $VAULT"
echo "👤 Service user: $SERVICE_USER"
echo "🖥  OS:          ${OSTYPE}"
echo "📦 Repo:         $REPO"
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
echo "✅ Wiki install complete"
echo "🌐 Dashboard: http://localhost:5173 (after service start)"
echo "📊 MCP stdio: python3 -m mcp.cli"
echo "📊 MCP http:  python3 -m mcp.cli --transport http --port 8765"
