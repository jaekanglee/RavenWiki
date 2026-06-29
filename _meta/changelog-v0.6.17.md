# raven v0.6.17 — Modal auto-closes mobile sidebar drawer

> **핵심**: v0.6.15 폴더 1차 시민 이후의 UX 마이크로 패치. 모바일/좁은 viewport(<744px)에서 sidebar drawer가 열린 채로 ＋ 버튼을 누르면 화면 중앙 모달과 drawer가 동시에 보이는 문제 — 모달만 남도록 자동 close.

릴리스 일자: 2026-06-29
이전: v0.6.16+ (폴더 1차 시민 마무리 + folder create modal)

---

## 한 줄 요약

`NewPageButton` / `NewFolderButton` 에 `onOpen?: () => void` prop 추가 → `Sidebar` 가 두 호출부에 `onOpen={onClose}` 전달. 트리거 클릭 시 모달 open 직전 onOpen 콜백 발화 → mobile drawer 자동 close.

## 1. 변경 사항

### 1-1. `dashboard/src/components/NewPageButton.tsx` (+6)

- `NewPageButtonProps.onOpen?: () => void` 추가 (optional, 회귀 안전)
- 트리거 `onClick` 핸들러에서 `setOpen(true)` 직전 `onOpen?.()` 호출
- onOpen 미지정 시 throw ❌, 기존 동작 그대로

### 1-2. `dashboard/src/components/NewFolderButton.tsx` (+7)

- 동일 패턴 — `NewFolderButtonProps.onOpen?: () => void` 추가
- 트리거에서 `onOpen?.()` 호출

### 1-3. `dashboard/src/components/Sidebar.tsx` (+3/-1)

- `VaultTreeGroup` 안의 `<NewPageButton ... onOpen={onClose} />`
- `<NewFolderButton ... onOpen={onClose} />`
- `onClose` 는 Layout이 넘기는 drawer close 핸들러 (`setMobileNavOpen(false)`)

## 2. 회귀 가드 (테스트 9건, 신규 파일 2개)

### 2-1. `dashboard/tests/Modal-close-sidebar.test.tsx`

컴포넌트 마운트 + 클릭 기반 검증:
1. NewPageButton: onOpen 콜백 발화 + 모달 열림
2. NewFolderButton: onOpen 콜백 발화 + 모달 열림
3. NewPageButton: onOpen 미지정 시 throw ❌
4. NewFolderButton: onOpen 미지정 시 throw ❌

### 2-2. `dashboard/tests/Modal-close-sidebar.contract.test.ts`

소스 위치 contract 검증 (vite `?raw` import 기반, `@types/node` 미추가):
1. NewPageButton: `onOpen?: () => void` prop + `onOpen?.()` 호출 + `setOpen(true)` 직전
2. NewFolderButton: 동일 패턴
3. Sidebar: `<NewPageButton ... onOpen={onClose} ... />` 전달
4. Sidebar: `<NewFolderButton ... onOpen={onClose} ... />` 전달
5. Layout: `max-width: 744px` 모바일 breakpoint 유지

> globals.css 검증은 vite `?raw` 가 CSS를 처리하지 못하는 한계로 제외 — Layout 744px 매칭으로 간접 보장.

## 3. 검증

| 항목 | 결과 |
|---|---|
| vitest (전체) | **11 파일 / 61 tests pass** (회귀 0) |
| tsc -b | **exit 0** (타입 OK) |
| 브라우저 smoke | ＋버튼 클릭 → 모달 정상 오픈, console error 0 |

## 4. 영향 범위

- 모바일 (<744px): sidebar drawer 열린 상태에서 ＋버튼 클릭 → drawer 자동 close + 모달만 표시 (UX 개선)
- 데스크탑 (>744px): onOpen 콜백 발화하지만 drawer가 이미 off-canvas 라 시각 변화 0 (단일 코드 경로, 분기 ❌)
- 다른 호출부: 영향 0 — onOpen optional 이므로 Sidebar 외 위치는 무관

## 5. 후속 작업 후보

- Type ADR 자동 표시 + 📑 Index 자동 표시 + folder hover 메뉴 (메모리 큐 2번)
- MiniMax 회귀 검증 (메모리 큐 3번)