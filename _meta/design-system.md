---
title: "Raven Design System (v0.7.59+)"
created: 2026-07-02
updated: 2026-07-02
type: rule
audience: system, agent
confidence: high
---

# Raven Design System

> 3-layer 디자인 토큰 시스템. **Light / Dark 양쪽 모드** 지원. AGENTS.md §13.2 (CSS 변수 우선) + §13.1 (재사용 컴포넌트) 원칙 준수.

## 0. 원칙 (Principles)

1. **변수 우선** — 인라인 hex/rgba ❌, `var(--token)` ✅
2. **3-layer 분리** — Palette (의미 ❌) / Semantic (의미) / Component (별칭)
3. **Dark-first**: 토큰 정의 시 다크값을 우선 검증 (라이트는 fallback/축소)
4. **컴포넌트 일관성** — 같은 의도 = 같은 토큰, 중복 정의 ❌
5. **Vendor-neutral** — 색상 이름은 Raven 만의 용어. (예: `--color-warn` ❌ → `--color-warning`)

## 1. Layer 1 — Palette (원시 색상)

의미 없는 base scale. 라이트/다크 무관, Tailwind-like 명명.

### Slate (중성 회색)

| 토큰 | 값 | 용도 |
|---|---|---|
| `--slate-50` | `#f8fafc` | 다크 bg-subtle, 라이트 bg-canvas alt |
| `--slate-100` | `#f1f5f9` | 라이트 bg-soft, 다크 border-subtle |
| `--slate-200` | `#e2e8f0` | 라이트 border-default, 다크 border-strong |
| `--slate-300` | `#cbd5e1` | 라이트 border-strong, 다크 fg-soft |
| `--slate-400` | `#94a3b8` | 라이트 fg-subtle, 다크 fg-muted |
| `--slate-500` | `#64748b` | 양쪽 fg-muted |
| `--slate-600` | `#475569` | 라이트 fg-muted, 다크 fg-default |
| `--slate-700` | `#334155` | 양쪽 border-hover (dark) |
| `--slate-800` | `#1e293b` | 다크 bg-surface (다크모드 code bg) |
| `--slate-900` | `#0f172a` | 다크 bg-canvas, 라이트 fg-ink |

### Sky (라이트/다크 모두 강조 색조)

| 토큰 | 값 | 용도 |
|---|---|---|
| `--sky-300` | `#7dd3fc` | 다크 인라인 코드 강조 |
| `--sky-500` | `#0ea5e9` | 양쪽 accent (default) |
| `--sky-700` | `#0369a1` | 다크 accent-strong |

### Green (성공)

| 토큰 | 값 | 용도 |
|---|---|---|
| `--green-100` | `#dcfce7` | 성공 bg-soft |
| `--green-500` | `#22c55e` | 성공 accent |
| `--green-700` | `#15803d` | 성공 text |

### Red (위험)

| 토큰 | 값 | 용도 |
|---|---|---|
| `--red-100` | `#fee2e2` | 위험 bg-soft |
| `--red-500` | `#ef4444` | 위험 accent |
| `--red-700` | `#b91c1c` | 위험 text |

### Amber (경고)

| 토큰 | 값 | 용도 |
|---|---|---|
| `--amber-100` | `#fef3c7` | 경고 bg-soft |
| `--amber-500` | `#f59e0b` | 경고 accent |
| `--amber-700` | `#b45309` | 경고 text |

## 2. Layer 2 — Semantic (의미)

Light/Dark 양쪽에 다르게 매핑. **모든 컴포넌트 코드는 Layer 2 이상만 참조** 권장.

### Background

| 토큰 | Light | Dark |
|---|---|---|
| `--bg-canvas` | `--slate-50` | `--slate-900` |
| `--bg-surface` | `#ffffff` | `--slate-800` |
| `--bg-soft` | `--slate-100` | `--slate-700` |
| `--bg-overlay` | rgba(0,0,0,0.5) | rgba(0,0,0,0.65) |

### Foreground (Text)

