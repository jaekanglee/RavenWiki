#!/usr/bin/env bash
# verify-raven-vault.sh — AI-Agent-Wiki-Template v1.0.0 배포 전 검증 스크립트
#
# 이 스크립트는 템플릿 저장소 자체(또는 사용자 vault)에 대해 다음을 점검한다:
#   1) 필수 파일/디렉토리 존재
#   2) OS metadata (.DS_Store, Thumbs.db) 제거
#   3) secrets 패턴 (api_key, token, password, secret) 검사
#   4) Raven CLI 호출 가능 시 `raven lint run --no-log` 호출
#
# 종료 코드:
#   0 — 모든 검사 통과
#   1 — 필수 파일/디렉토리 누락
#   2 — OS metadata 발견
#   3 — secrets 패턴 의심 매치
#   4 — Raven lint 실패
#   5 — 사용 오류 (인자 등)

set -u
# NOTE: -e 는 일부 검사가 실패해도 다른 검사를 계속할 수 있도록 의도적으로 켜지 않는다.
# 각 검사 함수에서 명시적으로 종료 코드를 누적한다.

# ---------- 설정 ----------
SCRIPT_NAME="$(basename "$0")"
TARGET_DIR="${1:-$(pwd)}"

# 필수 파일/디렉토리 (TEMPLATE_MANIFEST.md 와 동기화 유지)
REQUIRED_PATHS=(
  "README.md"
  "AGENTS.md"
  "START_HERE.md"
  "index.md"
  "log.md"
  "VERSION"
  "LICENSE.md"
  "TEMPLATE_MANIFEST.md"
  ".gitignore"
  "prompts"
  "prompts/first-setup.md"
  "prompts/save.md"
  "prompts/ingest.md"
  "prompts/query.md"
  "prompts/lint.md"
  "scripts"
  "scripts/verify-raven-vault.sh"
)

# OS metadata 패턴 (재귀 제거 대상)
OS_METADATA_FILES=(
  ".DS_Store"
  "Thumbs.db"
  "._*"
  ".Spotlight-V100"
  ".Trashes"
  "ehthumbs.db"
  "Desktop.ini"
)

# secrets 의심 정규식 (대소문자 무시).
# BSD grep -E (macOS) 는 ERE만 지원 — `(?i)` inline flag 무시됨.
# 따라서 inline flag 없이 작성하고 grep 호출 시 `-i` 옵션으로 case-insensitive 처리한다.
# 매치되어도 자동 삭제는 하지 않고 보고만 한다.
SECRET_PATTERNS=(
  '(api[_-]?key|apikey)[[:space:]]*[:=][[:space:]]*["'\'']?[A-Za-z0-9_\-]{16,}'
  '(secret|secret[_-]?key)[[:space:]]*[:=][[:space:]]*["'\'']?[A-Za-z0-9_\-]{16,}'
  '(password|passwd|pwd)[[:space:]]*[:=][[:space:]]*["'\'']?[A-Za-z0-9_\-]{8,}'
  '(token|access[_-]?token|auth[_-]?token)[[:space:]]*[:=][[:space:]]*["'\'']?[A-Za-z0-9_\-]{16,}'
  '(sk-[A-Za-z0-9_\-]{16,}|ghp_[A-Za-z0-9]{36,}|AKIA[0-9A-Z]{16}|xox[abposr]-[A-Za-z0-9-]+)'
)

# ---------- 누적 카운터 ----------
EXIT_CODE=0
MISSING_COUNT=0
OS_META_COUNT=0
SECRET_HIT_COUNT=0

# ---------- 유틸 ----------
log()  { printf '[%s] %s\n' "$SCRIPT_NAME" "$*"; }
warn() { printf '[%s] WARN: %s\n' "$SCRIPT_NAME" "$*" >&2; }
err()  { printf '[%s] ERROR: %s\n' "$SCRIPT_NAME" "$*" >&2; }

# ---------- 검사 1: 필수 파일/디렉토리 ----------
check_required_paths() {
  log "check 1/4 — required paths under: $TARGET_DIR"
  local p
  for p in "${REQUIRED_PATHS[@]}"; do
    if [[ ! -e "$TARGET_DIR/$p" ]]; then
      err "  missing: $p"
      MISSING_COUNT=$((MISSING_COUNT + 1))
    fi
  done
  if [[ "$MISSING_COUNT" -eq 0 ]]; then
    log "  OK — all ${#REQUIRED_PATHS[@]} required paths present"
  else
    err "  $MISSING_COUNT required path(s) missing"
    EXIT_CODE=1
  fi
}

