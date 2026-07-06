# Changelog v0.7.71 — Toast race 회피 + color-primary fallback 정리 (2026-07-06)

> **BLUF**: 3페이지 RAG 점검 (WorkspacePage / GardenPage / VaultManage) 후 도출된 §13.1 + §13.2 위반 2건. per-feature commit 2개. Toast는 race condition 회피 (페이지 unmount 시 setState 경고 해결), color-primary fallback hex 7곳 정리.
>
> 이전 changelog: `_meta/changelog-v0.7.70.md`

---

## §0 — commit 2개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `fb5eb76` | A. GardenPage + VaultManage Toast 자체 setTimeout 제거 | 2 routes | +17/−5 |
| `fe223fc` | B. color-primary fallback hex 7곳 제거 | 4 files (3 routes + 1 component) | +7/−7 |

---

## A. Toast race 회피 (`fb5eb76`)

**문제**: `GardenPage`와 `VaultManage` 두 곳 모두 `<Toast>` 컴포넌트는 import해서 사용 중이었지만, `showToast()` 함수 내부에 **자체 setTimeout(2400ms)** 이 추가 호출되고 있었음:

```ts
function showToast(message, type) {
  setToast({ message, type });
  setTimeout(() => setToast(null), 2400);  // ← unmount 시 setState race
}
```

페이지 전환 (navigate) 직전에 toast가 떴다가 unmount되면, setTimeout이
**unmount된 컴포넌트의 setState**를 호출 → React 경고 + 메모리 leak.

**v0.7.71+ 해결**: `showToast`는 단순 `setToast`만. auto-close는 별도 useEffect가 담당:

```ts
function showToast(message, type) {
  setToast({ message, type });  // 단순 setState
}

// auto-close: race-free
useEffect(() => {
  if (!toast) return;
  const timer = window.setTimeout(() => setToast(null), 2400);
  return () => window.clearTimeout(timer);  // ← unmount / toast 변경 시 cleanup
}, [toast]);
```

**§13.1 정신**: `<Toast>` 컴포넌트 자체는 변동 없음 — auto-close는 부모 페이지 책임.
(auto-close를 Toast에 추가하는 건 over-engineering, 페이지마다 2400ms가 다를 수 있음.)

**검증**: tsc -b --noEmit clean.

---

## B. color-primary fallback hex 7곳 정리 (`fe223fc`)

`var(--color-primary, #hex)` 형태로 fallback hex가 붙은 7곳 — `--color-primary`는
`globals.css`에 정의되어 있어 fallback은 무의미. §13.2 "디자인 토큰 단일성" 위반.

| 파일 | 줄 | 변경 |
|---|---|---|
| `HomePage.tsx` | 416, 496, 694 | `var(--color-primary, #1c69d4)` → `var(--color-primary)` |
| `WorkspacePage.tsx` | 917 | `var(--color-primary, #3b82f6)` → `var(--color-primary)` |
| `Sidebar.tsx` | 250, 670 | `var(--color-primary, #3b82f6)` → `var(--color-primary)` |
| `PageMetaRow.tsx` | 50 | `var(--color-primary, #1c69d4)` → `var(--color-primary)` |

**검증**: tsc -b --noEmit clean.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `tsc -b --noEmit` | clean |
| `git push origin master` | 완료 |

---

## §2 — 후속 후보 (이번 사이클 제외)

| 우선순위 | 항목 | 출처 |
|---|---|---|
| P3 | WorkspacePage / GardenPage 인라인 button style (`neutralButtonStyle`, `dangerButtonStyle` 모듈 상수) → `<Button variant>` 통일 | AGENTS §13.1 — `<Button>` 이미 v0.6.28+ 존재 |
| P3 | 인라인 이모지 잔여 점검 (`🔍 ✚ ⬡ ◐` 외) — GraphPage / LogPage / VaultManage | v0.7.70 SVG 마이그레이션 연속 |
| P3 | Sidebar 즐겨찾기 ★ 버튼 hover/focus 상태 CSS 변수 통일 | §13.2 |

---

## §3 — 사이클 연속성 정리

| 사이클 | §13 적용 |
|---|---|
| v0.7.69 | LogPage 디자인 토큰 통일 (input-base) |
| v0.7.70 A | HomePage Quick Action SVG 마이그레이션 |
| v0.7.70 B | Sidebar vault select 디자인 토큰 통일 |
| v0.7.71 A | GardenPage + VaultManage Toast race 회피 (§13.1) |
| v0.7.71 B | color-primary fallback 7곳 정리 (§13.2) |

→ §13 통일 작업 5번째 사이클 연속.