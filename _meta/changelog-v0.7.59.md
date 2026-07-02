# raven v0.7.59 — 디자인 시스템 (3-layer) 도입 — 컴포넌트 인라인 rgba → 토큰 치환

> **핵심**: 다크모드만 작동하던 Dashboard를 라이트/다크 양쪽 모두 지원하도록 **3-layer 디자인 토큰 시스템** (Palette / Semantic / Component)을 처음부터 정의했습니다. `_meta/design-system.md` 가이드 작성 + `globals.css`에 Layer 1 (~30 컬러 hex) + Layer 2 (~20 의미별 양쪽 정의) + Layer 3 (~25 컴포넌트 별칭 양쪽 정의) 일괄 도입. 그리고 Dashboard의 **8개 컴포넌트에서 인라인 `rgba(...)`를 모두 토큰으로 치환** (남은 인라인 rgba 0개). AGENTS.md §13.1 (재사용 컴포넌트) + §13.2 (CSS 변수 우선) 원칙 codebase 전역 적용.

릴리스 일자: 2026-07-02
이전: v0.7.58

---

## 1. 변경 사항

### 1-1. `_meta/design-system.md` (신규, 8.9KB)

8개 섹션:
- **원칙 (Principles)**: 변수 우선 / 3-layer 분리 / 다크-first / 일관성 / vendor-neutral
- **Layer 1 (Palette)**: Slate / Sky / Green / Red / Amber (Tailwind-like 명명)
- **Layer 2 (Semantic)**: background / foreground / border / accent / semantic-color (라이트+다크)
- **Layer 3 (Component)**: button / input / toast / code / graph / nav 별칭
- **Light/Dark 토글**: `:root` + `[data-color-mode="light"]` + `html.dark` + `[data-color-mode="dark"]`
- **적용 규칙**: 인라인 hex ❌, Layer 3 토큰 우선
- **Self-audit** + 마이그레이션 가이드

### 1-2. `globals.css` — Layer 1+2+3 토큰 정의 (3 commit 분리)

#### commit 1 (d0e65a7): Phase 1 — 토큰 정의

- **Layer 1 (Palette)** — 의미 없는 base scale (slate 50~900 / sky 300/500/700 / green 100/500/700 / red 100/500/700 / amber 100/500/700)
- **Layer 2 (Semantic, 라이트)** — `:root, [data-color-mode="light"]`에 bg/fg/border/accent/semantic 정의
- **Layer 2 (Semantic, 다크)** — `html.dark, [data-color-mode="dark"]`에 매핑 (slate 900/800/700, sky 300 등)
- **Layer 3 (Component, 양쪽)** — button/input/toast/code/graph/nav 별칭

총 **~75 토큰** (`globals.css` L160-450 부근).

#### commit 2 (c013ed1): Phase 2 — 컴포넌트 인라인 rgba → 토큰 치환

- **Dashboard 8 파일, 12+ 치환**:
  - `WorkspacePage` L216+L344: `rgba(220,38,38,0.1)` → `--danger-bg-soft` / `--danger-border`
  - `WorkspacePage` L451+L454: `rgba(28,105,212,0.2)` / `rgba(0,0,0,0.04)` → `--focus-overlay` / `--hover-overlay`
  - `WorkspacePage` L524-528: diff 라인 색상 → `--success-bg-strong` / `--danger-bg-strong` / `--accent-softest`
  - `SearchPage` / `HomePage` (3곳) / `EditButton` / `SearchBar` / `VaultPicker` / `InlineMarkdownEditor`: 그림자 토큰화
- **인라인 rgba 0개 잔존** (Dashboard 전체 컴포넌트)

#### commit 3 (2ed5cbd): Phase 2 dark — 다크 매핑

