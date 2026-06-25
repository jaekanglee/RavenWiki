---
title: changelog-v0.4
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, changelog, raven, v0.4]
sources: [_meta/plan-v0.4.md, _meta/changelog-v0.3.md]
confidence: high
---

# changelog-v0.4

> 2026-06-25. 운영성 + UX 마무리.

## 추가

- `raven.core.archive` — archive list/clean/restore 모듈
- `Vault.clone()` — src vault를 새 vault로 복사 (content/ + _meta/, _archive/ 제외)
- CLI sub-app `raven archive {list,clean,restore}`
- CLI 명령 `raven vault clone` + alias `vault import`
- API endpoints:
  - `POST /api/vaults/clone`
  - `GET  /api/vaults/{n}/archive`
  - `POST /api/vaults/{n}/archive/clean`
  - `POST /api/vaults/{n}/archive/restore`

## 변경

- `Vault.create(bootstrap=False)` — 이제 빈 `content/` + `_meta/` 디렉토리 생성 (v0.3에서는 안 만듦).
  Templates는 복사 안 함. rationale: 사용자가 즉시 `raven page new` 가능.
- 기존 archive 2개 (`~/vaults/default/_archive/content/v032-*`) 정리 대상 — 권장:
  ```bash
  raven archive list --vault default          # 확인
  raven archive clean --older-than 0 --vault default --apply  # 정리
  ```

## GUI 갭 (사용자 작업분)

`dashboard/` 변경은 사용자 작업 영역. v0.3/0.4 백엔드 기능이 frontend에서 아직 미반영:

| 기능 | backend | frontend | 권장 가이드 |
|---|---|---|---|
| vault create bootstrap 옵션 | ✅ v0.3.1 | ❌ | VaultCreateForm에 checkbox 추가 (기본 on) |
| meta sync | ✅ v0.3.0 | ❌ | VaultDetail에 "메타 동기화" 버튼 + confirm |
| archive list/clean/restore | ✅ v0.4 | ❌ | 신규 Archive 페이지 또는 VaultDetail 탭 |
| vault clone | ✅ v0.4 | ❌ | VaultPicker에 "Clone" 액션 추가 |

API endpoints (curl 또는 dashboard 모두 사용 가능):
```bash
# archive list
curl http://localhost:8765/api/vaults/default/archive

# archive clean (dry-run)
curl -X POST 'http://localhost:8765/api/vaults/default/archive/clean?older_than=30'

# archive clean (apply)
curl -X POST 'http://localhost:8765/api/vaults/default/archive/clean?older_than=30&apply=true'

# vault clone
curl -X POST http://localhost:8765/api/vaults/clone \
  -H "Content-Type: application/json" \
  -d '{"src":"default","name":"fresh","path":"/Users/me/vaults/fresh"}'
```

## 호환성

- 기존 vault, archive 동작 무변경 (마이그레이션 불필요)
- `raven vault create --no-bootstrap` 동작 변경 (빈 dir 추가) — 사용자 OK 후 적용

## 테스트

- `tests/test_archive.py`: 16 신규 케이스 (list/single/nested/rel + dry-run/skip-recent/zero-days + apply/clean-empty + restore basic/nested/exists/outside/missing + ts-regex + CleanResult shape)
- `tests/test_cli.py`: +11 케이스 (clone 5 + import alias 1 + archive list 2 + clean 2 + restore 2 + json 1) — 일부 stderr 매칭 추가
- `tests/test_api.py`: +6 케이스 (clone 3 + archive 3)
- `tests/test_vault_create.py`: 1 케이스 업데이트 (no-bootstrap 정책 변경 반영)
- 합계 **128 passed** (94 → 128, +34)

## 호환성 위험

- `--no-bootstrap` 정책 변경: 기존에 `content/`가 없는 vault를 만들던 사용자는 영향 없음 (이미 만든 vault는 그대로). 신규 vault만 변경.
- archive mirror 정책 (v0.3): restore 명령이 mirror 구조를 정확히 해석하는지 v0.4 테스트로 확인.
