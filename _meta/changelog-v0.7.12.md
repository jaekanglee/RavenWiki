# raven v0.7.12 — Docker 셋업 (다른 PC 환경에서도 동일 동작)

> **핵심**: 사용자 (2026-06-30) — "도커로 하면 어때? 다른 피씨 환경에서도 할 건데 사실"
> "볼트는 외부경로에 있으니까 ~/Raven 잘 매핑해놓고"
>
> v0.7.12: **Dockerfile + docker-compose.yml + .env.example + .dockerignore + scripts/docker-entrypoint.sh + Makefile docker-* target**. 사용자 vault 외부 경로 `~/Raven`을 정확히 mount. 한 명령 (`docker compose up --build`)으로 모든 환경에서 동일 동작.

릴리스 일자: 2026-06-30
이전: v0.7.11 (make dev one-command = full set)

---

## 한 줄 요약

`docker compose up --build` 한 명령으로 3 서비스 (API + MCP HTTP + Dashboard) 띄움. 사용자 vault 외부 경로 `~/Raven` 자동 mount. 다른 PC/Linux/Windows/Mac에서도 동일.

## 1. 변경 사항

### 1-1. `Dockerfile` (multi-stage)

- **Stage 1**: `node:20-slim` → Dashboard 정적 빌드 (`npm ci` + `npm run build`)
- **Stage 2**: `python:3.11-slim` → Python runtime + 정적 dashboard + 4 진입점 entrypoint
- `EXPOSE 8765 8766 5173` (3 서비스 port)
- `HEALTHCHECK` curl로 API alive 확인
- `USER raven` (uid 1000, 비-root)
- `ENTRYPOINT ["docker-entrypoint.sh"]` `CMD ["api"]` (entrypoint가 라우팅)

### 1-2. `docker-compose.yml` (3 services)

| 서비스 | Command | Port | Volume |
|---|---|---|---|
| `api` | `["api"]` | 8765 | `${RAVEN_VAULTS_DIR}:/vaults` |
| `mcp-http` | `["mcp-http"]` | 8766 | `${RAVEN_VAULTS_DIR}:/vaults` |
| `dashboard` | `["dashboard"]` | 5173 | (없음) |
| `stdio` | ❌ | ❌ | background 서비스 아님 — `docker compose exec api docker-entrypoint.sh mcp-stdio` |

→ `restart: unless-stopped` — 죽으면 자동 재시작
→ `healthcheck` — API 30초마다 curl, 3회 실패 시 unhealthy

### 1-3. `scripts/docker-entrypoint.sh`

```bash
case "$1" in
    api)        exec python -m raven.api --host "$HOST" --port "$PORT_API" ;;
    mcp-http)   exec python -m raven.mcp.cli --transport http --host "$HOST" --port "$PORT_MCP_HTTP" ;;
    mcp-stdio)  exec python -m raven.mcp.cli --transport stdio ;;
    dashboard)  cd /app/dashboard/dist && exec python -m http.server "$PORT_DASHBOARD" --bind "$HOST" ;;
    cli)        shift && exec python -m raven.cli "$@" ;;
esac
```

### 1-4. `.env.example`

```
PORT_API=8765
PORT_MCP_HTTP=8766
PORT_DASHBOARD=5173
HOST=0.0.0.0
RAVEN_VAULTS_DIR=/Users/jaekanglee/Raven   # 사용자 외부 vault 경로
```

### 1-5. `.dockerignore`

- `scripts/.venv/` (재빌드 inside container)
- `dashboard/node_modules/` (재빌드)
- `__pycache__/`, `*.pyc`, `*.db-journal`, `wiki.db`, `*.bak`, `*.tmp`
- `.env` (secret)
- `.hermes/` (Hermes profile data)

### 1-6. `Makefile` — docker-* targets 추가

```makefile
docker-build   # build image (auto-create .env if missing)
docker-up      # docker compose up -d
docker-down    # docker compose down
docker-logs    # follow logs
docker-ps      # container status
```

### 1-7. `tests/test_v0_7_12_docker.py` (신규, 9 tests)

