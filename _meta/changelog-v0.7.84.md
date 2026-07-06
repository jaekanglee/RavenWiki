# Changelog v0.7.84 — §13.2 잔여 정리 8곳 + Edit/Delete icon SVG (2026-07-06)

> **BLUF**: v0.7.76에서 30곳 CDS 토큰 fallback 정리를 했지만 *fallback 있는 CDS 토큰* 일부 잔존. v0.7.83+ silent hotfix 직후 8곳 잔여 발견 → 정리. EditButton/DeleteButton의 ✏️/🗑 icon 2개도 SVG 통일. per-feature commit 2개.
>
> 이전 changelog: `_meta/changelog-v0.7.83.md`

---

## §0 — commit 2개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `9c901d6` | A. §13.2 잔여 — var(--cds-*, #hex) fallback 8곳 | 6 파일 | +9/−9 |
| `cb77129` | B. EditButton + DeleteButton icon SVG (✏️/🗑) | 2 파일 | +15/−2 |

---

## A. §13.2 잔여 정리 8곳 (`9c901d6`)

### 진단

v0.7.76에서 `var(--cds-*, #hex)` 30곳 정리했으나 **fallback 있는 CDS 토큰** 일부 잔존. globals.css에 `--cds-*` 토큰이 모두 정의되어 있어 fallback 무의미 → 우리 자체 토큰으로 일관성.

### 8개 정리 (페이지별)

| 파일 | 토큰 변환 |
|---|---|
| `HomePage.tsx` | `--cds-background, #f4f4f4` → `--color-surface-soft` |
| `VaultManage.tsx` (×3) | `--cds-danger, #fff1f1` → `--color-danger-bg` (2곳) + `--cds-warning, #fff8e1` → `--color-warning-bg` (1곳) |
| `NewVaultWizard.tsx` | `--cds-background, #f4f4f4` → `--color-surface-soft` |
| `VaultPicker.tsx` (×3) | `--cds-border-subtle-01, #e0e0e0` → `--color-hairline` (2곳) + `--cds-field-01, #f4f4f4` → `--color-surface-soft` (1곳) |
| `NewPageInline.tsx` | `--cds-background, #fff` → `--color-canvas` |
| `PageMetaRow.tsx` | `--cds-background-brand, #f4f7fc` → `--color-primary-bg` |

### 검증

- `tsc -b --noEmit` clean
- `grep 'var(--cds-*, #hex)'` 잔여 0건
- 모든 CDS 토큰이 globals.css에 정의되어 있어 fallback 무의미 → 우리 토큰으로 일관성 (CDS alias layer가 우리 `--color-*` 토큰을 wrapping)

**vendor-neutral 검증**: vendor 명 0건.

---

## B. EditButton + DeleteButton icon SVG (`cb77129`)

### 진단

§P (ui-ux 스킬): 이모지 ❌ (다크모드 깨짐, OS별 렌더링 차이) — **icon 역할 한정**. v0.7.71/v0.7.82에서 정한 정책: "Toast 메시지 안 ✅/❌는 text 안쪽이라 §P 적용 외". 

→ `EditButton`의 `✏️`와 `DeleteButton`의 `🗑`는 *icon 역할*이라 §P 적용 대상.

### 변경

| 파일 | 변환 |
|---|---|
| `EditButton.tsx` | `✏️` → Lucide SVG (Edit, path 2개, 14x14) |
| `DeleteButton.tsx` | `🗑` → Lucide SVG (Trash, polyline + path 4개, 14x14) |

### §13 적용

- `aria-hidden="true"` (decoration) + `title`/`aria-label`로 접근성 유지
- `currentColor` → `var(--color-ink)` 자동 상속 (button 색상 따라 변경)
- `display: block` — button 안 inline span layout 깨짐 방지

### 검증

`tsc -b --noEmit` clean.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `tsc -b --noEmit` | clean |
| `git push origin master` | 완료 |

---

## §2 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.69-76 | §13 통일 (CDS 토큰 / label 이모지 / Button 통일 / EmptyState SVG) |
| v0.7.77-82 | HTTP-only + verify-all + banner 모달 |
| v0.7.83 | silent stale hotfix (MCP lifecycle 통합) |
| v0.7.84 | **§13.2 잔여 8곳 + Edit/Delete icon SVG** |

→ §13 통일 작업 마무리 단계. 잔여 fallback hex 0건 + 잔여 icon 이모지 0건.