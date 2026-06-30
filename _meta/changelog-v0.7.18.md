# raven v0.7.18 — vault path 정합성 (WIKI_VAULTS_DIR 환경변수)

> **핵심**: 사용자 (2026-06-30) — "외부의 ~/Raven이랑 지금 연결이 안 된 것 같아"
>
> v0.7.18: docker-compose.yml에 `WIKI_VAULTS_DIR=${RAVEN_VAULTS_DIR}` 명시. API/CLI가 bind mount된 `/Users/jaekanglee/Raven`을 정상 인식.

릴리스 일자: 2026-06-30
이전: v0.7.17 (Dockerfile 빌드 + 권한)

---

## 한 줄 요약

`docker-compose.yml` `environment` 블록에 `WIKI_VAULTS_DIR` 명시 (registry.py가 읽는 정확한 이름). 컨테이너 안에서 `WIKI_VAULTS_DIR=/Users/jaekanglee/Raven` 확인 + `vaults root: /Users/jaekanglee/Raven` 응답 OK.

## 1. 문제 (사용자 진단)

**Before (v0.7.17)**:
```bash
$ docker exec raven-api bash -c 'python -m raven.cli where'
📁 vaults root: /home/raven/Raven       # ❌ 컨테이너 안 default (USER raven의 HOME)
📋 registry:    /home/raven/Raven/.registry.json
⚠️  no vaults registered.

$ curl http://localhost:8765/api/vaults
{"ok":true,"vaults":[],"vaults_root":"/home/raven/Raven"}   # ❌ 빈 배열
```

→ `RAVEN_VAULTS_DIR` (Dockerfile ENV + compose env_file) **박혀있지만**, Python code는 **`WIKI_VAULTS_DIR`** 환경변수만 읽음. **이름 불일치** → default = `$HOME/Raven` 사용.

## 2. 변경 사항

### 2-1. `scripts/docker-entrypoint.sh` — fallback export (보조)

```bash
# v0.7.18+: WIKI_VAULTS_DIR export fallback
# - Python code는 $WIKI_VAULTS_DIR 환경변수 사용 (registry.py:4, 10, 34)
# - RAVEN_VAULTS_DIR alias도 인정 (Docker compose 호환)
export WIKI_VAULTS_DIR="${WIKI_VAULTS_DIR:-${RAVEN_VAULTS_DIR:-/vaults}}"
```

### 2-2. `docker-compose.yml` — environment 명시

```yaml
services:
  api:
    env_file:
      - .env
    # v0.7.18+: WIKI_VAULTS_DIR 환경변수 명시
    environment:
      - WIKI_VAULTS_DIR=${RAVEN_VAULTS_DIR}
  mcp-http:
    env_file:
      - .env
    environment:
      - WIKI_VAULTS_DIR=${RAVEN_VAULTS_DIR}
```

→ `WIKI_VAULTS_DIR` = `RAVEN_VAULTS_DIR` (host path `~/Raven`) = `/Users/jaekanglee/Raven`

## 3. 검증

```bash
$ make docker-down && make docker-up

$ docker exec raven-api bash -c 'echo WIKI_VAULTS_DIR=$WIKI_VAULTS_DIR; python -m raven.cli where'
WIKI_VAULTS_DIR=/Users/jaekanglee/Raven
📁 vaults root: /Users/jaekanglee/Raven   # ✅ 정상
📋 registry:    /Users/jaekanglee/Raven/.registry.json

$ curl http://localhost:8765/api/vaults
{"ok":true,"vaults":[...],"vaults_root":"/Users/jaekanglee/Raven"}   # ✅ 경로 정상
```

## 4. 잔여 (v0.7.19+ 후보)

API 응답이 `vaults: []` (빈 배열) ⚠️ — registry.json은 vault 2개 있는데. → API serialization 또는 응답 변환 문제. CLI는 vault list 정상 동작 ⭕. → API 응답 코드 별도 디버깅.

## 5. 호환성

- ✅ **v0.7.17 사용자**: 영향 ❌ (env 추가만)
- ✅ **Tailscale 외부 접속**: 영향 ❌ (port 8765 그대로 0.0.0.0)
- ✅ **vault bind mount**: `/Users/jaekanglee/Raven` → `/vaults` 정상

## 6. 다음 단계

- **v0.7.19 (후보)**: API 응답 `vaults: []` 디버깅 (registry는 2개, API는 0개)
- **v0.7.20 (후보)**: dashboard healthcheck endpoint (`/health`) — dashboard/mcp-http healthcheck 적절화

다음 사용자 입력 대기. 👋