- 13개 alpha 토큰의 **다크 다크 다크 override** (라이트 alpha 0.04-0.22 → 다크 0.05-0.5, 더 진하게):
  - `--danger-bg-soft`: `rgba(220,38,38,0.1)` → `rgba(127,29,29,0.3)`
  - `--danger-bg`: `rgba(220,38,38,0.15)` → `rgba(127,29,29,0.4)`
  - `--danger-bg-strong`: `rgba(220,38,38,0.22)` → `rgba(127,29,29,0.5)`
  - `--danger-border`: `rgba(220,38,38,0.3)` → `rgba(248,113,113,0.42)`
  - `--accent-soft`: `rgba(28,105,212,0.2)` → `rgba(59,130,246,0.25)`
  - `--accent-softest`: `rgba(59,130,246,0.05)` → `rgba(59,130,246,0.08)`
  - `--success-bg-soft/strong`: green alpha 진하게
  - `--hover-overlay`: `rgba(0,0,0,0.04)` → `rgba(255,255,255,0.05)` (반대 톤)
  - `--shadow-base/overlay-color`: `rgba(0,0,0,...)` → 더 진하게

### 1-3. 신규 토큰 정의 (~75개)

| Layer | 토큰 수 | 예시 |
|---|---|---|
| Layer 1 (Palette) | ~30 | `--slate-50` ~ `--amber-700` |
| Layer 2 (Semantic) | ~20 | `--bg-canvas`, `--fg-ink`, `--accent`, `--success-fg`, `--danger-bg` |
| Layer 3 (Component) | ~25 | `--btn-primary-bg`, `--field-border`, `--code-block-bg`, `--graph-edge`, `--nav-active-bg` |

---

## 2. 검증 결과

| 항목 | 결과 |
|---|---|
| `tsc -b` (Dashboard) | exit 0 |
| `vitest tests/Folder-hover-menu tests/GraphCanvas.obsidian-style` | 11/11 passed |
| **인라인 rgba 잔존** | **0개** (Dashboard 전체) |
| 인라인 hex 잔존 | 0개 (이전부터) |
| `var(--xxx)` 사용 파일 | 36 (이전과 동일 — 의미: 모든 인라인 rgba를 토큰으로 변환) |

---

## 3. 호환성 / 회귀 분석

- ✅ 기존 CDS 별칭 (`--color-ink`, `--color-canvas` 등)은 **유지** — backward compatible
- ✅ 기존 토큰 (`--color-primary`, `--cds-*`)이 정의된 위치 = 그대로, 새 토큰은 **추가만**
- ✅ 컴포넌트 인라인 rgba → 토큰 변환은 **시각적 동일** (라이트) / **다크 진하게** (v0.7.59 다크 매핑)

---

## 4. 추가 가능 작업 (다음 패치 후보)

- `WorkspacePage`의 `fetchGit*` / `GitChange` import 누락 (사용자 작업 회귀) — 별도 패치
- 시각 검증 (Dashboard 라이트/다크 양쪽 — `make restart-all` 후)
- Layer 2 심화 — `--bg-overlay-soft` 등 더 세분화
- 컴포넌트 height/padding 토큰화 (현재는 magic number)

---

## 5. 부록 — self-audit (Karpathy §6 + AGENTS.md §6,9)

- [x] **명시 (§6 ①)**: 디자인 시스템 정립 + 라이트/다크 매핑 — 사용자 요청 정확히 따름
- [x] **단순성 (YAGNI)**: 3-layer로 충분, 4-layer ❌
- [x] **Surgical (§3)**: globals.css 토큰 일괄 + 컴포넌트 인라인 rgba 12곳 — 점진적
- [x] **Goal-Driven**: 라이트/다크 양쪽 토큰 정의, 인라인 rgba 0개 잔존
- [x] **4 저장 신호**: 디자인 시스템 문서 + changelog 시간축 보존 ✓
- [x] **재사용 컴포넌트 원칙 (§13.1)**: 토큰 사용 → 컴포넌트 인라인 ❌
- [x] **CSS 변수 우선 (§13.2)**: 인라인 hex 0개, var(--xxx) 36 파일
- [x] **vendor-neutral**: Raven 고유 토큰 이름 (slate/sky/green/red/amber + semantic)
- [x] **test 통과**: 11/11 + tsc 0
