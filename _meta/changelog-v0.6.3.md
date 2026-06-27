# raven v0.6.3 — Raven root 단일화 (`~/Raven/<name>/`)

> **핵심**: 모든 vault는 **`~/Raven/<name>/`** 패턴으로 자동 생성. Wizard의 path 입력이 **readonly 표시**로 단순화. `WIKI_VAULTS_DIR` env var로 override 가능 (유연성 보존).

릴리스 일자: 2026-06-27
이전: v0.6.2 (write-path 단일화)

---

## 한 줄 요약

`~/vaults/<name>/` → **`~/Raven/<name>/`**로 단일화. Wizard가 name만 받고 path는 자동 표시. 사용자가 절대경로 외울 필요 없음.

---

## 1. 변경 사항

### 1.1 Backend

| 파일 | 변경 |
|---|---|
| `raven/core/registry.py` `VAULTS_ROOT()` | 기본값 `~/vaults` → **`~/Raven`** (env override 유지) |
| `raven/api/server.py` `list_vaults` | 응답에 `vaults_root` 필드 추가 (frontend 표시용) |
| `raven/api/server.py` import | `from raven.core.registry import VAULTS_ROOT` 추가 |

### 1.2 Frontend

| 파일 | 변경 |
|---|---|
| `dashboard/src/components/NewVaultWizard.tsx` | `defaultPath()` → `~/Raven/<name>/` |
| `dashboard/src/components/NewVaultWizard.tsx` | path input → **readonly** + gray background + cursor default |
| `dashboard/src/components/VaultPicker.tsx` | `vaultsRoot` state + `setVaultsRoot(d.vaults_root)` |
| `dashboard/src/components/VaultPicker.tsx` | "Vaults (N)" 헤더 아래에 `root: /Users/.../Raven` 표시 |

### 1.3 사용자 워크플로 (before → after)

| Before (v0.6.2) | After (v0.6.3) |
|---|---|
| 1. Name 입력 | 1. Name 입력 |
| 2. **Path 직접 입력** (빡셈) | 2. ~~Path 입력~~ — 자동 표시 (`~/Raven/wiki/`) |
| 3. Mode 선택 | 3. Mode 선택 |
| 4. 확인 | 4. 확인 |

---

## 2. 호환성

| 케이스 | 동작 |
|---|---|
| 신규 설치 | `~/Raven/<name>/` 자동 생성 |
| 기존 사용자 (~/vaults/ 사용 중) | `WIKI_VAULTS_DIR=~/vaults` env var로 그대로 유지 |
| 테스트 (tmp_path) | `WIKI_VAULTS_DIR=...` 명시 또는 HOME 리다이렉트 |
| Dashboard | `vaultsRoot` 표시 (사용자 인지) |

→ **breaking change ❌** — 기본값만 변경, override 가능.

---

## 3. 검증

```bash
$ PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/ -q
366 passed, 1 warning in 5.65s   ✅ 회귀 0 (기존 361 + 신규 5)

$ PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/test_raven_root.py -v
test_vaults_root_default_is_ralph_home_raven      PASSED
test_vaults_root_env_override_still_works          PASSED
test_create_vault_auto_creates_directory            PASSED
test_list_vaults_response_includes_vaults_root      PASSED
test_create_vault_under_raven_root_default          PASSED
5 passed

$ cd dashboard && npx tsc -b --noEmit
(타입 에러 0)

$ cd dashboard && npm run build
✓ built in 1.51s
```

### 신규 회귀 가드 (5건)

| 테스트 | 보장 |
|---|---|
| `test_vaults_root_default_is_ralph_home_raven` | 기본값이 `~/Raven` |
| `test_vaults_root_env_override_still_works` | `WIKI_VAULTS_DIR` override 작동 |
| `test_create_vault_auto_creates_directory` | `mkdir(parents=True)` 보장 + Lite 4종 bootstrap |
| `test_list_vaults_response_includes_vaults_root` | API 응답에 `vaults_root` 포함 |
| `test_create_vault_under_raven_root_default` | E2E: 빈 registry → vault under `~/Raven` |

---

## 4. 변경 사항 요약

| 카테고리 | 변경 |
|---|---|
| Backend Python | 2 files (registry, server), 4 lines 변경 |
| Frontend TSX | 2 files (Wizard, VaultPicker), ~30 lines 추가 |
| Tests | 1 file 신규 (5 tests, 회귀 가드) |
| **`_meta/changelog-v0.6.3.md`** | 이 문서 |

---

## 5. 다음 사이클 후보

1. **Wizard Step 1 "Vaults root" 표시** — 사용자가 `vaults_root` 더 명확히 인지
2. **VaultPicker 기본 vault 자동 선택** (이미 있지만 UX 강화)
3. **delete/rename_page 단일화** (P1-1 후속)
4. **Dashboard NewVaultWizard 실사용 검증** (방금 머지한 lost-in-limbo 회수분)

---

## 6. 작업 보고

- **무엇**: `~/Raven/<name>/` 단일화 (backend 기본값 + frontend readonly)
- **왜 (저장 신호)**: ① 재사용 가능성 (사용자 빡셈 제거), ② 인수인계 (모든 vault 일관 위치), ③ 결정 추적 (changelog)
- **검증**: pytest 366 passed, dashboard typecheck + build PASS
- **다음 가능**: Wizard UX 추가 강화, delete/rename_page 단일화
