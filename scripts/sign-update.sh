#!/usr/bin/env bash
# Package + sign a tauri-plugin-updater artifact from the already-built Raven.app,
# and emit the latest.json manifest the desktop app polls at startup.
#
# Expects: make desktop-dmg already run (Raven.app present)
# Requires env:
#   TAURI_SIGNING_PRIVATE_KEY           path to the private key from `tauri signer generate`
#   TAURI_SIGNING_PRIVATE_KEY_PASSWORD  optional, if the key was generated with a password
#
# Usage: bash scripts/sign-update.sh <version> <owner/repo>
set -euo pipefail

VERSION="${1:?usage: sign-update.sh <version> <owner/repo>}"
REPO_SLUG="${2:?usage: sign-update.sh <version> <owner/repo>}"
: "${TAURI_SIGNING_PRIVATE_KEY:?TAURI_SIGNING_PRIVATE_KEY (path to signer private key) must be set}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAURI_DIR="$REPO_ROOT/desktop/src-tauri"
APP_DIR="$TAURI_DIR/target/release/bundle/macos/Raven.app"
UPDATE_DIR="$TAURI_DIR/target/release/bundle/updater"
ARTIFACT="$UPDATE_DIR/Raven.app.tar.gz"
TAURI_CLI="$REPO_ROOT/dashboard/node_modules/.bin/tauri"

[ -d "$APP_DIR" ] || { echo "❌ Raven.app not found: $APP_DIR (run: make desktop-dmg)"; exit 1; }
[ -x "$TAURI_CLI" ] || { echo "❌ tauri CLI not found — run 'npm ci' in dashboard/"; exit 1; }

mkdir -p "$UPDATE_DIR"
rm -f "$ARTIFACT" "$ARTIFACT.sig"

echo "=== Packaging update artifact ==="
tar czf "$ARTIFACT" -C "$(dirname "$APP_DIR")" "Raven.app"

echo "=== Signing update artifact ==="
"$TAURI_CLI" signer sign \
  -k "$TAURI_SIGNING_PRIVATE_KEY" \
  ${TAURI_SIGNING_PRIVATE_KEY_PASSWORD:+-p "$TAURI_SIGNING_PRIVATE_KEY_PASSWORD"} \
  "$ARTIFACT"

SIGNATURE="$(cat "$ARTIFACT.sig")"
PUB_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "$UPDATE_DIR/latest.json" << JSON
{
  "version": "$VERSION",
  "notes": "See GitHub release notes.",
  "pub_date": "$PUB_DATE",
  "platforms": {
    "darwin-aarch64": {
      "signature": "$SIGNATURE",
      "url": "https://github.com/$REPO_SLUG/releases/download/v$VERSION/Raven.app.tar.gz"
    }
  }
}
JSON

echo ""
echo "=== Done ==="
echo "  artifact:  $ARTIFACT"
echo "  signature: $ARTIFACT.sig"
echo "  manifest:  $UPDATE_DIR/latest.json"
