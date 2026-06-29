# raven v0.6.26 — Modal 공통 컴포넌트 (DeleteButton/EditButton 교체)

> **핵심**: 4개 모달이 반복하던 backdrop/dim-click/Escape/z-index 패턴을 `<Modal>` 공통 컴포넌트로 추출. DeleteButton/EditButton 교체.

릴리스 일자: 2026-06-29
이전: v0.6.25 (회귀 검증)

---

## 한 줄 요약

`dashboard/src/components/ui/Modal.tsx` 신규 — Portal + backdrop + Escape + 커스터마이즈 옵션. DeleteButton/EditButton 2개 모달 교체 (-110/+70줄). NewPageButton/NewFolderButton은 별도 패치 (자체 추가 UI — path picker 등).

## 1. Modal API

```tsx
<Modal
  open={open}
  onClose={() => setOpen(false)}
  maxWidth={720}        // 기본 720
  zIndex={80}           // 기본 80
  overlay="rgba(0,0,0,0.5)"  // 기본값
  disableBackdropClose={false} // busy 상태 등에서 dim 클릭 방지
>
  <h2>제목</h2>
  ... 본문 ...
</Modal>
```

자동 처리:
- `createPortal(<div>, document.body)` — v0.6.18 containing block 회피
- backdrop 클릭 → onClose (disableBackdropClose로 비활성화 가능)
- Escape 키 → onClose
- card click → stopPropagation (modal 내용 클릭 시 dim 닫기 방지)

## 2. 변경 사항

### 2-1. `dashboard/src/components/ui/Modal.tsx` (신규)

`createPortal` + `useEffect` (Escape 등록/해제) + 인라인 스타일. 

### 2-2. `dashboard/src/components/DeleteButton.tsx` (-52 / +33)

- `{open && createPortal(...)}` 패턴 → `<Modal>`
- `disableBackdropClose={busy}` — busy일 때 dim 클릭 방지
- 모달 내부 children 구조 그대로 유지

### 2-3. `dashboard/src/components/EditButton.tsx` (-57 / +38)

- 동일 패턴
- maxWidth=960 (편집 모달이라 넓게)

## 3. 회귀 가드 (`dashboard/tests/Modal.test.tsx`, 6 tests)

1. closed → null
2. open → body 직속 portal
3. backdrop click → onClose
4. 내용 click → onClose 안 함 (stopPropagation)
5. Escape key → onClose
6. maxWidth 커스터마이즈

## 4. 검증

| 항목 | 결과 |
|---|---|
| vitest | **18 파일 / 90 tests pass + 1 skip** (회귀 0) |
| tsc -b | **exit 0** |

## 5. 범위 외 (별도 패치)

- **NewPageButton** — TextField + path picker + 2-column grid 등 자체 UI 복잡. Modal 교체 시 children 구조 변경 필요
- **NewFolderButton** — 위와 유사 + autoFocus + Enter 키 submit 등 자체 동작

## 6. 효과

| 항목 | 효과 |
|---|---|
| DeleteButton/EditButton 라인 | -109 / +71 (-38줄) |
| 4 모달 중 2 모달 통일 | 절반 완료 |
| 코드 추적성 | 한 곳(Modal) 수정 → 2 사용처 자동 반영 |

## 7. 후속 작업

- NewPageButton/NewFolderButton Modal 교체
- 다른 공통 컴포넌트: `<Button>`, `<SelectField>`
- 자가 사용 위임