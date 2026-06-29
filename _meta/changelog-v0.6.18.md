# raven v0.6.18 — Modal Portal: 진짜 viewport 중앙 띄우기

> **핵심**: v0.6.17의 `onOpen={onClose}` 패치는 UX 보조일 뿐, **진짜 원인**은 사이드바의 `transform: translateX(-100%)` 가 containing block을 만들어서 안에 있는 `position: fixed` 모달이 viewport가 아닌 sidebar 박스 기준으로 배치되던 것. React Portal로 모달을 `document.body` 직속으로 옮겨서 진짜 fix.

릴리스 일자: 2026-06-29
이전: v0.6.17 (mobile drawer auto-close)

---

## 한 줄 요약

`NewPageButton` / `NewFolderButton` 의 모달 JSX를 `createPortal(<div>, document.body)` 로 감쌈 → 어떤 CSS transform/containing block 영향도 받지 않고 viewport 기준 최상위 중앙 표시.

## 1. 발견 경위

사용자 짚어줌: "아니 대체 왜 새페이지 만들기 팝업이 사이드바 안에 있냐고.. 그냥 화면단위에서 최상위에 센터에 뜨면안되나"

v0.6.17 적용 후 브라우저 측정 결과:

```
modal.getBoundingClientRect() = { x: -320, y: 0, width: 319, height: 633 }
parent = BUTTON#sidebar-vault-row
```

→ 데스크탑에서 모달이 화면 왼쪽 밖(-320px) 에 떠있었음. 데스크탑에선 사이드바 자체가 `translateX(-100%)` 로 화면 밖이라 모달도 같이 화면 밖으로 밀림. 모바일에서는 사이드바가 열리면 모달이 사이드바 안쪽에 갇혀 보임.

## 2. 근본 원인

`.sidebar-offcanvas` CSS:
```css
transform: translateX(-100%);  /* ← containing block 생성 */
```

CSS spec: `transform` / `perspective` / `filter` / `will-change: transform` 가 적용된 요소는 **새 containing block** 이 됨. 그 안에 있는 `position: fixed` 자식은 viewport가 아닌 그 박스를 기준으로 배치됨 (the "fixed-position ancestor" rule).

→ v0.6.17의 `onOpen={onClose}` 는 모바일에서 drawer를 닫아 시각적 가림만 해소했을 뿐, **데스크탑에선 모달 자체가 화면 밖** 이라 onOpen 콜백 발화해도 변화 없음.

## 3. 진짜 Fix — React Portal

```tsx
{open && createPortal(
  <div style={{ position: "fixed", inset: 0, zIndex: 80, ... }}>
    <div className="card">...모달 본문...</div>
  </div>,
  document.body
)}
```

→ 모달을 `document.body` 직속으로 옮기면 React tree는 그대로 (props/state/event 모두 정상), DOM 위치만 body 아래로. 모든 CSS containing block 우회.

## 4. 변경 사항

### 4-1. `dashboard/src/components/NewPageButton.tsx` (+3/-1)

- `import { createPortal } from "react-dom"`
- `{open && (...)}` → `{open && createPortal(..., document.body)}`

### 4-2. `dashboard/src/components/NewFolderButton.tsx` (+3/-1)

- 동일 패턴

### 4-3. `dashboard/tests/Modal-portal.test.tsx` (신규, 4 tests)

회귀 가드:
1. NewPageButton 모달: parent = document.body, primary-sidebar 안에 없음
2. NewFolderButton 모달: 동일
3. 모달 inline style: `position: fixed` + `inset: 0` 명시
4. 모달 부모 chain: aside / complementary / primary-sidebar 어디에도 없음

> jsdom 한계: `getBoundingClientRect()` 가 0 반환, `getComputedStyle` 이 inset shorthand 미분리. 그래서 inline style attribute 직접 검증 + DOM 부모 chain 검증으로 우회.

## 5. v0.6.17 (onOpen={onClose})과의 관계

| 항목 | v0.6.17 | v0.6.18 |
|---|---|---|
| 모바일 drawer 가림 | ✅ 해결 | ✅ 해결 (그대로) |
| 모달이 viewport 중앙 | ❌ sidebar 박스 기준 | ✅ viewport 기준 |
| 데스크탑 모달 보임 | ❌ 화면 밖 (-320px) | ✅ 정상 |

→ **둘 다 필요**. v0.6.17은 UX 보조 (drawer가 가리는 것 방지), v0.6.18은 진짜 위치 fix. onOpen={onClose} 그대로 유지.

## 6. 검증

| 항목 | 결과 |
|---|---|
| vitest (전체) | **12 파일 / 65 tests pass** |
| tsc -b | **exit 0** |
| 브라우저 smoke (Browserbase) | modal parent = document.body, parent chain 비어있음 |

## 7. 후속 작업 후보

- 다른 in-place 모달 컴포넌트도 portal 적용 점검 (EditButton, DeleteButton, VaultPicker 등)
- Type ADR 자동 표시 + 📑 Index 자동 표시 + folder hover 메뉴 (메모리 큐 2번)
- MiniMax 회귀 검증 (메모리 큐 3번)