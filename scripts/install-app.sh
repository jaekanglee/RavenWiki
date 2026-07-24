#!/usr/bin/env bash
# Raven Desktop — DMG 다운로드 + /Applications 설치
#
#   sh ./scripts/install-app.sh          (repo 안에서)
#   또는 gh release download 후 직접 실행
set -eu

REPO="jaekanglee/RavenWiki"
TAG="v0.1.0"
DMG_NAME="Raven_0.1.0_aarch64.dmg"
APP_NAME="Raven.app"
TMP_DMG="/tmp/$DMG_NAME"

echo "🐦 Raven Desktop 설치 ($TAG)"

# --- 1. DMG 다운로드 ---
if [ -f "$TMP_DMG" ]; then
  echo "✅ 이미 다운로드됨: $TMP_DMG"
else
  if command -v gh >/dev/null 2>&1; then
    echo "📥 gh로 다운로드..."
    if ! gh release download "$TAG" --repo "$REPO" --pattern "$DMG_NAME" --dir /tmp 2>/dev/null; then
      echo "❌ gh 다운로드 실패 — private repo 접근 권한 없음"
      echo "   해결: gh auth login (repo 소유 계정으로 로그인)"
      echo "   또는: 이 DMG를 AirDrop으로 전송"
      exit 1
    fi
  else
    URL="https://github.com/$REPO/releases/download/$TAG/$DMG_NAME"
    echo "📥 curl로 다운로드..."
    echo "   (private repo면 gh CLI 설치 권장: brew install gh)"
    curl -fSL -o "$TMP_DMG" "$URL"
  fi
fi

# --- 2. 마운트 ---
echo "💿 DMG 마운트..."
MOUNT=$(hdiutil attach "$TMP_DMG" -nobrowse | grep '/Volumes/' | awk -F'\t' '{print $NF}')
echo "   마운트: $MOUNT"

# --- 3. /Applications 복사 ---
echo "📦 $APP_NAME → /Applications ..."
if [ -d "/Applications/$APP_NAME" ]; then
  echo "   기존 앱 제거..."
  rm -rf "/Applications/$APP_NAME"
fi
cp -R "$MOUNT/$APP_NAME" /Applications/

# --- 4. 언마운트 + 정리 ---
hdiutil detach "$MOUNT" -quiet
rm -f "$TMP_DMG"

echo ""
echo "✅ 설치 완료: /Applications/$APP_NAME"
echo "   Spotlight에서 'Raven' 검색하거나 Launchpad에서 실행하세요."
