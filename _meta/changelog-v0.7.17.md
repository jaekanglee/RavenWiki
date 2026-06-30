# raven v0.7.17 — Dockerfile 빌드 + 컨테이너 권한 fix

> **핵심**: 사용자 (2026-06-30) — "docker up 하니까 끝까지 해보고 잘 될 때 얘기해"
>
> v0.7.17: Dockerfile **3가지 빌드/실행 문제** 수정 → 3 컨테이너 모두 정상.

릴리스 일자: 2026-06-30
이전: v0.7.16 (Compose v2 `version` 키 제거)

---

## 한 줄 요약

Dockerfile 3개 문제 (pyproject.toml path / editable install fail / USER raven 권한) 수정 → `make docker-build` + `make docker-up` **한 번에 정상 동작**. 3 컨테이너 (API/MCP HTTP/Dashboard) 모두 healthy.

## 1. 문제 + 해결 (3가지)

### 1-1. `COPY pyproject.toml ./` — 파일 ❌ (v0.7.12 작성 시 오타)

**Before**:
```dockerfile
COPY pyproject.toml ./        # ❌ /app/pyproject.toml 없음
```

**After**:
```dockerfile
# editable install 자체가 build fail → 의존성 직접 install
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        'python-frontmatter>=1.1.0' \
        'mcp[cli]>=1.0' \
        'fastapi>=0.100' \
        'uvicorn[standard]>=0.20' \
        'pydantic>=2.0' \
        'typer>=0.9' \
        'pytest>=7.0' \
        'httpx<0.28' \
        'starlette>=0.30'
```

→ `scripts/pyproject.toml` editable install 시 `mcp[cli]>=1.x` 의존성 build fail. **editable install ❌, 의존성 직접 install ⭕**.

### 1-2. `docker compose build` — 병렬 image 빌드 충돌

**Before**: `docker compose build` (3 service **병렬 빌드**)
```
❌ target api: failed to solve: image "raven:latest": already exists
❌ target dashboard: failed to solve: image "raven:latest": already exists
```

**After (Makefile)**: 순차 빌드 (v0.7.17+)
```makefile
docker-build:
    $(MAKE) docker-build-api           # 1) api
    $(MAKE) docker-build-mcp-http      # 2) mcp-http
    $(MAKE) docker-build-dashboard     # 3) dashboard
```

→ 같은 tag (`raven:latest`)에 3 service가 동시 write 충돌. **순차 빌드**로 해결.

### 1-3. `USER raven` — 실행/읽기 권한 ❌

**Before**:
```dockerfile
RUN useradd --create-home --uid 1000 --shell /bin/bash raven
COPY raven/ ./raven/                 # root:root 권한
COPY scripts/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x docker-entrypoint.sh     # root:root 권한 → raven user 실행 ❌
...
USER raven                            # ❌ Permission denied
```

→ root가 만든 파일에 `chmod +x`만 적용 → `644` (`-rw-r--r--`). raven user는 read OK, **exec ❌**.

**After**:
```dockerfile
COPY --chown=raven:raven raven/ ./raven/
COPY --chown=raven:raven dashboard/public ./dashboard/public
COPY --chown=raven:raven dashboard/index.html ./dashboard/
COPY --chown=raven:raven scripts/docker-entrypoint.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh
...
USER raven                            # ✅ 정상
```

→ `--chown=raven:raven` + `chmod 755` → `755` (`-rwxr-xr-x`). raven user exec ⭕.

## 2. 검증 (실제 동작)

```bash
$ make docker-build
✅ raven:latest built (3 services: api, mcp-http, dashboard)

$ make docker-up
🟢 Raven Docker stack running

$ make docker-ps
NAME              STATUS                  PORTS
raven-api         Up 15 seconds (healthy)    8765
raven-mcp-http    Up 15 seconds              8766
raven-dashboard   Up 15 seconds              5173

$ curl http://localhost:8765/api/vaults
{"ok":true,"vaults":[],"vaults_root":"/home/raven/Raven"}   # HTTP 200

$ curl http://localhost:5173
HTTP 200 (Dashboard)

$ curl -X POST http://localhost:8766/mcp ...   # initialize
HTTP 200 (MCP HTTP)
```

## 3. 잔여 (vault 표시 — 다음 작업)

API가 응답 `vaults_root: "/home/raven/Raven"` — 컨테이너 안의 default path. **bind mount된 `/vaults` ❌**. 

**원인**: API가 `RAVEN_VAULTS_DIR` 환경변수 안 읽고 hard-coded default 사용. 

**다음**: docker-entrypoint.sh에서 `RAVEN_VAULTS_DIR` 환경변수 박기 + API/CLI가 그걸 읽도록 검증.

## 4. 변경 사항 (총 2 파일)

### 4-1. `Dockerfile`
- `COPY pyproject.toml ./` ❌ (이 라인 삭제)
- `COPY scripts/ ./scripts/ && pip install -e ./scripts` ❌ → `pip install <deps>` 직접 install
- `COPY raven/`, `dashboard/public`, `dashboard/index.html`, `scripts/docker-entrypoint.sh` → 모두 `--chown=raven:raven`
- `RUN chmod +x` → `RUN chmod 755`

### 4-2. `Makefile`
- `docker-build`: `docker compose build` (병렬) → 순차 `$(MAKE) docker-build-{api,mcp-http,dashboard}`
- 신규 target 3개: `docker-build-api` / `docker-build-mcp-http` / `docker-build-dashboard`

## 5. 호환성

- ✅ **v0.7.16 사용자**: 영향 ❌ (build 실패 해결만)
- ✅ **첫 `make docker-up` 성공**: 3 컨테이너 모두 healthy
- ⚠️ **vault 표시 경로**: `/home/raven/Raven` (다음 작업에서 수정)

## 6. 다음 단계

- **v0.7.18 (후보)**: vault path 정합성 — docker-entrypoint.sh에서 `RAVEN_VAULTS_DIR` 환경변수 박기, API/CLI/MCP가 그걸 읽도록 검증
- **v0.7.19 (후보)**: `make docker-logs` 가독성 (현재는 docker compose 기본 출력)

다음 사용자 입력 대기. 👋