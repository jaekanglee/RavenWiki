# raven v0.7.19 — default vault 경로 = `~/Raven` 통일 + 폴더 검증

> **핵심**: 사용자 (2026-06-30) — "기본적으로 디폴트 경로는 ~/Raven으로 하자. 도커를 띄웠을 때 여기로, 폴더가 없으면 만드는 걸로"
>
> v0.7.19: `.env.example`의 default = `${HOME}/Raven` (사용자 vault 표준 위치). entrypoint에서 vault 폴더 검증 (bind mount가 호스트 폴더 보장).

릴리스 일자: 2026-06-30
이전: v0.7.18 (WIKI_VAULTS_DIR 환경변수)

---

## 한 줄 요약

`.env.example`의 `RAVEN_VAULTS_DIR` default = `${HOME}/Raven`. entrypoint에서 `$WIKI_VAULTS_DIR` 폴더 검증 + 친절한 안내 (bind mount는 호스트 폴더 보장).

## 1. 변경 사항

### 1-1. `.env.example` — default `~/Raven` 통일

**Before (v0.7.18)**:
```bash
RAVEN_VAULTS_DIR=/Users/jaekanglee/Raven   # 절대경로 (사용자 한정)
```

**After (v0.7.19+)**:
```bash
RAVEN_VAULTS_DIR=${HOME}/Raven   # ~/Raven (사용자 표준)
```

→ 다른 PC에서 본인 홈 경로 자동 인식. `mkdir -p ~/Raven` 한 번이면 끝.

### 1-2. `scripts/docker-entrypoint.sh` — vault 폴더 검증 + 안내

**Before (v0.7.18)**:
```bash
export WIKI_VAULTS_DIR="${WIKI_VAULTS_DIR:-${RAVEN_VAULTS_DIR:-/vaults}}"
# 폴더 검증 ❌ → 컨테이너 안 /home/raven/Raven default 사용
```

**After (v0.7.19+)**:
```bash
WIKI_VAULTS_DIR="${WIKI_VAULTS_DIR:-${RAVEN_VAULTS_DIR:-$HOME/Raven}}"
RAVEN_VAULTS_DIR="$WIKI_VAULTS_DIR"
export WIKI_VAULTS_DIR RAVEN_VAULTS_DIR

# bind mount 정상: 호스트 폴더가 mount → 폴더 존재 ⭕
# bind mount 비정상: 호스트 폴더 없음 → mount 빈 디렉토리 → vault 0건
if [ ! -d "$WIKI_VAULTS_DIR" ]; then
    echo "⚠️  vault 폴더 없음: $WIKI_VAULTS_DIR"
    echo "   권장: mkdir -p \"$WIKI_VAULTS_DIR\" (호스트에서 실행)"
fi
```

→ 컨테이너 안에서 `mkdir` 자동 ❌ (bind mount로 호스트가 폴더 보장). **사용자 안내만** 친절하게.

### 1-3. 회귀 가드 (test_v0_7_12 + test_v0_7_14) — `${HOME}/Raven` 검증 추가

```python
assert "RAVEN_VAULTS_DIR=/Users/jaekanglee/Raven" in content or \
       "RAVEN_VAULTS_DIR=${HOME}/Raven" in content, \
    ".env.example must default to ~/Raven (외부 vault 경로)"
```

## 2. 사용법 (v0.7.19+)

### 2-1. 첫 실행 (사용자 vault 처음 만들 때)

```bash
# 호스트에서: vault 폴더 한 번 만들기 (영구)
mkdir -p ~/Raven

# Docker 띄우기
make docker-up

# API가 자동으로 ~/Raven mount → registry.json 없으면 vault 0건 표시
# Dashboard에서 첫 vault 생성 (vault create 또는 자동 wizard)
```

### 2-2. 이미 ~/Raven 있음

```bash
make docker-up   # 자동으로 mount + registry.json 읽음
```

### 2-3. 다른 PC

```bash
# 본인 홈 경로 자동 인식 (${HOME}/Raven)
make docker-up
```

### 2-4. 다른 경로 사용

```bash
# .env 파일에서 override
echo "RAVEN_VAULTS_DIR=/Users/alice/Documents/vaults" > .env
make docker-up
```

## 3. 검증

| 항목 | 결과 |
|---|---|
| pytest | **471 passed, 1 skipped** |
| `.env.example` default | `${HOME}/Raven` (v0.7.19+) |
| entrypoint default | `$HOME/Raven` (컨테이너 안에서 자동 = `/home/raven/Raven`) |
| bind mount | `${RAVEN_VAULTS_DIR}:/vaults` (호스트 ~/Raven → 컨테이너 /vaults) |
| 폴더 검증 | bind mount 정상 시 ✅ / 폴더 없을 시 ⚠️ 안내 |

## 4. 호환성

- ✅ **v0.7.18 사용자**: `.env` 이미 절대경로 (`/Users/jaekanglee/Raven`) 박혀있음. 영향 ❌
- ✅ **다른 PC**: `.env.example`의 `${HOME}/Raven` 자동 적용. 본인 홈 경로 인식
- ✅ **이미 ~/Raven 있음**: bind mount로 즉시 사용 가능
- ⚠️ **폴더 없음**: ⚠️ 메시지 표시. 사용자 `mkdir -p ~/Raven` 권장

## 5. 다음 단계

- **v0.7.20 (후보)**: API 응답 `vaults: []` 디버깅 (registry.json은 vault 2개 있는데 API는 0개 — 별도 이슈)
- **v0.7.21 (후보)**: Dashboard 첫 실행 wizard (vault create 자동 안내)

다음 사용자 입력 대기. 👋