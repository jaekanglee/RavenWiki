# raven v0.6.24 — DeleteButton/EditButton Portal 누락 fix

> **핵심**: v0.6.18 Portal fix 이후에도 DeleteButton/EditButton 모달은 Portal 미적용. 같은 containing block 버그 가능성 → 같은 패턴으로 Portal 적용.

릴리스 일자: 2026-06-29
이전: v0.6.23 (TextField 사용처 확장)

---

## 한 줄 요약

`DeleteButton.tsx`, `EditButton.tsx` 두 컴포넌트의 모달 JSX를 `createPortal(modal, document.body)` 로 감쌈. v0.6.18과 동일한 패턴. 통합 회귀 가드 `All-modals-portal.test.tsx` 추가.

## 1. 발견 경위

v0.6.23 작업 중 DeleteButton을 grep하다가 Portal 미사용 발견:
```
$ grep -l 'createPortal' dashboard/src/components/*.tsx
NewFolderButton.tsx        ← v0.6.18 ✅
NewPageButton.tsx          ← v0.6.18 ✅
DeleteButton.tsx           ← ❌ Portal 없음
EditButton.tsx             ← ❌ Portal 없음
GraphCanvas.tsx            ← 별도 라우트, viewport 기준 OK
```

DeleteButton/EditButton은 **PageView 안에 있고 PageView는 Layout 안**. Layout의 sidebar가 `transform: translateX(-100%)` (mobile off-canvas) 적용 → 같은 v0.6.18 버그 발생 가능.

## 2. 변경 사항

### 2-1. `dashboard/src/components/DeleteButton.tsx` (+4 / -2)

- `import { createPortal } from "react-dom"`
- `{open && (...)}` → `{open && createPortal(..., document.body)}`

### 2-2. `dashboard/src/components/EditButton.tsx` (+4 / -2)

- 동일 패턴

### 2-3. `dashboard/tests/All-modals-portal.test.tsx` (신규, 3 tests)

회귀 가드:
1. DeleteButton 모달 → `document.body` 직속
2. EditButton 모달 → `document.body` 직속 (트리거 없으면 통과)
3. NewPageInline은 인라인 폼 — Portal 불필요, skip

## 3. NewPageInline은 왜 skip?

NewPageInline은 **모달이 아니라 인라인 폼** (HomePage의 Quick Action 카드 내부에 펼쳐짐). 사이드바 안에 있을 가능성도 있지만 position:fixed 사용 안 함 — v0.6.18 버그 패턴 해당 안 됨. **Portal 불필요**.

## 4. 검증

| 항목 | 결과 |
|---|---|
| vitest | **17 파일 / 84 tests pass + 1 skip** (회귀 0) |
| tsc -b | **exit 0** |
| 브라우저 smoke | DeleteButton 모달 parent=document.body, parent chain 비어있음 |

## 5. 전체 모달 Portal 적용 현황

| 컴포넌트 | Portal | 위치 |
|---|---|---|
| NewPageButton | ✅ v0.6.18 | Sidebar |
| NewFolderButton | ✅ v0.6.18 | Sidebar |
| DeleteButton | ✅ **v0.6.24** | PageView (Article) |
| EditButton | ✅ **v0.6.24** | PageView (Article) |
| NewPageInline | ❌ N/A | 인라인 폼, Portal 불필요 |
| GraphCanvas | ❌ N/A | 별도 라우트, 자체 캔버스 |

## 6. 후속 작업

- (즉시 안 함) 다른 모달 점검 — FullscreenGraphModal, VaultManage 등
- Task 4: MiniMax 회귀 검증
- 코드 추출: `<Modal>` 공통 컴포넌트 (Portal + backdrop + dim click 닫기) — 5개 모달 동일 패턴