| 토큰 | Light | Dark |
|---|---|---|
| `--fg-ink` | `--slate-900` | `--slate-50` |
| `--fg-default` | `--slate-700` | `--slate-200` |
| `--fg-muted` | `--slate-500` | `--slate-400` |
| `--fg-subtle` | `--slate-400` | `--slate-500` |
| `--fg-on-accent` | `#ffffff` | `#ffffff` |

### Border

| 토큰 | Light | Dark |
|---|---|---|
| `--border-subtle` | `--slate-200` | `--slate-700` |
| `--border-strong` | `--slate-300` | `--slate-600` |
| `--border-focus` | `--sky-500` | `--sky-300` |

### Accent / Semantic colors

| 토큰 | Light | Dark |
|---|---|---|
| `--accent` | `--sky-700` | `--sky-300` |
| `--accent-hover` | `--sky-500` | `--sky-500` |
| `--success-fg` | `--green-700` | `--green-100` |
| `--success-bg` | `--green-100` | rgba(34,197,94,0.15) |
| `--danger-fg` | `--red-700` | `--red-100` |
| `--danger-bg` | `--red-100` | rgba(239,68,68,0.15) |
| `--warning-fg` | `--amber-700` | `--amber-100` |
| `--warning-bg` | `--amber-100` | rgba(245,158,11,0.15) |

## 3. Layer 3 — Component

Layer 2의 별칭. **컴포넌트 코드는 Layer 3 사용** 권장 (의도가 토큰 이름에 드러나게).

### Button

| 토큰 | Layer 2 참조 | 용도 |
|---|---|---|
| `--btn-primary-bg` | `var(--accent)` | primary 버튼 배경 |
| `--btn-primary-bg-hover` | `var(--accent-hover)` | hover |
| `--btn-primary-fg` | `var(--fg-on-accent)` | primary 텍스트 |
| `--btn-ghost-bg` | `transparent` | ghost 버튼 배경 |
| `--btn-ghost-bg-hover` | `var(--bg-soft)` | hover |
| `--btn-ghost-fg` | `var(--fg-ink)` | ghost 텍스트 |
| `--btn-danger-bg` | `var(--danger-bg)` | danger (delete) 버튼 |
| `--btn-danger-fg` | `var(--danger-fg)` | danger 텍스트 |

### Input / Field

| 토큰 | Layer 2 참조 | 용도 |
|---|---|---|
| `--field-bg` | `var(--bg-canvas)` | input 배경 |
| `--field-bg-readonly` | `var(--bg-soft)` | read-only |
| `--field-border` | `var(--border-subtle)` | input border |
| `--field-border-focus` | `var(--border-focus)` | focus |
| `--field-fg` | `var(--fg-ink)` | input text |

### Toast / Alert

| 토큰 | Layer 2 참조 | 용도 |
|---|---|---|
| `--toast-success-bg` | `var(--success-bg)` | 성공 토스트 bg |
| `--toast-success-fg` | `var(--success-fg)` | 성공 토스트 fg |
| `--toast-error-bg` | `var(--danger-bg)` | 에러 토스트 bg |
| `--toast-error-fg` | `var(--danger-fg)` | 에러 토스트 fg |

### Code

| 토큰 | Layer 2 참조 | 용도 |
|---|---|---|
| `--code-inline-bg` | `var(--bg-soft)` | 인라인 `code` 배경 |
| `--code-inline-fg` | `var(--accent)` (dark: `--sky-300`) | 인라인 코드 |
| `--code-block-bg` | `#1e293b` (라이트) / `#0f172a` (다크) | `pre` 배경 (의도된 강한 대비) |
| `--code-block-fg` | `#e2e8f0` (라이트) / `#f1f5f9` (다크) | `pre` 텍스트 |

### Graph

