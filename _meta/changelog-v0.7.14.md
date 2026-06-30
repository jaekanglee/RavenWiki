# raven v0.7.14 — Docker 컨테이너 down/up 시 vault 데이터 영속성 보장

> **핵심**: 사용자 (2026-06-30) — "도커 내렸다 올렸다 한다고 db나 문서들 초기화되면 안된다"
>
> v0.7.14: `docker-compose.yml` = **bind mount (호스트 외부 경로 직접 연결)**. 컨테이너 down/up 시 vault 데이터 (content/, .vault.json, wiki.db, .mcp/, backups/, logs/) **모두 보존**. 옛 named Docker volume ❌ (데이터 loss 위험).

릴리스 일자: 2026-06-30
이전: v0.7.13 (Makefile 청소)

---

## 한 줄 요약

`docker-compose.yml`이 `${RAVEN_VAULTS_DIR}:/vaults` bind mount 사용 → 호스트의 `~/Raven`이 컨테이너와 직접 연결 → down/up해도 데이터 보존. 다른 PC에서도 호스트 동일 경로 mount 시 동일하게 동작.

## 1. 영속 대상 (vault 안)

Raven이 vault 안에 만드는 파일 (모두 gitignored, bind mount로 영속):

| 파일/폴더 | 내용 |
|---|---|
| `content/` | 사용자 마크다운 (Obsidian-style 자유) |
| `.vault.json` | vault 메타 (name, mode, owner, created, description) |
| `wiki.db` | sqlite 인덱스 (markdown에서 regenerate 가능) |
| `.mcp/` | MCP runtime state (idempotency store) |
| `backups/` | 자동 백업 |
| `logs/` | 서비스 로그 |

→ **모두 `${RAVEN_VAULTS_DIR}` (호스트 외부 경로) 안에 위치** → bind mount로 컨테이너와 호스트가 **실시간 동기화**.

## 2. 변경 사항

### 2-1. `docker-compose.yml` — vault 영속성 명시

```yaml
services:
  api:
    volumes:
      # ──────────────────────────────────────────────────────────────
      # v0.7.14+: vault 영속성 보장 (bind mount, 컨테이너 down/up 안전)
      # ──────────────────────────────────────────────────────────────
      # 1) 사용자 vault 외부 경로 ~/Raven → 컨테이너 /vaults
      #    → content/ + .vault.json + wiki.db + .mcp/ + backups/ + logs/
      #    → 마운트된 호스트 디렉토리에 영속. 컨테이너 재시작해도 보존.
      # 2) 다른 PC에서도 호스트의 동일 경로를 mount하면 동일하게 동작.
      - ${RAVEN_VAULTS_DIR}:/vaults
    working_dir: /vaults
```

### 2-2. `tests/test_v0_7_14_vault_persistence.py` (신규, 5 tests)

1. `test_api_service_uses_bind_mount` — api 서비스 bind mount 검증
2. `test_mcp_service_uses_bind_mount` — mcp-http 서비스 bind mount 검증 (api와 동일)
3. `test_env_example_default_vault_path` — `RAVEN_VAULTS_DIR` = `~/Raven`
4. `test_no_named_docker_volume` — 옛 `vault-data` named volume ❌
5. `test_persistence_comment_in_compose` — 주석에 영속성 명시

## 3. 검증

| 항목 | 결과 |
|---|---|
| pytest | **468 passed, 1 skipped** (v0.7.13: 463 → v0.7.14: 468, +5) |
| api service bind mount | ✅ `${RAVEN_VAULTS_DIR}:/vaults` |
| mcp-http service bind mount | ✅ 동일 (영속성 보장) |
| 옛 `vault-data` named volume | ❌ 제거됨 |

## 4. 사용법 (v0.7.14+)

```bash
# 1회 셋업
cp .env.example .env
# .env의 RAVEN_VAULTS_DIR이 호스트의 vault 경로인지 확인 (기본 ~/Raven)

# 빌드 + 시작
make docker-build
make docker-up

# 자유롭게 down/up 반복 (영속성 보장)
make docker-down     # vault 데이터 ❌ 손실
make docker-up       # vault 데이터 ✅ 그대로
make docker-down     # 다시 down — 또 안전
make docker-up       # 다시 up — 또 안전

# ❌ 절대 안 함: docker compose down -v (named volume 삭제 시 데이터 손실)
# ❌ 절대 안 함: 컨테이너 안에서 직접 vault 파일 수정 (host mount 무시)
```

## 5. 위험 시나리오 분석 (정직)

| 시나리오 | 결과 |
|---|---|
| `make docker-down` → `make docker-up` | ✅ vault 보존 (bind mount) |
| 머신 재부팅 | ✅ vault 보존 (호스트 디렉토리 그대로) |
| `docker compose down -v` | ⚠️ **named volume이 있으면 삭제됨**. v0.7.14+ named volume 없음 → 안전 ✅ |
| 컨테이너 안에서 `/vaults` 파일 수정 | ✅ 호스트에 즉시 반영 (bind mount). 충돌 ❌ (양방향 sync) |
| `.env`의 `RAVEN_VAULTS_DIR` 변경 | ⚠️ 다른 경로 → 다른 vault. 기존 vault는 이전 경로에 그대로 |

## 6. 다른 PC 환경

```bash
# PC-A (~/Raven 있음)
echo "RAVEN_VAULTS_DIR=/Users/jaekanglee/Raven" > .env
make docker-up

# PC-B (~/Raven 있음, git push 후 동일 코드)
git pull
echo "RAVEN_VAULTS_DIR=/Users/alice/Raven" > .env  # 본인 경로
make docker-up
# → PC-A의 vault와 다른 vault. 코드만 공유, vault는 각 PC에서 관리.

# (옵션) vault 동기화: git push ~/Raven → 다른 PC git pull → 동일 vault
```

## 7. 다음 단계

- **v0.7.15 (후보)**: `make docker-reset` target — **명시적 reset** (vault 데이터 wipe) — 위험 + 확인 prompt
- **v0.8.0 (후보)**: 신규 사용자 onboarding — README → Docker compose up → MCP 가이드

## 8. 호환성

- ✅ **v0.7.13 사용자**: 영향 ❌ (docker-compose.yml 보강만)
- ✅ **bind mount 사용 중**: 데이터 그대로 보존
- ⚠️ **옛 `vault-data` named volume (만약 있다면)**: 마이그레이션 필요
  ```bash
  docker compose down
  docker run --rm -v raven_vault-data:/from -v ~/Raven:/to alpine cp -a /from/. /to/
  # .env에서 RAVEN_VAULTS_DIR=~/Raven 설정
  ```

## 9. 시각화

```
호스트                                  Docker (컨테이너 안)
─────────                               ──────────────────
~/Raven/                                /vaults/
├── .vault.json          ◄────────►    (동일 파일, 실시간 sync)
├── content/
│   ├── decisions/...     ◄────────►    
│   └── journal/...       ◄────────►    
├── wiki.db              ◄────────►    
├── .mcp/                ◄────────►    
├── backups/             ◄────────►    
└── logs/                ◄────────►    

→ make docker-down/up 반복해도 호스트 디렉토리 그대로
→ 컨테이너 안에서 만들어진 파일도 호스트에 보존 (실시간)
```

다음 사용자 입력 대기. 👋