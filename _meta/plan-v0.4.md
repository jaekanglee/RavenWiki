---
title: plan-v0.4 — archive cleanup + vault clone + GUI v0.3 반영
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, plan, wikisys, v0.4]
sources: [_meta/plan-v0.3-crud.md, _meta/changelog-v0.3.md]
confidence: high
---

# plan-v0.4 — 운영성 + UX 마무리

> v0.3 (2026-06-25) CRUD 안전성 + 4-way 일관성 완료 후.
> v0.4 = "이미 안전한 것을 더 편하게/더 단단하게": 운영 자동화 + multi-vault UX + GUI 갭 해소.

---

## 1. v0.3 완료 상태 (참조)

4 인터페이스 모두 동일 정책:
- slug 검증, `created` 보존, tags list 강제, archive mirror

**총 94 테스트 pass.** 잔여 결함 (v0.3 §10):
- B6 (path rename) / B8 (clone/import) / B9 (archive cleanup) / B10 (stale 가드)

v0.3 작업 중 발견한 GUI/코드 갭:
- N1 (GUI v0.3 미반영) / N2 (build_db inline 통합)

---

## 2. v0.4 scope (3건)

| # | 작업 | 영향도 | 작업량 | 우선순위 |
|---|---|---|---|---|
| **B9** | `_archive` cleanup 정책 (CLI `wikisys archive clean`) | 디스크 누적, 이미 발생 중 | S | 1 |
| **B8** | vault `clone` (CLI/API) | multi-vault 운영 편의 | M | 2 |
| **N1** | GUI dashboard v0.3 반영 (bootstrap 옵션 + meta sync 버튼) | 사용자 UX 갭 | M | 3 |

**선택 사유 (옵션 A)**:
- 사용자 영향도 × 작업량 균형
- 한 세션에 완료 가능 (~280 LOC)
- GUI 갭 해소 = "기능은 있는데 화면에 없음" 상태 제거

**v0.4 범위 외 (v0.5+)**:
- N2 (build_db inline 통합) — 코드 일관성, 리스크 있음
- B6 / B10 / N4-N9 — 미래

---

## 3. B9 — Archive cleanup 정책

### 문제
- `_archive/`에 페이지 archive 누적 (현재 `~/vaults/default/_archive/content/v032-*` 2개)
- 정책 없음 → 무한 누적
- 사용자 (또는 자동 백업) 시점에 정리 필요

### 결정 (D16)
- **CLI sub-app** `wikisys archive` 추가
- **3개 명령**: `list` / `clean` / `restore`
- **기본 보존 정책**: 30일 (사용자 옵션 `--older-than`)
- **dry-run 기본**: `wikisys archive clean`은 `--apply` 없으면 dry-run

### 명령 시그니처

```bash
# 목록 (전체 또는 N일 이상)
wikisys archive list [--vault NAME]
wikisys archive list --older-than 30 --vault NAME

# 정리 (dry-run 기본)
wikisys archive clean --older-than 30 --vault NAME      # dry-run
wikisys archive clean --older-than 30 --vault NAME --apply  # 실제 삭제

# 복원 (mirror 구조 다시 풀기)
wikisys archive restore _archive/content/foo-20260625-1234.md --vault NAME
```

### 구현
- `wikisys.core.archive` 신규 모듈 (`list_archived`, `clean_archived`, `restore_archived`)
- `wikisys.cli.__main__`에 `archive_app` sub-app 추가
- mirror 경로 (`_archive/content/sub/foo-ts.md`)를 다시 `content/sub/foo.md`로 복원

### 테스트 (~6 케이스)
- `archive list` 빈 vault / 1개 / 다중
- `archive clean --older-than N` dry-run 출력 (삭제 안 함)
- `archive clean --apply` 실제 삭제
- `archive restore` 단일 페이지 복원
- 잘못된 경로 (`_archive` 밖) 거부

**예상 LOC: ~80 (코드 ~40 + 테스트 ~40).**

---

## 4. B8 — Vault clone / import

### 문제
- multi-vault 운영 시 "이 vault를 템플릿으로 새 vault 만들기" 필요
- 현재: `vault create` → 수동으로 파일 복사 → 옵션 많음 → 실수 잦음

### 결정 (D17)
- **CLI**: `wikisys vault clone <src> <new-name> <new-path>`
- **API**: `POST /api/vaults/clone` body `{src, name, path, mode?, owner?, bootstrap?}`
- **clone = vault meta + content/ + _meta/ 전체 복사** (wiki.db / _archive/ 제외)
- **same-host 전용** (네트워크 clone은 v0.5+)

### clone 동작

```
src vault (~/vaults/default)
  ↓ register, copy .vault.json + content/ + _meta/
new vault (/tmp/new-vault)
  ↓ 새 .vault.json (mode/owner 오버라이드 가능)
  ↓ wiki.db는 빌드 안 함 — 첫 사용 시 build
```

### 시그니처

```bash
wikisys vault clone default fresh ~/vaults/fresh --mode personal
wikisys vault clone default sandbox ~/vaults/sandbox --mode agent --owner codex
```

### API

```
POST /api/vaults/clone
{
  "src": "default",
  "name": "fresh",
  "path": "/Users/.../fresh",
  "mode": "personal",
  "owner": "user",
  "bootstrap": true  // false면 src에서 _meta/ 복사 안 함
}
```

### import = clone의 alias (사용자 멘탈 모델 친화)

```bash
# 둘 다 같은 동작
wikisys vault clone default fresh ~/vaults/fresh
wikisys vault import default fresh ~/vaults/fresh
```

### 구현
- `wikisys.core.vault.Vault.clone(src, name, path, ...)` classmethod
- `wikisys.cli.vault_clone` + `wikisys.api.create_clone`
- `shutil.copytree` + 메타 덮어쓰기 + registry 등록

