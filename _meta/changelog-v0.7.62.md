# raven v0.7.62 — WorkspacePage 모바일 반응형 (744px breakpoint)

> **핵심**: v0.7.61에서 추가한 워크스페이스 OS 트리 + .md 미리보기가 모바일(폭 < 744px)에서 비좁았음 — 좌측 stacked 컨테이너가 가로 폭 320px 강제 + 우측 패널 paddingLeft 12px + 리사이저가 column에서도 표시됨. v0.7.62에서 `isMobile` state + `window.innerWidth` 기반으로 레이아웃 분기.

릴리스 일자: 2026-07-03
이전: v0.7.61

---

## 1. 변경 사항

### 1-1. `WorkspacePage.tsx` — 모바일 레이아웃 분기

```tsx
const MOBILE_BREAKPOINT = 744;
const [isMobile, setIsMobile] = useState(() => window.innerWidth < MOBILE_BREAKPOINT);
useEffect(() => {
  const onResize = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
  window.addEventListener("resize", onResize);
  return () => window.removeEventListener("resize", onResize);
}, []);
```

### 1-2. 레이아웃 분기

| 요소 | 데스크탑 (≥ 744px) | 모바일 (< 744px) |
|---|---|---|
| 메인 split view `flex-direction` | `row` | **`column`** |
| 좌측 stacked 컨테이너 `width` | `leftWidth` (320px, 리사이저로 조절) | **`100%`** |
| 좌측 컨테이너 `border-right` | `1px solid var(--color-hairline)` | **`none`** |
| 좌측 컨테이너 `border-bottom` | `none` | **`1px solid var(--color-hairline)`** (섹션 분할) |
| 좌측 컨테이너 `max-height` | `none` | **`50vh`** (화면 절반, 나머지 미리보기 영역 확보) |
| 리사이저 divider | 표시 | **숨김** (column stack엔 폭 조절 불필요) |
| 우측 패널 `paddingLeft` | `12px` | **`0`** |
| 우측 패널 `paddingTop` | `0` | **`12px`** |

### 1-3. 동작 (시나리오)

**데스크탑 1024px+ (변화 ❌)**:
- 좌측 stacked: 트리(상) + 변경사항(하), 320px 폭
- 우측: diff viewer 또는 md preview
- 리사이저 1개로 좌측 폭 조절

**모바일 375px (예: iPhone SE)**:
```
┌────────────────────┐
│  ① 트리 (max 50vh)  │ ← 워크스페이스 OS 트리, breadcrumb + ⬆
│                     │
├────────────────────┤  ← border-bottom
│  ② 변경사항 (auto)  │ ← Git 변경파일
│                     │
├────────────────────┤
│  ③ 미리보기 (auto)  │ ← .md 인라인 또는 diff
│                     │
└────────────────────┘
```

각 섹션이 viewport 폭 100% 차지 + `overflow-y: auto`로 자체 스크롤. **세로 스크롤 한 번에 페이지 전체가 자연스럽게 흐름**.

### 1-4. resize 핸들링

`window.resize` 이벤트마다 `setIsMobile(innerWidth < 744)`. 데스크탑 ↔ 모바일 전환 시 즉시 레이아웃 리플로우 (리사이저 200~800px clamp는 데스크탑에서만 의미 있으므로 모바일에서 hide).

---

## 2. 검증 결과

| 항목 | 결과 |
|---|---|
| `cd dashboard && npm run build` (tsc -b + vite build) | exit 0, 988 modules |
| `cd dashboard && npm test -- --run` | **116/116 passed** (회귀 ❌) |
| 수동 검증 | (사용자) 모바일 375px / 744px+ / 1024px+ 3 케이스 |

---

## 3. 안전성 / 정책 정렬

- **744px breakpoint** — Raven 글로벌 breakpoint와 정합 (기존 sidebar/mobile-nav 패턴과 동일).
- **NO 5th entry point 추가 ❌** — WorkspacePage 1개 파일만 수정.
- **§13.1 재사용 컴포넌트** — 새 컴포넌트 ❌. 인라인 style 분기만 (간단한 CSS 분기).
- **§13.2 CSS 변수 우선** — 인라인 hex 0개, 모든 색은 `var(--xxx)`.

---

## 4. 추가 가능 작업 (다음 패치 후보)

- 모바일에서 트리 섹션 header에 collapse/expand 토글 (현재는 항상 펼침)
- 모바일에서 미리보기 닫기 버튼 위치 개선 (현재 ✕ 우상단 — 모바일에서 thumb zone 아닐 수 있음)
- `MOBILE_BREAKPOINT`를 `dashboard/src/styles/globals.css`의 CSS 변수로 추출 (현재는 .tsx 상수)
- `useMediaQuery` 훅 추출 (WorkspacePage 외 다른 페이지도 재사용 가능)

---

## 5. 부록 — self-audit (Karpathy §6 + AGENTS.md §6,9)

- [x] **명시 (§6 ①)**: "워크트리가 모바일 상태에서 참 친화적이지 않네" — 사용자 요청 정확히 따름
- [x] **단순성 (YAGNI)**: useState + resize listener만, useMediaQuery 훅 추출 ❌ (1개 페이지에서만 씀)
- [x] **Surgical (§3)**: 1 파일 수정. 다른 페이지/컴포넌트 미접촉
- [x] **Goal-Driven**: 744px 기준 2-case 분기, 데스크탑 회귀 ❌
- [x] **4 저장 신호**: changelog (사용자 UX 개선 이력) — 재사용 가치 높음
- [x] **재사용 컴포넌트 (§13.1)**: 새 컴포넌트 ❌, 인라인 분기만
- [x] **CSS 변수 우선 (§13.2)**: 인라인 hex 0개