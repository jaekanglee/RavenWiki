#!/usr/bin/env bash
# Raven — one-liner install
#
#   curl -fsSL <raw-url>/scripts/install.sh | bash
#
# Clones the repo (if not already inside it), sets up Python venv,
# installs deps, and builds the dashboard.
set -euo pipefail

REPO_URL="${RAVEN_REPO_URL:-https://github.com/jaekanglee/Raven.git}"
INSTALL_DIR="${RAVEN_INSTALL_DIR:-$HOME/Raven}"

# --- detect: inside repo already, or fresh clone? ---
if [ -f "$(pwd)/raven/__init__.py" ]; then
  ROOT="$(pwd)"
  echo "=== Raven install (in-repo) ==="
else
  ROOT="$INSTALL_DIR"
  echo "=== Raven install → $ROOT ==="
  if [ -d "$ROOT/.git" ]; then
    echo "--- pulling latest ---"
    git -C "$ROOT" pull --ff-only
  else
    echo "--- cloning ---"
    git clone --depth 1 "$REPO_URL" "$ROOT"
  fi
fi
cd "$ROOT"

# --- prerequisites ---
command -v python3 >/dev/null || { echo "ERROR: python3 not found"; exit 1; }
command -v node    >/dev/null || { echo "ERROR: node not found (need >=18)"; exit 1; }
command -v git     >/dev/null || { echo "ERROR: git not found"; exit 1; }

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  python: $PY_VER  node: $(node -v)"

# --- Python venv + deps ---
VENV="$ROOT/scripts/.venv"
if [ ! -d "$VENV" ]; then
  echo "--- creating venv ---"
  python3 -m venv "$VENV"
fi
echo "--- installing python deps ---"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r requirements.txt

# --- Dashboard build ---
echo "--- building dashboard ---"
cd "$ROOT/dashboard"
npm install --silent
npm run build --silent

# --- done ---
echo ""
echo "=== install complete ==="
echo ""
echo "  Start API server:"
echo "    $VENV/bin/python -m raven.api"
echo ""
echo "  Start with external access (Tailscale/LAN):"
echo "    $VENV/bin/python -m raven.api --host 0.0.0.0"
echo ""
echo "  CLI:"
echo "    $VENV/bin/python -m raven --help"
echo ""
echo "  Dashboard (after API start):"
echo "    http://127.0.0.1:8765"