| 토큰 | Layer 2 참조 | 용도 |
|---|---|---|
| `--graph-bg` | `var(--bg-soft)` | 그래프 canvas bg |
| `--graph-grid` | `var(--border-subtle)` | 그리드 라인 |
| `--graph-surface` | rgba(var(--bg-surface), 0.82) | 노드 라벨 bg |
| `--graph-text` | `var(--fg-ink)` | 노드 텍스트 |
| `--graph-text-muted` | `var(--fg-muted)` | 노드 상세 |
| `--graph-node-outline` | rgba(0,0,0,0.18) / rgba(255,255,255,0.18) | 노드 외곽선 |
| `--graph-edge` | `rgba(0,0,0,0.28)` (라이트) / `rgba(255,255,255,0.22)` (다크) | 엣지 (v0.7.48 다크 전용 가시성 강화 양쪽) |
| `--graph-label-color` | `var(--fg-ink)` | 라벨 색 |
| `--graph-label-shadow` | `0 1px 3px rgba(255,255,255,0.92)` / `0 1px 3px rgba(0,0,0,0.92)` | 라벨 그림자 (반대 톤) |
| `--graph-tooltip-bg` | `var(--bg-canvas)` | 툴팁 bg |
| `--graph-tooltip-border` | `var(--border-subtle)` | 툴팁 border |

### Sidebar / Navigation

| 토큰 | Layer 2 참조 | 용도 |
|---|---|---|
| `--nav-bg` | `var(--bg-canvas)` | 사이드바 bg |
| `--nav-fg` | `var(--fg-ink)` | 사이드바 텍스트 |
| `--nav-active-bg` | `var(--bg-soft)` | 선택된 항목 bg |
| `--nav-active-fg` | `var(--accent)` | 선택된 항목 색 |

## 4. Light/Dark 모드 토글

```css
:root {
  /* Layer 1: Palette — 양쪽 동일 값 */
  --slate-900: #0f172a;
  /* ... */
  /* Layer 2/3: 라이트 기본값 */
  --bg-canvas: --slate-50;
  /* ... */
}

.dark,
[data-color-mode="dark"] {
  /* Layer 2/3: 다크 override */
  --bg-canvas: --slate-900;
  /* ... */
}

[data-color-mode="light"] {
  /* 명시 라이트 토글 (사용자 선택) */
  --bg-canvas: --slate-50;
  /* ... */
}
```

## 5. 적용 규칙 (AGENTS.md §13.2)

### 컴포넌트 코드
- ❌ 인라인 색상 ❌ — `color: "#3b3b3b"` 등
- ❌ 인라인 rgba ❌ — `border: "1px solid rgba(0,0,0,0.1)"`
- ✅ **Layer 3 토큰 우선** — `color: "var(--fg-default)"`
- ✅ **차수 구조 배치만** — `display: flex`, `padding`, `margin` 등 (color/spacing 없이)

### 새 컬러 필요 시
1. **Layer 1** 팔레트에 base 추가 — 예: `--rose-500`
2. **Layer 2** 매핑 정의 (light/dark)
3. **Layer 3** 별칭 — 컴포넌트 의도 노출
4. **changelog** 갱신

### 새 컴포넌트
- Layer 2 토큰 우선, Layer 3 별칭으로 의미 노출
- 인라인 `style={{ color: "#xxx" }}` ❌

## 6. Self-audit

- [x] **3-layer 분리**: Palette / Semantic / Component — 독립적
- [x] **Light/Dark 양쪽 정의**: 모든 Layer 2/3 토큰 양쪽 정의
- [x] **재사용 컴포넌트** (§13.1): `<Toast>`, `<Button>`, `<TextField>` 등 토큰 사용
- [x] **vendor-neutral** (§13): Raven 고유 토큰 이름만
- [x] **런타임 안전**: 미정의 토큰 사용 시 `var(--undefined)` (fallback)

## 7. 마이그레이션 (v0.7.59+)

- **Phase 1** (현재): 토큰 정의 (globals.css)
- **Phase 2**: 컴포넌트 인라인 hex → Layer 3 별칭 (점진적, 변경 시마다)
- **Phase 3**: Light/Dark 양쪽 시각 검증 (Dashboard 모든 화면)

## 8. 참고

- Tailwind CSS Color System — base palette 명명 컨벤션
- IBM Carbon Design System — role-based tokens (cds- 별칭)
- AGENTS.md §13.2 — CSS 변수 우선
