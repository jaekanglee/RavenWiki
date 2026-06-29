# raven v0.6.27 — Modal 교체 완료 (4/4)

> **핵심**: v0.6.26 Modal 공통 컴포넌트의 두 번째 적용 — NewPageButton/NewFolderButton 2 모달 교체. 이제 Raven의 position:fixed 모달 4개 모두 `<Modal>` 통일.

릴리스 일자: 2026-06-29
이전: v0.6.26 (Modal + DeleteButton/EditButton)

---

## 한 줄 요약

`NewPageButton.tsx`, `NewFolderButton.tsx` 의 인라인 모달 패턴을 `<Modal>` 로 교체. 4/4 모달 통일 완료. 코드 -49/+27줄.

## 1. 변경 사항

### 1-1. `dashboard/src/components/NewFolderButton.tsx` (-25 / +13)

- `{open && createPortal(...)}` 패턴 → `<Modal maxWidth={480} disableBackdropClose={busy}>`
- TextField 그대로 유지, autoFocus + Enter submit 그대로

### 1-2. `dashboard/src/components/NewPageButton.tsx` (-30 / +17)

- 동일 패턴, `maxWidth={880}` (path picker 2-column)
- outer wrapper div로 `display:flex, flexDirection:column, overflow:hidden` 처리
- PathPicker, TextField, advanced toggle, type select, content textarea 모두 그대로

## 2. 회귀 검증

| 항목 | 결과 |
|---|---|
| vitest | **18 파일 / 90 tests pass + 1 skip** (회귀 0) |
| tsc -b | **exit 0** |
| 브라우저 smoke 4 모달 | 모두 `parent=document.body` ✅ |

## 3. 4 모달 통일 매트릭스

| 컴포넌트 | Modal | maxWidth | disableBackdropClose |
|---|---|---|---|
| NewPageButton | ✅ v0.6.27 | 880 | busy |
| NewFolderButton | ✅ v0.6.27 | 480 | busy |
| DeleteButton | ✅ v0.6.26 | 480 | busy |
| EditButton | ✅ v0.6.26 | 960 | busy |

**공통 자동 처리**: Portal → document.body, Escape → onClose, backdrop click → onClose (disableBackdropClose 비활성화 가능)

## 4. 효과

| 항목 | 효과 |
|---|---|
| NewPageButton/NewFolderButton 라인 | -55 / +30 |
| 4 모달 일관성 | 100% |
| 새 모달 작성 비용 | ~5줄 (`<Modal>` 한 줄) |
| ESC/dim 닫기 패턴 | 4 곳 → 1 곳 (Modal 안) |

## 5. 후속 작업

- `<Button>` 공통 컴포넌트 (`.btn-primary`/`.btn-secondary`/`.btn-pill-primary` 다수 인스턴스)
- `<SelectField>` (TextField의 select 지원)
- 자가 사용 위임