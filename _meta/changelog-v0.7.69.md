# Changelog v0.7.69 — Dashboard UI/UX 미세 정합 4건 (2026-07-06)

> **BLUF**: 사용자 + agy CLI 의뢰 시도 후 직접 코드베이스 RAG 검토로 도출된
> Dashboard 미세 정합 4건. 기능 추가 ❌ — 죽은 DOM 제거, 들여쓰기 회복,
> debounce 통일, 디자인 토큰 통일. per-feature commit 4개 (surgical 원칙).
>
> 근거: ui-ux-iterative-improvement 스킬 §13 (재사용 컴포넌트·토큰화),
> v0.7.68 REST 관례 정리(B#17) 정신 연속선. **agy 비대화형 모드는 프롬프트
> 해석 실패** — 직접 codebase 읽고 같은 RAG 원칙으로 통합. (agy 의뢰 자체는
> 별도 이슈 추적 안 함 — 도구 한계 기록만.)
>
> 이전 changelog: `_meta/changelog-v0.7.68.md` (P2 백로그 4건)

---

## §0 — 이번 사이클의 commit 4개 (per-feature 분리, v0.7.54+ 원칙)

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `aa8fe03` | A. Sidebar 보관소 select 중복 DOM 제거 | `dashboard/src/components/Sidebar.tsx` | −7 |
| `2d0d054` | B. InlineMarkdownEditor 들여쓰기 정정 (P43b) | `dashboard/src/components/InlineMarkdownEditor.tsx` | +6/−7 |
| `d00a808` | C. useDebounced hook + SearchBar/SearchPage 220ms 통일 | `dashboard/src/lib/useDebounced.ts`(new) + 2 files | +42/−19 |
| `5cccc98` | D. LogPage 액션 필터 .input-base 토큰 통일 | `dashboard/src/routes/LogPage.tsx` | +12/−7 |

---

## A. Sidebar 보관소 select 중복 DOM 제거 (`aa8fe03`)

`dashboard/src/components/Sidebar.tsx:209-242` 에 동일 `onChange`를 가진
`<select>`가 **두 개** 렌더되고 있었음:

- 214줄: `style={{ display: "none" }}` — dead, UI에 안 보임
- 217줄: `style={{ flex: 1 }}` — live, 실제 동작

원인 추정: v0.7.68 이전 사이클에서 "native fallback" 패턴을 남겨두려다
신규 select로 교체하면서 dead 코드가 남음. v0.7.68 REST 관례 정리(B#17)와
같은 정신 — **죽은 인터페이스 정리**.

**검증**: tsc -b --noEmit clean. DOM 노드 1개 절감.

---

## B. InlineMarkdownEditor 들여쓰기 정정 (`2d0d054`, P43b 발견)

`dashboard/src/components/InlineMarkdownEditor.tsx`에 누적된 들여쓰기 drift:

| 위치 | 문제 | 정상 |
|---|---|---|
| L1-3 | JSDoc `/**` 미종결 + 중복 시작 | 단일 JSDoc 블록 |
| L199, 208, 222, 230 | `setToastType` 4줄 8-space over-indent | 6-space |
| L283 | `return (` 직후 `<div>` 5-space | 6-space |
| L424 | `{/* Body */}` 주석 column 0 | 4-space |
| L425 | `<div inline-md-body>` 7-space | 5-space |

원인: v0.7.51 도입 후 여러 차례 patch tool 적용 시 fuzzy match가 누적 drift.
**P43b 신규 함정 발견**: 이미 들여쓰기가 어긋난 파일에 `patch` tool을 쓰면
`new_string`이 정상이어도 `old_string` 매칭이 fuzzy하게 변형되며 drift가 누적.

**해결**: `git checkout` 후 Python byte-level `str.replace()` 직접 수정.
patch tool 회피. 동작/타입 영향 0, 가독성만 회복.

**검증**: tsc -b --noEmit clean.

**스킬 갱신**: `ui-ux-iterative-improvement/SKILL.md` P43b 섹션 추가
(2026-07-06) — 다음 patch부터 Python byte-level 우선 패턴 적용.

---

## C. useDebounced hook 추출 + SearchBar/SearchPage 220ms 통일 (`d00a808`)

`SearchBar.tsx:68-81`은 AbortController만 있고 **debounce 없음** (매 keystroke fetch).
반면 `SearchPage.tsx:24-34`은 220ms `setTimeout` 패턴. 동일 로직인데 페이지마다 다름.

**v0.7.69+ 변경**:

1. `dashboard/src/lib/useDebounced.ts` 신설 — §13 재사용 hook 추출.
   ```ts
   export function useDebounced<T>(value: T, delayMs: number): T
   ```
   입력은 즉시 state 반영, effect는 N ms 후 발화. AbortController는 effect 측 책임.

2. `SearchBar.tsx`, `SearchPage.tsx` 둘 다 `useDebounced(q, 220)` 적용.
   IME 조합 중 / 빠른 typing 시 `/api/vaults/{}/search` 폭주 방지.

**검증**: tsc -b --noEmit clean, vitest 9 passed (관련 회귀 가드).

---

## D. LogPage 액션 필터 디자인 토큰 통일 (`5cccc98`)

`dashboard/src/routes/LogPage.tsx:185-210` 인라인 `<select>`에 하드코딩된
6개 스타일 속성(border/background/color/outline/fontFamily/padding)을
제거하고 `className="input-base"` + 인라인 padding만 유지.

```tsx
<label style={{ display: "inline-flex", alignItems: "center", gap: 8, ... }}>
  액션
  <select className="input-base" style={{ padding: "6px 14px", ... }}>
```

**§13.2 디자인 토큰화 원칙** 충실 — 색/배경은 CSS 변수(`input-base`),
구조 배치(flex/gap)만 인라인.

**§13.1 재사용 컴포넌트 추출은 보류**: `SelectField`은 block label 패턴
(form용), LogPage는 inline 필터 패턴. 2개 사용처가 다른 모양이면 별도
inline 컴포넌트 추가는 다음 사이클.

**검증**: tsc -b --noEmit clean.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `tsc -b --noEmit` | clean |
| `vitest run` (관련 가드) | 9 passed |
| `git push origin master` | `12002ea..5cccc98` ✅ |
| Dashboard restart (`make restart`) | localhost:5173 정상 |

> ⚠️ `pytest tests/` 는 `test_mcp_multi_vault.py` collection error
> (`mcp.server` 모듈 미설치) — 기존 환경 문제, 이번 사이클과 무관.

---

## §2 — 후속 후보 (이번 사이클 제외)

| 우선순위 | 항목 | 출처 |
|---|---|---|
| P2 | HomePage Quick Action 이모지(🔍 ✚ ⬡ ◐) → SVG 통일 | v0.7.69 보고서 5번 (사용자 의도 확인 후) |
| P2 | Sidebar 인라인 select(검색/즐겨찾기) `.input-base` 통일 | LogPage(D)와 동일 패턴 |
| P3 | pytest `test_mcp_multi_vault.py` collection error (`mcp.server`) | 환경 |

---

## §3 — 도구 한계 기록 (agy 비대화형 모드)

`agy --print --print-timeout 6m "<UX 개선 5개 후보 짚어줘>"` 실행 시 모델이
프롬프트 해석 실패 → "이 플래그가 뭔지" 자기 설명 답변 출력.

**원인 추정**: 비대화형 `--print` 모드에서 LLM이 첫 도구 호출 결과(CLI help)를
받아 그 후속으로 해석을 잃고 자기 task로 전환. 페이크 결과 보고 ❌, 즉시
"agy 실패 + 직접 codebase RAG로 통합"으로 전환.

**대안**: 다음 사이클부터 agy 의뢰는 **명시적 코드 영역 지정 + "에러 시
'No tool result interpretation needed' 응답하라"** 명시, 또는 그냥 직접 RAG.