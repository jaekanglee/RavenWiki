#!/usr/bin/env bash
# scripts/restart-all.sh — Raven Docker 스택 안전 재시작 (강제 이미지 rebuild)
#
# v0.7.55+ DEPRECATED. Docker stack은 더 이상 기본이 아님 — local host stack (raven.sh)이 default.
# 이 스크립트는 호환성 위해 유지되며, Docker가 production에서 쓰이는 경우에만 사용.
# 신규 사용자는 `make restart` (= ./raven.sh restart) 사용 권장.
#
# 목적:
#   - 백엔드(API/MCP) + Dashboard 전부 내렸다가 다시 올림
#   - layer cache + base image cache 강제 무효화 (--no-cache --pull)
#   - 현재 HEAD를 GIT_SHA로 박아서 stale 이미지 섞임 방지
#   - 각 서비스 헬스체크 (최대 60s) + 실패 시 로그 출력
#
# 사용법:
#   ./scripts/restart-all.sh              # 강제 rebuild + 재시작 (DEPRECATED, Docker 전용)
#   ./scripts/restart-all.sh --no-rebuild # rebuild 없이 재시작만 (코드 변경 없을 때)
#
# Local 호스트 stack (권장):
#   make restart                         # ./raven.sh restart (local PID 관리)
#
# 주의:
#   - vault 데이터는 volume이 아닌 호스트 bind mount → 절대 안 날아감
#   - network 'raven_raven-net' 재생성 (다른 컨테이너와 통신 끊김 일시적)
#   - 첫 실행은 base image pull + npm ci + build → 5-10분 소요 가능
#
# Local 권장 흐름 (v0.7.55+):
#   make start / make restart / make stop  # raven.sh wrapper (local host stack)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

NO_REBUILD=false
for arg in "$@"; do
    case "$arg" in
        --no-rebuild) NO_REBUILD=true ;;
        --help|-h)
            sed -n '2,15p' "$0" | sed 's/^# //; s/^#//'
            exit 0
            ;;
        *) echo "❌ unknown flag: $arg"; exit 1 ;;
    esac
done

# ─── 1. 사전 헬스체크 ─────────────────────────────────────
echo "🔍 사전 헬스체크…"
command -v docker >/dev/null 2>&1 || { echo "❌ docker not installed"; exit 1; }
docker info >/dev/null 2>&1 || { echo "❌ docker daemon not running"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "❌ docker compose plugin missing"; exit 1; }

[[ -f docker-compose.yml ]] || { echo "❌ docker-compose.yml not found (run from repo root)"; exit 1; }

# .env 검증 (없으면 안내 후 중단)
if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        echo "⚠️  .env 없음 → .env.example 복사"
        cp .env.example .env
    else
        echo "❌ .env 없고 .env.example도 없음"; exit 1
    fi
fi

# vault 디렉토리 검증
VAULTS_DIR=$(grep -E '^RAVEN_VAULTS_DIR=' .env | head -1 | cut -d'=' -f2- | tr -d '"' || echo "")
if [[ -z "$VAULTS_DIR" ]]; then
    VAULTS_DIR="$HOME/Raven"
    echo "⚠️  RAVEN_VAULTS_DIR 미설정 → 기본 $VAULTS_DIR 사용"
fi
if [[ ! -d "$VAULTS_DIR" ]]; then
    echo "⚠️  vault 폴더 없음: $VAULTS_DIR"
    read -p "   지금 만들기? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && mkdir -p "$VAULTS_DIR" || { echo "❌ aborted"; exit 1; }
fi

# 현재 HEAD
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
echo "   git HEAD: $GIT_SHA"
echo "   vault dir: $VAULTS_DIR"
echo

# ─── 2. down (안전) ─────────────────────────────────────
echo "🛑 docker compose down…"
docker compose down --remove-orphans 2>&1 | tail -5
echo

