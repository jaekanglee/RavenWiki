# raven v0.7.20 — Dashboard vault 표시 정상화 (WIKI_VAULTS_DIR=/vaults)

> **핵심**: 사용자 (2026-06-30) — "harumoa랑 raven-dev 있었잖아. 안 보이는 게 정상이야?"
>
> ❌ **정상이 아님**. v0.7.20: `WIKI_VAULTS_DIR` 환경변수를 mount target `/vaults`로 명시. API 응답 `vaults:[]` 빈 배열 → 2개 vault 정상 표시.

릴리스 일자: 2026-06-30
이전: v0.7.19 (default vault 경로 = ~/Raven)

---

## 한 줄 요약

docker-compose.yml `WIKI_VAULTS_DIR=/vaults` (mount target, 컨테이너 안 path). registry.py가 컨테이너 안 `/vaults/.registry.json` 정상 읽음 → API 응답에 vault 2개 (raven-dev + harumoa) 표시.

## 1. 문제 (사용자 진단)

**Before (v0.7.19)**:
```bash
$ docker exec raven-api python -m raven.cli where
📁 vaults root: /Users/jaekanglee/Raven   # ❌ 컨테이너 안에 없는 path

$ curl http://localhost:8765/api/vaults
{"ok":true,"vaults":[],"vaults_root":"/home/raven/Raven"}   # ❌ 빈 배열
```

**원인 분석**:
- `RAVEN_VAULTS_DIR=/Users/jaekanglee/Raven` (호스트 path)
- 컨테이너 안 `/Users/jaekanglee/Raven/` **존재 ❌** (bind mount는 `/vaults`에 mount됨)
- `/Users/jaekanglee/Raven` 가르키는 경로가 컨테이너 안에 없음 → `exists()=False` → `list()=[]`
- **dashboard에 vault 0개 표시** ⚠️ (실제로는 2개 정상)

## 2. 변경 사항

### 2-1. `docker-compose.yml` — WIKI_VAULTS_DIR mount target 고정

**Before (v0.7.19)**:
```yaml
environment:
  - WIKI_VAULTS_DIR=${RAVEN_VAULTS_DIR}   # = /Users/jaekanglee/Raven (❌ 컨테이너 안에 없음)
```

**After (v0.7.20+)**:
```yaml
environment:
  - WIKI_VAULTS_DIR=/vaults   # mount target, 컨테이너 안 path
```

→ **RAVEN_VAULTS_DIR**: 호스트 경로 (mount source) → mount target에 자동 연결
→ **WIKI_VAULTS_DIR**: 컨테이너 안 path (`/vaults`) → registry.py가 정확히 읽음

### 2-2. `tests/test_v0_7_12_docker.py` — 회귀 가드 추가

```python
def test_compose_mounts_user_vault_path():
    """v0.7.20+: WIKI_VAULTS_DIR=/vaults (mount target, 컨테이너 안)."""
    assert "${RAVEN_VAULTS_DIR}:/vaults" in content  # mount source → target
    assert "WIKI_VAULTS_DIR=/vaults" in content       # WIKI_VAULTS_DIR은 mount target
```

## 3. 검증 (실제 동작)

```bash
$ make docker-down && make docker-up

$ curl http://localhost:8765/api/vaults
{
  "ok": true,
  "vaults": [
    {"name": "raven-dev", "path": "/Users/jaekanglee/Raven/raven-dev", "mode": "agent", "default": true},
    {"name": "harumoa", "path": "/Users/jaekanglee/Raven/harumoa", "mode": "personal", "default": false}
  ],
  "vaults_root": "/vaults"
}   # ✅ 2개 vault 정상 표시

$ docker exec raven-api python -m raven.cli vault list
  ★ raven-dev      agent    /Users/jaekanglee/Raven/raven-dev
    harumoa        personal /Users/jaekanglee/Raven/harumoa
```

## 4. 개념 정리 (정직)

| 변수 | 의미 | 컨테이너 안 path |
|---|---|---|
| `RAVEN_VAULTS_DIR` | **호스트 경로** (mount source) | `/Users/jaekanglee/Raven` ❌ |
| `WIKI_VAULTS_DIR` | **컨테이너 안 path** (mount target) | `/vaults` ⭕ |

→ **두 변수의 역할 분리**: 
- RAVEN_VAULTS_DIR = 사용자 vault 외부 경로 (호스트에서 정의)
- WIKI_VAULTS_DIR = 컨테이너 안에서 registry.py가 읽는 path

## 5. 사용자 의도 (정직)

> "harumoa랑 raven-dev 있었잖아. 안 보이는 게 정상이야?"

→ ❌ **정상이 아님**. v0.7.19까지 버그. **v0.7.20으로 정상화**.

## 6. 호환성

- ✅ **v0.7.19 사용자**: 영향 ❌ (env 변수 하나 추가)
- ✅ **vault 데이터**: 그대로 보존 (bind mount)
- ✅ **다른 PC**: 본인 호스트 경로 자동 인식 (`RAVEN_VAULTS_DIR`)
- ✅ **Dashboard**: 2개 vault 정상 표시 (raven-dev + harumoa)

## 7. 다음 단계

- **v0.7.21 (후보)**: Dashboard v0.7.20+ 변경사항 반영 (사용자가 이미 commit한 v0.7.21과 충돌 ❌ — 별도 분석 필요)
- **v0.7.22 (후보)**: README 업데이트 — v0.7.20+ vault path 개념 (RAVEN_VAULTS_DIR vs WIKI_VAULTS_DIR)

다음 사용자 입력 대기. 👋