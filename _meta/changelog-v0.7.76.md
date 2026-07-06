# Changelog v0.7.76 — §13 잔여 cleanup 3건 (CDS 토큰 + label emoji + 즐겨찾기 hover) (2026-07-06)

> **BLUF**: v0.7.73 §2 잔여 §13 작업 3건 — `var(--cds-*, #hex)` fallback 30곳, VaultManage label 이모지, Sidebar 즐겨찾기 hover. per-feature commit 3개.
>
> 이전 changelog: `_meta/changelog-v0.7.75.md`

---

## §0 — commit 3개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `735e90e` | A. `var(--cds-*, #hex)` fallback 30곳 정리 | `globals.css` + 4 routes/components | +31/−30 |
| `0f37dde` | B. VaultManage label 이모지 → SVG | `VaultManage.tsx` | +6/−2 |
| `01ab6e8` | C. Sidebar 즐겨찾기 ★ hover/focus 명시 | `globals.css` + `Sidebar.tsx` | +19/−1 |

---

## A. `var(--cds-*, #hex)` fallback 30곳 정리 (`735e90e`)

**RAG 발견**: v0.7.71 B에서 `var(--color-primary, #hex)` 정리는 했지만 CDS (Carbon Design
System) 토큰 fallback은 잔존. CDS 토큰은 globals.css에 **정의되어 있지 않아** fallback hex가
항상 적용되고 있었음 → 우리 자체 토큰으로 교체.

### 신설 토큰

- `--color-primary-bg: #f4f7fc` (brand soft background, CDS `background-brand` 동등)

### 매핑 (30곳)

| CDS 토큰 | 우리 토큰 | 사용처 |
|---|---|---|
| `--cds-field-01` (background) | `--color-canvas` / `--color-surface-soft` | HomePage, VaultManage, NewVaultWizard, NewPageInline |
| `--cds-border-subtle-01` | `--color-hairline` | 4 파일 |
| `--cds-background-brand` | `--color-primary-bg` (신설) | HomePage ActionCard primary, NewPageCard active |
| `--cds-danger-text` | `--color-danger-text` | VaultManage |
| `--cds-danger` / `--cds-danger-border` | `--color-danger-bg` / `--color-danger-border` | VaultManage |
| `--cds-support-success` / `support-success-text` | `--color-success-bg` / `--color-success-text` | VaultManage bootstrap chip |
| `--cds-support-error` | `--color-error-text` | NewVaultWizard |
| `--cds-warning-border` | `--color-warning-border` | VaultManage bulk banner |
| `--cds-border-interactive` | `--color-primary` | NewPageInline |

### §13 적용

- §13.2: 색/배경 모두 globals.css 정의 토큰 사용 (CDS fallback ❌)
- §13.3: 인라인 hex fallback ❌ (모두 토큰으로 치환)

**검증**: tsc -b --noEmit clean.

---

## B. VaultManage label 이모지 → SVG (`0f37dde`)

vault row의 두 action button 라벨 (`지침 검증 🔍`, `지침 당겨오기 🔄`)에 잔존한 이모지를
`ActionIcon.Search` / `ActionIcon.Refresh` (Lucide SVG, v0.7.72에서 정의)로 교체.

**§P ui-ux 스킬**: 이모지 ❌ (다크모드 깨짐, OS별 렌더링 차이) → SVG (currentColor).

**검증**: tsc -b --noEmit clean.

---

## C. Sidebar 즐겨찾기 ★ hover/focus 명시 (`01ab6e8`)

v0.7.73 §2 잔여. 기존 hover/focus 처리가 없어 키보드 사용자/마우스 hover 모두 시각적 피드백 없음.

### 변경

- **신설 토큰**: `--color-favorite-hover-bg: #f4f7fc` (primary soft)
- **Sidebar 즐겨찾기 button**:
  - `onMouseEnter` / `onMouseLeave` 핸들러
  - `onFocus` / `onBlur` 핸들러
  - 배경: `transparent` ↔ `var(--color-favorite-hover-bg)`
  - border: `var(--color-hairline)` ↔ `var(--color-primary)`
  - transition: `background-color + border-color + color 0.15s ease`
  - `outline: none` (focus 표현을 border-color로 통일)

### §13 적용

- §13.1: `<Button>` 컴포넌트화는 over-scope (단일 사용처) → inline style + React event handler
- §13.2: 색/배경 CSS 변수만 사용

**검증**: tsc -b --noEmit clean.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `tsc -b --noEmit` | clean |
| `git push origin master` | 완료 |

---

## §2 — 사이클 연속성 (§13 통일 8-9번째 사이클)

| 사이클 | §13 적용 |
|---|---|
| v0.7.69 | LogPage 디자인 토큰 (input-base) |
| v0.7.70 | HomePage Quick Action SVG + Sidebar select 디자인 토큰 |
| v0.7.71 | Toast race 회피 + color-primary fallback |
| v0.7.72 | GardenPage Button + VaultManage icon SVG |
| v0.7.73 | EmptyState SVG 13곳 + 새로고침/first vault Button |
| v0.7.75 | VaultManage 자동 verify-all + 일괄 업뎃 banner |
| v0.7.76 | **CDS 토큰 30곳 정리 + label 이모지 + 즐겨찾기 hover** |

→ §13 통일 작업 약 9번째 사이클. 신규 토큰 2개 추가 (`--color-primary-bg`, `--color-favorite-hover-bg`).