### 테스트 (~5 케이스)
- `vault clone` src → dst (파일 1:1 복사)
- `vault clone --mode agent` (mode 오버라이드)
- `vault clone` 이미 존재하는 name 거부 (409)
- `vault clone` src 없으면 거부 (404)
- API + CLI 동일 결과

**예상 LOC: ~150 (코드 ~80 + 테스트 ~70).**

---

## 5. N1 — GUI dashboard v0.3 반영

### 현재 상태 (점검)
- dashboard/src/App.tsx, PageView.tsx — 사용자 작업분 (커밋 d47b4c0 등)
- v0.3.1에서 API에 추가한 `bootstrap` 옵션이 GUI 폼에 안 보임
- `meta sync` CLI는 있지만 GUI 버튼 없음

### 결정 (D18)
- **VaultPicker 폼**: `bootstrap` 체크박스 추가 (기본 on)
- **VaultDetail 페이지**: "Meta 동기화" 버튼 + confirm
- **Archive 페이지**: `wikisys archive list/clean/restore` 결과 표시 (clean은 dry-run 표시 + Apply 버튼)

### 변경 파일
- `dashboard/src/components/VaultCreateForm.tsx` (또는 동등) — bootstrap 옵션
- `dashboard/src/routes/VaultDetail.tsx` (또는 동등) — Meta sync 버튼
- `dashboard/src/routes/Archive.tsx` (신규) — archive list/clean UI

### 테스트
- 단위 테스트는 frontend 영역 — 사용자 작업 영역 존중
- 통합 테스트: API가 bootstrap 옵션 받고 응답 (이미 v0.3.1에서 테스트됨)
- 수동 검증: `npm run dev` 후 GUI에서 동작 확인

### 사용자 협업
- GUI 변경은 **사용자가 직접 작업 중** (`M dashboard/src/...`)
- v0.4에서는 **최소한의 가이드만** 제공:
  - changelog에 "GUI에서 확인 필요" 명시
  - 사용자 작업 완료 시 함께 검증

**예상 LOC: 가이드 문서 ~30 + 사용자 작업분 (별도).**

---

## 6. 파일 변경 계획

### 신규
| 경로 | 역할 | LOC |
|---|---|---|
| `wikisys/core/archive.py` | archive list/clean/restore | ~40 |
| `tests/test_archive.py` | archive 정책 검증 | ~60 |

### 수정
| 경로 | 변경 |
|---|---|
| `wikisys/core/__init__.py` | `archive_module` export |
| `wikisys/core/vault.py` | `Vault.clone()` classmethod |
| `wikisys/cli/__main__.py` | `archive_app` sub-app + `vault clone` 명령 |
| `wikisys/api/server.py` | `POST /api/vaults/clone` endpoint |
| `tests/test_cli.py` | `vault clone` + `archive` 명령 (~5 cases) |
| `tests/test_api.py` | `clone` endpoint (~2 cases) |
| `_meta/changelog-v0.4.md` | 릴리스 노트 |

### GUI (사용자 협업)
- 가이드만 제공, 사용자가 직접 작업

**총 LOC: ~280 (코드 ~150 + 테스트 ~130 + 문서 ~30).**

---

## 7. 단계별 실행

| 단계 | 작업 | 의존 | 산출물 |
|---|---|---|---|
| **E1** | `archive.py` + 6 테스트 | 없음 | `pytest tests/test_archive.py` pass |
| **E2** | CLI `archive` sub-app + `vault clone` + 테스트 | E1 | `pytest tests/test_cli.py` +5 pass |
| **E3** | API `POST /vaults/clone` + 테스트 | E2 | `pytest tests/test_api.py` +2 pass |
| **E4** | GUI 가이드 (changelog + 사용자 코멘트) | E1-E3 | changelog 갱신 |
| **E5** | 회귀 + 수동 검증 + 커밋 | E1-E4 | `pytest tests/` 100% pass |

---

## 8. 완료 기준 (DoD)

- [ ] `pytest tests/test_archive.py` 6 케이스 pass
- [ ] `pytest tests/` 누적 100+ pass (94 + 6 + 5 + 2)
- [ ] `wikisys archive list --vault default` — 현재 archive 2개 표시
- [ ] `wikisys archive clean --older-than 0 --vault default --apply` — archive 삭제 (수동 dry-run 후 사용자 OK 시)
- [ ] `wikisys vault clone default /tmp/test-clone` — 디렉토리 복사 + 등록
- [ ] `curl POST /api/vaults/clone {src:default, name:test, path:/tmp/x}` — 200 + vault 등록
- [ ] 기존 vault 회귀 0
- [ ] changelog-v0.4.md 작성
- [ ] 커밋 (단일 또는 분리 — 사용자 선택)

---

## 9. 결정 기록

| 결정 | 내용 | 일자 |
|---|---|---|
| **D16** | archive cleanup 정책: dry-run 기본, `--older-than N`, `list/clean/restore` 3 명령 | 2026-06-25 |
| **D17** | vault clone: same-host only, content/+_meta/ 복사, wiki.db 빌드는 사용자 시점 | 2026-06-25 |
| **D18** | v0.4는 GUI 가이드만. 실제 GUI 변경은 사용자 작업분 | 2026-06-25 |
| **D19** | archive 보존 기본값: 30일 (`--older-than 30`이 dry-run 기본) | 2026-06-25 |

---

## 10. v0.5 후보 (이번 plan 범위 외)

- N2 build_db.py inline 통합 (코드 일관성)
- B6 path 환경변수 rename
- B10 stale 가드
- N4 `vault remove --purge`
- N6 backup cron
- cross-vault wikilink
- wiki.db 증분 빌드
