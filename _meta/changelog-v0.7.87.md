# Changelog v0.7.87 — Dashboard 다크모드 `--color-primary-bg` 누락 patch (2026-07-07)

> **BLUF**: 사용자 보고 (2026-07-07) — "대시보드 홈에서 다크모드로 보면 새볼트 버튼만 하얀 배경에 하얀 텍스트. 안 보임. 다른 버튼이랑 톤 안 맞음". root cause: `--color-primary-bg` 토큰이 **라이트 정의(line 24)에만** 존재, **다크 두 블록(line 385+ `[data-color-mode="dark"]`, line 513+ `html.dark`)에 override가 빠져** 다크에서 라이트 값 `#f4f7fc` 그대로 fallback → `color: var(--color-ink)` (다크 `#f3f4f6` 흰 텍스트)와 **밝은 배경 + 흰 글자 = 안 보임** 조합. 3곳 영향 (HomePage ActionCard primary line 421, HomePage NewPageCard active line 695, PageMetaRow Index chip line 49).
>
> 이전 changelog: `_meta/changelog-v0.7.86.md`

---

## §0 — commit 1개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| (pending) | A. 다크 두 블록에 `--color-primary-bg` override 추가 | `dashboard/src/styles/globals.css` | +2/−0 |

---

## A. `--color-primary-bg` 다크 override 추가

### 진단 (사용자)

홈 다크모드에서 `/vault/new`로 가는 "새 vault" Quick Action 카드만:

- 배경: 밝은 회색-파랑 (라이트 `#f4f7fc`이 그대로 fallback)
- 텍스트: 거의 흰색 (`--color-ink` 다크 `#f3f4f6`)
- = **"하얀 배경 + 흰 텍스트"** → 라벨/설명 안 보임

다른 Quick Action (검색/그래프/디제스트)는 `background: var(--color-canvas)` (다크 `#0f172a`) + 흰 텍스트라 정상이지만, primary 카드는 `--color-primary-bg`만 다크 override가 없었음.

### 진짜 원인

`globals.css`에 다크 정의 두 블록이 있는데 둘 다 `--color-primary` 계열은 있지만 `--color-primary-bg`는 누락:

```css
/* :root (라이트, line 21-24) */
--color-primary: #1c69d4;
--color-primary-active: #0653b6;
--color-primary-disabled: #d4e3f7;
--color-primary-bg: #f4f7fc;          /* ← 라이트만 정의 */

/* [data-color-mode="dark"] (line 385-502) — line 441 */
--color-primary: #3b82f6;
--color-primary-active: #2563eb;
--color-primary-disabled: #1d4ed8;
--color-error-text: #f87171;
/* ← --color-primary-bg 누락 */

/* html.dark (line 513+) — line 519 */
--color-primary: #3b82f6;
--color-primary-active: #2563eb;
--color-primary-disabled: #1d4ed8;
--color-error-text: #f87171;
/* ← --color-primary-bg 누락 */
```

→ 다크 cascade에서 `--color-primary-bg`가 `:root` 라이트 값 `#f4f7fc`을 그대로 사용. `var(--color-ink)`는 다크 `#f3f4f6`이라 가독성 깨짐.

### 영향 범위 (3곳)

`var(--color-primary-bg)` 사용처:

1. `HomePage.tsx:421` — **ActionCard primary** (검색/새 vault/그래프/디제스트 4-up grid 중 새 vault) ← **사용자 보고**
2. `HomePage.tsx:695` — **NewPageCard active** (인라인 폼 토글 시 active 상태) — 같은 카드 가독성 깨짐
3. `PageMetaRow.tsx:49` — Index chip (📑 Index). 다크에서도 `color: var(--color-primary)` 라서 영향 미미하지만 동일하게 fix.

### Fix (surgical, 2줄)

다크 두 블록의 `--color-primary` 정의 직후에 동일 값 추가. 다크 토큰은 line 460의 `--cds-background-brand: rgba(59, 130, 246, 0.14)`와 의미 일치 (BMW Blue @ 14% alpha):

```css
/* [data-color-mode="dark"] */
--color-primary: #3b82f6;
--color-primary-active: #2563eb;
--color-primary-disabled: #1d4ed8;
--color-primary-bg: rgba(59, 130, 246, 0.14);   /* brand soft background — 라이트 #f4f7fc의 다크 동등 (CDS background-brand 톤) */
--color-error-text: #f87171;

/* html.dark — 동일 */
```

### 검증

- `npm run build` (tsc -b + vite build) ✅ 990 modules, CSS 101KB
- Lint (`npm run lint`)는 ESLint 9 flat config 미설정으로 사전부터 실패 (무관, 이 패치와 별개)
- 시각 검증: 사용자 측 다크모드 reload 후 "새 vault" 카드 라벨/설명 가독성 확인 필요

### §13 컴포넌트화 원칙 준수

- 인라인 hex 추가 ❌ (글로벌 CSS 토큰만 사용)
- `var(--cds-background-brand)` 별도 alias 안 만들고 `--color-primary-bg` 직접 다크 정의 (기존 사용처 3곳과 일관)
- surgical, 기존 패턴 100% 동화

### 연관

- v0.7.60 phase 3 — Legacy CDS 다크 override 일괄 작업에서 `--color-primary-bg`가 누락된 회귀. v0.7.87에서 정정.