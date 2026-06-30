# raven v0.7.15 — `make docker-up` 사용성 (`.env` 자동 생성)

> **핵심**: 사용자 (2026-06-30) — `make docker-up` 시 `invalid spec: :/vaults` (empty section between colons). 원인: `.env` 부재 → `${RAVEN_VAULTS_DIR}` 빈 문자열 → 빈 volume mount section.
>
> v0.7.15: `make docker-up`도 `make docker-build`처럼 **`.env` 부재 시 자동 복사**. 사용자가 `cp .env.example .env` 직접 안 해도 됨.

릴리스 일자: 2026-06-30
이전: v0.7.14 (vault 영속성)

---

## 한 줄 요약

`make docker-up`도 `.env` 자동 생성. 사용자가 docker-build 거치지 않고 바로 docker-up 호출 가능. 친절한 UX.

## 1. 문제 (사용자 진단)

```
$ make docker-up
WARN[0000] The "PORT_API" variable is not set. Defaulting to a blank string.
WARN[0000] The "RAVEN_VAULTS_DIR" variable is not set. Defaulting to a blank string.
...
invalid spec: :/vaults: empty section between colons
make: *** [docker-up] Error 1
```

→ `.env` 파일 없음 → `RAVEN_VAULTS_DIR` = 빈 string → docker-compose의 `${RAVEN_VAULTS_DIR}:/vaults` = `:/vaults` (invalid).

## 2. 변경 사항

### 2-1. `Makefile` — docker-up에 .env 자동 생성 추가

**Before (v0.7.12~v0.7.14)**:
```makefile
docker-up:
    docker compose up -d
```

**After (v0.7.15+)**:
```makefile
docker-up:
    @if [ ! -f .env ]; then \
        echo "📋 .env 없음. .env.example → .env 복사. RAVEN_VAULTS_DIR 조정 후 사용."; \
        cp .env.example .env; \
    fi
    docker compose up -d
```

→ `make docker-build`와 동일 로직. 사용자가 .env 만들 필요 ❌.

### 2-2. `tests/test_v0_7_15_docker_up_env.py` (신규, 2 tests)

1. `test_makefile_docker_up_creates_env` — `docker-up` body에 `.env.example` + `test -f .env` 박힘
2. `test_makefile_docker_build_creates_env` — `docker-build` body도 동일 검증

## 3. 검증

| 항목 | 결과 |
|---|---|
| pytest | **470 passed, 1 skipped** (v0.7.14: 468 → v0.7.15: 470, +2) |
| `make docker-up` (.env 없을 때) | ✅ `.env` 자동 생성 후 정상 동작 |

## 4. 사용법

```bash
# v0.7.15+: .env 자동 생성됨
make docker-up            # .env 없으면 자동 cp 후 시작
make docker-build         # build + .env 자동 생성

# v0.7.14 이하: .env 수동 생성
cp .env.example .env
vi .env                   # RAVEN_VAULTS_DIR 조정
make docker-up
```

## 5. 호환성

- ✅ **v0.7.14 사용자**: 영향 ❌ (.env 자동 생성만 추가)
- ✅ **docker-build**: 변경 ❌ (이미 .env 자동 생성)
- ⚠️ **사용자 .env 수정했다면**: v0.7.15+도 cp는 .env 없을 때만. 기존 .env 보존 ✅

## 6. 다음 단계

- **v0.7.16 (후보)**: `make docker-reset` target — 명시적 vault 데이터 wipe (확인 prompt)
- **v0.8.0 (후보)**: 신규 사용자 onboarding — README → Docker compose up → MCP 가이드

다음 사용자 입력 대기. 👋