# ─── 3. build (no-rebuild 옵션 시 skip) ─────────────────
if [[ "$NO_REBUILD" == false ]]; then
    # v0.7.51+: multi-stage 빌드 충돌 회피.
    #
    # 문제: `docker compose build`는 stage를 병렬로 실행하며 모든 stage가
    # 같은 `raven:${GIT_SHA}` 태그로 export → 첫 stage 성공 직후 두 번째
    # stage가 "image already exists" CANCELED. (README 주석도 "sequential
    # build 절차" 언급 — 단, compose로는 달성 불가.)
    #
    # 해결: Dockerfile을 안 건드리고 스크립트가 `docker build`로 stage별
    # 임시 태그(`raven-${GIT_SHA}-stage-N`)로 빌드 → 마지막에 `docker tag`로
    # 통합 태그(`raven:${GIT_SHA}`) 생성 → dangling stage 이미지 정리.
    echo "🧹 stale raven 이미지 + dangling build cache 정리…"
    docker images "raven*" -q 2>/dev/null | xargs -r docker rmi -f 2>&1 | tail -3 || true
    docker builder prune -f 2>&1 | tail -2 || true
    docker image prune -f 2>&1 | tail -2 || true
    echo

    echo "🔨 docker build (multi-stage, sequential, stage별 임시 tag)…"
    echo "   (5-10분 소요 — npm ci + dashboard build + python deps install)"
    STAGE_TAGS=(
        "raven-${GIT_SHA}-stage1-dashboard"
        "raven-${GIT_SHA}-stage2-runtime"
    )
    # stage 1: dashboard build
    if ! docker build \
        --target dashboard-build \
        --tag "${STAGE_TAGS[0]}" \
        --build-arg VITE_API_BASE=/api \
        . 2>&1 | tail -5; then
        echo "❌ stage 1 (dashboard-build) 실패"
        exit 1
    fi
    # stage 2: runtime (full multi-stage)
    if ! docker build \
        --tag "${STAGE_TAGS[1]}" \
        --build-arg GIT_SHA="$GIT_SHA" \
        . 2>&1 | tail -10; then
        echo "❌ stage 2 (runtime) 실패"
        exit 1
    fi
    # stage 1 이미지는 stage 2 build로 흡수됨 (multi-stage). 두 번째 결과
    # 이미지가 `raven:${GIT_SHA}`로 명명되지 않은 경우를 대비해 tag 생성.
    docker tag "${STAGE_TAGS[1]}" "raven:${GIT_SHA}" 2>&1 | tail -2 || true
    docker tag "${STAGE_TAGS[1]}" "raven:latest" 2>&1 | tail -2 || true
    # stage 임시 tag 정리
    for tag in "${STAGE_TAGS[@]}"; do
        docker rmi "$tag" 2>/dev/null || true
    done
    echo "   ✅ raven:${GIT_SHA} built (sequential multi-stage)"
    echo
else
    echo "⏭  --no-rebuild 지정 → 빌드 건너뜀 (기존 이미지 사용)"
    echo
fi

# ─── 4. up -d ─────────────────────────────────────
echo "🟢 docker compose up -d…"
GIT_SHA="$GIT_SHA" docker compose up -d 2>&1 | tail -10
echo

# ─── 5. 헬스체크 (최대 60s) ─────────────────────────────
echo "🩺 헬스체크 (최대 60s)…"
HEALTH_OK=true

check_service() {
    local svc="$1"
    local url="$2"
    local expect="$3"
    local ok=false
    local status
    local i
    for i in $(seq 1 30); do
        status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "$url" 2>/dev/null || echo "000")
        if [[ "$status" =~ ^($expect)$ ]]; then
            ok=true
            break
        fi
        sleep 2
    done
    if $ok; then
        printf "   ✅ %-10s %s → %s\n" "$svc" "$url" "$status"
    else
        printf "   ❌ %-10s %s → %s (최대 60s 대기 후 실패)\n" "$svc" "$url" "$status"
        HEALTH_OK=false
    fi
}

check_service "api" "http://localhost:8765/api/vaults" "200"
check_service "mcp" "http://localhost:8766/mcp" "200|406"
check_service "dashboard" "http://localhost:5173/" "200"
echo

# ─── 6. post-check 로그 ─────────────────────────────────────
if ! $HEALTH_OK; then
    echo "⚠️  일부 서비스 헬스체크 실패 — 최근 로그:"
    echo "────────────────────────────────────"
    docker compose ps
    echo "────────────────────────────────────"
    for svc in api mcp-http dashboard; do
        if docker ps -a --format '{{.Names}}' | grep -q "raven-$svc"; then
            echo
            echo "── raven-$svc (last 20 lines) ──"
            docker logs --tail 20 "raven-$svc" 2>&1 | tail -20 || true
        fi
    done
    echo "────────────────────────────────────"
    exit 1
fi

# ─── 7. 성공 보고 ─────────────────────────────────────
echo "✨ Raven 재시작 완료"
echo "   • git HEAD: $GIT_SHA"
echo "   • API    → http://localhost:8765        (curl http://localhost:8765/api/vaults)"
echo "   • MCP    → http://localhost:8766/mcp    (MCP HTTP client config)"
echo "   • UI     → http://localhost:5173        (Dashboard — 강력 새로고침 Cmd+Shift+R)"
echo "   • CLI    → docker compose exec api docker-entrypoint.sh cli <args>"
echo "   • MCP stdio → docker compose exec api docker-entrypoint.sh mcp-stdio"
echo
echo "📝 사용 팁:"
echo "   - Dashboard 캐시: Cmd+Shift+R (PWA 강력 새로고침)"
echo "   - 로그 follow: docker compose logs -f"
echo "   - 서비스 상태: docker compose ps"