1. `test_dockerfile_exists` — multi-stage (dashboard + runtime)
2. `test_dockerfile_exposes_4_ports` — 8765 + 8766 + 5173
3. `test_compose_has_3_services` — api + mcp-http + dashboard
4. `test_compose_mounts_user_vault_path` — `${RAVEN_VAULTS_DIR}:/vaults`
5. `test_env_example_default_vault_path` — `/Users/jaekanglee/Raven` 또는 `${HOME}/Raven`
6. `test_dockerignore_excludes_dev_artifacts` — venv + node_modules 제외
7. `test_entrypoint_supports_all_4_entries` — api|mcp-http|mcp-stdio|dashboard|cli
8. `test_makefile_has_docker_targets` — docker-build/up/down
9. `test_no_legacy_vault_data_volume` — 옛 `vault-data` Docker volume ❌

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **468 passed, 1 skipped** (v0.7.11: 459 → v0.7.12: 468, +9) |
| Dockerfile multi-stage | ✅ Node 20 + Python 3.11-slim |
| docker-compose.yml | ✅ 3 services + volume mount |
| vault 경로 매핑 | ✅ `${RAVEN_VAULTS_DIR}:/vaults` = `~/Raven` |

## 3. 사용법

```bash
# 1회 셋업
cp .env.example .env
# .env의 RAVEN_VAULTS_DIR 조정 (다른 PC면 해당 경로)

# 빌드 + 시작
make docker-build
make docker-up

# 확인
make docker-ps       # 컨테이너 상태
make docker-logs     # 로그 follow
curl http://localhost:8765/api/vaults

# 사용
# - API:    http://localhost:8765
# - MCP:    http://localhost:8766/mcp  (HTTP client config)
# - UI:     http://localhost:5173
# - CLI:    docker compose exec api docker-entrypoint.sh cli vault list
# - stdio:  docker compose exec api docker-entrypoint.sh mcp-stdio

# 종료
make docker-down
```

## 4. 다른 PC 환경

| 환경 | 사용법 |
|---|---|
| **macOS (다른 머신)** | `.env`의 `RAVEN_VAULTS_DIR`을 해당 머신의 vault 경로로 변경 |
| **Linux** | 동일. `~/Raven` 또는 원하는 경로 |
| **Windows** | WSL2 + Docker Desktop. `RAVEN_VAULTS_DIR=/mnt/c/Users/<user>/Raven` 등 |
| **CI/CD** | `RAVEN_VAULTS_DIR=/tmp/ci-vault` (ephemeral) |

→ 한 명령으로 동일 동작. 호스트의 동일 vault 경로를 mount하면 됨.

## 5. 다음 단계

- **v0.7.13 (후보)**: docker compose로 vault 자동 migrate (vaults/ 폴더 → 호스트 ~/Raven)
- **v0.8.0 (후보)**: 신규 사용자 onboarding — README → docker compose up → MCP 가이드

## 6. 호환성

- ✅ **v0.7.11 사용자**: 영향 ❌ (Docker 파일만 추가)
- ✅ **로컬 개발 (make dev)**: 영향 ❌ (변경 없음)
- ✅ **다른 PC 배포**: 동일 Dockerfile/compose 사용
- ⚠️ **vault-data 옛 Docker volume**: v0.7.12+ 제거. 기존 `vault-data` 사용자는 직접 `~/Raven`으로 migrate 필요

## 7. 시각화

```
호스트                                 Docker (raven-net bridge)
─────────────────                      ─────────────────────────────────
~/Desktop/Dev/Project/Raven/     ────► Dockerfile build (multi-stage)
~/Raven/  ◄────────────────────── mount ───► /vaults/ (in container)
                                      
.env (포트/볼트)              ────► env_file
docker-compose.yml           ────► 3 서비스:
                                       api  (:8765)  → curl http://localhost:8765
                                       mcp-http (:8766) → curl http://localhost:8766/mcp
                                       dashboard (:5173) → http://localhost:5173
```

다음 사용자 입력 대기. 👋