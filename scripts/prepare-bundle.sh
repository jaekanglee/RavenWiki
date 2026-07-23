#!/usr/bin/env bash
# Prepare bundled Python + Raven source for Tauri .app packaging.
# Usage: bash scripts/prepare-bundle.sh
#
# Creates desktop/src-tauri/resources/{python,raven}/ for Tauri bundle.resources.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RESOURCES="$REPO_ROOT/desktop/src-tauri/resources"
PYTHON_VERSION="3.13.14"
PBS_TAG="20260718"

# Detect architecture
ARCH="$(uname -m)"
case "$ARCH" in
  arm64)  PBS_TARGET="aarch64-apple-darwin" ;;
  x86_64) PBS_TARGET="x86_64-apple-darwin" ;;
  *)      echo "Unsupported arch: $ARCH" >&2; exit 1 ;;
esac

PBS_NAME="cpython-${PYTHON_VERSION}+${PBS_TAG}-${PBS_TARGET}-install_only.tar.gz"
PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/${PBS_NAME}"

echo "=== Raven Desktop Bundle Preparation ==="
echo "Target: $PBS_TARGET (Python $PYTHON_VERSION)"
echo ""

# Clean previous resources
rm -rf "$RESOURCES"
mkdir -p "$RESOURCES"

# 1. Download python-build-standalone
echo "[1/4] Downloading python-build-standalone..."
TMPDIR_BUNDLE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_BUNDLE"' EXIT

if [ -f "$REPO_ROOT/.cache/${PBS_NAME}" ]; then
  echo "  Using cached: .cache/${PBS_NAME}"
  cp "$REPO_ROOT/.cache/${PBS_NAME}" "$TMPDIR_BUNDLE/"
else
  echo "  Downloading from GitHub..."
  mkdir -p "$REPO_ROOT/.cache"
  curl -L --progress-bar -o "$TMPDIR_BUNDLE/${PBS_NAME}" "$PBS_URL"
  cp "$TMPDIR_BUNDLE/${PBS_NAME}" "$REPO_ROOT/.cache/${PBS_NAME}"
fi

echo "[2/4] Extracting Python..."
tar -xzf "$TMPDIR_BUNDLE/${PBS_NAME}" -C "$TMPDIR_BUNDLE"
mv "$TMPDIR_BUNDLE/python" "$RESOURCES/python"

# Verify
"$RESOURCES/python/bin/python3" --version

# 3. Install dependencies
echo "[3/4] Installing dependencies into bundled Python..."
BUNDLED_PIP="$RESOURCES/python/bin/python3 -m pip"

# Core runtime dependencies (no dev/test deps)
$BUNDLED_PIP install --quiet --no-cache-dir \
  "fastapi>=0.115" \
  "uvicorn[standard]>=0.34" \
  "mcp>=1.28" \
  "python-frontmatter>=1.1" \
  "PyYAML>=6.0" \
  "jsonschema>=4.24" \
  "rich>=14.0" \
  "typer>=0.15" \
  "python-dotenv>=1.1" \
  "httpx>=0.27"

echo "  Installed packages:"
$BUNDLED_PIP list --format=columns 2>/dev/null | wc -l | xargs echo "   "

# 4. Copy Raven source
echo "[4/4] Copying Raven source..."
mkdir -p "$RESOURCES/raven"
cp -R "$REPO_ROOT/raven" "$RESOURCES/raven/raven"

# Remove __pycache__ and test artifacts
find "$RESOURCES/raven" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$RESOURCES/raven" -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "=== Bundle ready ==="
echo "Resources: $RESOURCES"
du -sh "$RESOURCES/python" "$RESOURCES/raven" 2>/dev/null
echo ""
echo "Next: cd desktop && npm run desktop:build"
