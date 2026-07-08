---
title: Changelog v0.7.116
created: 2026-07-08
updated: 2026-07-08
type: rule
audience: agent
confidence: high
---

# v0.7.116 — Dashboard wiki.db 리빌드 버튼 + silent warn hotfix

## 무엇을 했는가

### 1. Dashboard "wiki.db 리빌드" 버튼 (LintPage UI gap 해소)

- **문제**: `/lint` 페이지의 "새로고침" 버튼은 `GET /api/vaults/{name}/lint`만 호출 → wiki.db 미접촉. vault 사용자가 "lint 돌렸는데 검색은 옛날 데이터" 같은 mismatch를 만남. 사용자가 직접 `raven build` 또는 MCP `wiki_*` 도구를 호출해야 동기화됨.
- **원인**: 백엔드는 `POST /api/vaults/{name}/build` 라우터(`raven/api/server.py:1775`)를 이미 제공. dashboard에 그 진입점이 없었음.
- **수정** (4 항목):
  - `dashboard/src/lib/api.ts` — `BuildResult` 타입 + `fetchBuild(vault: string)` POST 함수 (lines 281-298)
  - `dashboard/src/routes/LintPage.tsx` — `building` / `buildResult` state 추가, `handleRebuild()` 핸들러, toolbar에 "🔨 wiki.db 리빌드" 버튼, inline 결과 표시 (3초 후 자동 hide)
  - race 방지: 빌드 중에는 "새로고침"도 `disabled={building}`
  - 빌드 결과(`build.ok`/`build.pages`)를 페이지 inline 표시 + toast 동시
- **스타일 정합 (AGENTS.md §13)**:
  - 색/폰트 하드코딩 ❌ → CSS 변수만 (`var(--color-primary)`, `var(--color-error-text)`, `var(--color-muted)`)
  - 새 컴포넌트 파일 ❌ → LintPage 내부에 끝냄 (재사용 추구)
  - 기존 `Button` 컴포넌트 + `showToast` 패턴 그대로 활용

### 2. silent warn hotfix (AGENTS.md §9 정합)

- **문제**: 두 곳에서 `except Exception: pass`로 어떤 에러도 silent swallow → 다음 사용자가 "왜 안 되지?" 할 때 단서가 안 남음.
- **수정**:
  - `raven/api/server.py:2007-2011` — `get_lint(write_log=true)` 분기 → stderr warn line 1줄 emit
  - `raven/core/db.py:64-66` — `build_db()` log append 분기 → 동일 패턴 stderr warn
  - 두 곳 모두 `AGENTS.md §9: silent 버그 정책 — silent swallow ❌` 주석 추가
- **동작 검증 (실측)**:
  - 정상 경로 → silent warn 분기 미실행 ✅
  - 화이트리스트 위반 `action='not_in_whitelist'` → ValueError raise → 새 분기에서 잡혀 stderr 출력 ✅
  - 기존 lint 12개 + build_db 회귀 없음 (실제 silent warn 발동 없음, fail 안 일어남)

## 왜 그렇게 했는가 (§5 4 신호)

| 신호 | 충족 |
|---|---|
| **재사용 가능성** | dashboard "리빌드" 버튼은 모든 vault의 stale 동기화 통로, 1회성 X |
| **인수인계 필요성** | 다음 운영자가 "왜 wiki.db mtime이 안 바뀌지?"를 묻지 않게 UI로 명시 |
| **scope/provenance 추적** | AGENTS.md §9(silent 버그 정책)에 명시된 위반 패턴을 hotfix로 보정 |
| **실패/리스크 기록** | silent swallow는 "동작은 했지만 무엇이 실패했는지 모름" → 진단 비용 ↑ |

## 검증

- `scripts/.venv/bin/python -c "import py_compile; py_compile.compile('raven/api/server.py', doraise=True); py_compile.compile('raven/core/db.py', doraise=True)"` → OK
- `cd dashboard && npx tsc -b --noEmit` → exit 0
- harumoa vault 즉시 rebuild → wiki.db 04:27 → 16:02, 95 pages, 2.3 MB, 378 links, 596 tags 정상
- raven-dev vault safety rebuild → wiki.db 04:25 → 16:09, 48 pages, 186 links, 155 tags 정상
- 4 vault status 검증: hermes-infra / babymoa / homelab은 mtime상 fresh (stale ❌, 손 안 댐)

## 관련 PR / 결정

- 4 파일 modified, 1 commit (PR bundling when related — dashboard UI patch + silent warn hotfix는 한 묶음 운영 일관성 패치)
- ADR 없음 (silent warn hotfix는 정책 준수형 §9 hotfix, 기능 추가형 신기능은 아님)