# ---------- 검사 2: OS metadata ----------
check_os_metadata() {
  log "check 2/4 — OS metadata scan"
  local pattern found
  for pattern in "${OS_METADATA_FILES[@]}"; do
    # find 는 macOS/리눅스 공통 호환을 위해 -name 사용. NUL 분리는 하지 않는다 (단순 보고용).
    while IFS= read -r found; do
      [[ -z "$found" ]] && continue
      warn "  OS metadata found: $found  (pattern: $pattern)"
      OS_META_COUNT=$((OS_META_COUNT + 1))
    done < <(cd "$TARGET_DIR" 2>/dev/null && find . \
              \( -name "$pattern" \) \
              -not -path '*/\.git/*' \
              -print 2>/dev/null)
  done
  if [[ "$OS_META_COUNT" -eq 0 ]]; then
    log "  OK — no OS metadata files found"
  else
    warn "  $OS_META_COUNT OS metadata file(s) found (보고만; 자동 삭제 ❌)"
    # OS metadata 발견은 경고. 종료 코드는 2로 설정하되, 권고만 하고 자동 제거는 하지 않는다.
    [[ "$EXIT_CODE" -eq 0 ]] && EXIT_CODE=2
  fi
}

# ---------- 검사 3: secrets 패턴 ----------
check_secrets() {
  log "check 3/4 — secrets pattern scan"
  local pat relpath hit
  # 검사 대상: 마크다운/스크립트/설정 파일. .git, node_modules, raw binary 제외.
  while IFS= read -r relpath; do
    [[ -z "$relpath" ]] && continue
    for pat in "${SECRET_PATTERNS[@]}"; do
      # grep -E 로 검사. macOS/리눅스 공통을 위해 -P (PCRE) 는 쓰지 않는다.
      # -i 로 case-insensitive 처리 (BSD grep -E 의 ERE 는 inline flag 미지원).
      hit=$(grep -niE "$pat" "$TARGET_DIR/$relpath" 2>/dev/null || true)
      if [[ -n "$hit" ]]; then
        while IFS= read -r line; do
          warn "  secret-suspect: $relpath:$line"
          SECRET_HIT_COUNT=$((SECRET_HIT_COUNT + 1))
        done <<< "$hit"
      fi
    done
  done < <(cd "$TARGET_DIR" 2>/dev/null && find . \
            -type f \
            \( -name "*.md" -o -name "*.sh" -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" -o -name "*.toml" -o -name "*.env" \) \
            -not -path '*/\.git/*' \
            -not -path '*/node_modules/*' \
            -print 2>/dev/null)

  if [[ "$SECRET_HIT_COUNT" -eq 0 ]]; then
    log "  OK — no secrets pattern matches"
  else
    err "  $SECRET_HIT_COUNT secrets-suspect line(s) found (자동 마스킹 ❌; 사용자 확인 필요)"
    [[ "$EXIT_CODE" -eq 0 || "$EXIT_CODE" -eq 2 ]] && EXIT_CODE=3
  fi
}

# ---------- 검사 4: Raven CLI 호출 가능 시 lint ----------
check_raven_cli() {
  log "check 4/4 — Raven CLI availability"
  if ! command -v raven >/dev/null 2>&1; then
    log "  SKIP — 'raven' not on PATH (Raven CLI 미설치 환경)"
    log "         설치 후 `bash $SCRIPT_NAME` 재실행 권장"
    return 0
  fi
  log "  found: $(command -v raven)"
  # vault 컨텍스트가 아니어도 `--no-log` 로 안전하게 호출.
  # 표준 출력은 dev/null 로 보내고, 종료 코드만 본다.
  if raven lint run --no-log >/dev/null 2>&1; then
    log "  OK — 'raven lint run --no-log' exit 0"
  else
    rc=$?
    err "  'raven lint run --no-log' exit $rc"
    # lint 실패는 별도 코드 4
    EXIT_CODE=4
  fi
}

# ---------- 메인 ----------
main() {
  if [[ ! -d "$TARGET_DIR" ]]; then
    err "TARGET_DIR is not a directory: $TARGET_DIR"
    exit 5
  fi

  log "verifying AI-Agent-Wiki-Template v1.0.0 under: $TARGET_DIR"
  log "---"

  check_required_paths
  check_os_metadata
  check_secrets
  check_raven_cli

  log "---"
  log "summary:"
  log "  missing required paths: $MISSING_COUNT"
  log "  OS metadata files:      $OS_META_COUNT"
  log "  secrets suspects:       $SECRET_HIT_COUNT"
  case "$EXIT_CODE" in
    0) log "RESULT: PASS";;
    1) err  "RESULT: FAIL — required paths missing";;
    2) err  "RESULT: WARN — OS metadata found (auto-cleanup disabled)";;
    3) err  "RESULT: FAIL — secrets pattern matches";;
    4) err  "RESULT: FAIL — raven lint failed";;
    *) err  "RESULT: FAIL — exit=$EXIT_CODE";;
  esac
  exit "$EXIT_CODE"
}

main "$@"