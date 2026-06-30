# raven v0.7.16 — `docker-compose.yml` `version` 키 제거 (Compose v2 deprecated)

> **핵심**: 사용자 (2026-06-30) — `make docker-up` 시
> 1. `WARN[...] the attribute version is obsolete`
> 2. `Cannot connect to the Docker daemon at unix:///.../docker.sock. Is the docker daemon running?`
>
> v0.7.16: `version: "3.9"` 라인 제거 (Compose v2에서 deprecated). Docker daemon은 **사용자 환경에서 별도 시작 필요** (이쪽은 코드 변경 ❌).

릴리스 일자: 2026-06-30
이전: v0.7.15 (`.env` 자동 생성)

---

## 한 줄 요약

`docker-compose.yml`에서 `version: "3.9"` 라인 제거. Docker Compose v2는 `version` 키 무시 + 경고. v0.7.16+ = 깨끗한 v2 표준. **Docker daemon 연결 오류는 코드 변경 ❌, 사용자 환경 셋업 필요**.

## 1. 변경 사항

### 1-1. `docker-compose.yml` — version 키 제거

**Before (v0.7.12~v0.7.15)**:
```yaml
# Raven — Docker Compose (4 진입점 일괄, one command).
# v0.7.12+ — 다른 PC 환경에서 동일하게 동작.
...

version: "3.9"

services:
  api: ...
```

**After (v0.7.16+)**:
```yaml
# Raven — Docker Compose (4 진입점 일괄, one command).
# v0.7.16+: 'version' 키 제거 (Docker Compose v2 deprecated).
...

services:
  api: ...
```

→ Compose v2 (Docker Desktop 4.x+, OrbStack, colima)에서 `version` 키 무시. 경고 사라짐.

### 1-2. `tests/test_v0_7_12_docker.py` — 회귀 가드 1개 추가

- `test_compose_no_version_key` — 첫 10줄 안에 `version:` (코멘트 외) ❌

## 2. Docker daemon 미연결 (사용자 환경)

```
$ make docker-up
unable to get image 'raven:latest': Cannot connect to the Docker daemon
at unix:///Users/jaekanglee/.docker/run/docker.sock. Is the docker daemon running?
```

→ **Docker daemon이 시작 안 됨**. 사용자 환경에서 별도 시작 필요.

### 2-1. macOS (Docker Desktop) — 가장 일반적

```bash
# 방법 1: GUI로 시작
open -a Docker
# → 메뉴바에 Docker 아이콘 🐳 보일 때까지 대기 (1-2분)

# 방법 2: CLI로 시작
launchctl start com.docker.docker
# 또는
/Applications/Docker.app/Contents/MacOS/com.docker.backend &
```

### 2-2. macOS (OrbStack) — 더 가벼움

```bash
# OrbStack 앱 실행
open -a OrbStack
```

### 2-3. macOS (colima)

```bash
colima start
```

### 2-4. 확인

```bash
docker ps    # 컨테이너 목록 (정상 = 데몬 연결 OK)
docker info  # 시스템 정보
```

## 3. 검증

| 항목 | 결과 |
|---|---|
| pytest | **471 passed, 1 skipped** (v0.7.15: 470 → v0.7.16: 471, +1) |
| `docker compose config` (Docker daemon 필요) | 데몬 안 떠 있으면 config도 안 됨. v0.7.16 환경 검증은 사용자 Docker daemon 시작 후 |

## 4. 호환성

- ✅ **v0.7.15 사용자**: 영향 ❌ (`version` 라인만 제거, docker-compose 동작 동일)
- ✅ **Docker Compose v1**: 영향 ❌ (`version` 무시해도 동작 OK)
- ✅ **Docker Compose v2**: 경고 사라짐
- ⚠️ **Docker daemon 안 떠 있는 사용자**: v0.7.16+도 동일. **사용자가 직접 Docker Desktop/colima/orbstack 시작 필요**

## 5. 다음 단계 (사용자 환경)

1. **Docker Desktop 실행** (`open -a Docker`)
2. 메뉴바 🐳 아이콘 안정화 (1-2분)
3. `docker ps` 확인
4. `make docker-up` 다시 시도
5. 정상 동작 시 `curl http://localhost:8765/api/vaults` 검증

## 6. 운영 노트

| 항목 | 확인 |
|---|---|
| Docker daemon 시작 | 사용자 환경 (이 PR 변경 ❌) |
| `version` 키 경고 | ✅ v0.7.16+ 제거됨 |
| `.env` 자동 생성 | ✅ v0.7.15 |
| Vault 영속성 (bind mount) | ✅ v0.7.14 |
| pytest | ✅ 471 passed |

다음 사용자 입력 대기. 👋