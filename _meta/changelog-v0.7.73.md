# Changelog v0.7.73 — EmptyState SVG + Button 통일 3건 (2026-07-06)

> **BLUF**: v0.7.72 잔여 §13.1 + §P 작업 3단계 — EmptyState icon prop 확장, 13개 호출처 emoji → SVG, 새로고침/first vault 버튼 `<Button>` 통일. per-feature commit 4개 (icon object 추가 포함).
>
> 이전 changelog: `_meta/changelog-v0.7.72.md`

---

## §0 — commit 4개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `30ad60b` | A. EmptyState icon prop ReactNode 확장 + 기본값 SVG | `dashboard/src/components/ui/EmptyState.tsx` | +37/−5 |
| `e510734` | B. EmptyIcon object + 13개 호출처 emoji → SVG | `lib/emptyIcons.tsx`(new) + 7 routes | +133/−14 |
| `12bc765` | C. 🔄 새로고침 + ✚ first vault `<Button>` + SVG 통일 | `emptyIcons.tsx` + 4 routes | +36/−29 |

---

## A. EmptyState icon prop ReactNode 확장 (`30ad60b`)

`EmptyState` 컴포넌트의 `icon` prop 타입을 `string` → `React.ReactNode`로 확장.
기본값도 `📭` 이모지 → Lucide-style Inbox SVG (`DefaultInboxIcon`).

**호환성**: `React.ReactNode`는 `string`을 포함하므로 기존 호출처 (string emoji)는 그대로 동작.

**검증**: tsc -b --noEmit clean.

---

## B. EmptyIcon object + 13개 호출처 SVG 교체 (`e510734`)

`dashboard/src/lib/emptyIcons.tsx` 신설 (§13 §P 공통 icon object, HomePage/VaultManage의
ActionIcon 패턴과 동일).

13개 호출처 emoji → `<EmptyIcon.X />` 교체:

| 페이지 | 변경 |
|---|---|
| `SearchPage.tsx` | 🔎 → Search, 🗂 → Folder |
| `PageView.tsx` | 🔍 → File |
| `GraphPage.tsx` | 🕸 → Spinner, ⚠️ → AlertTriangle, 🗂 → Database, 🌫 → Fog, 🔎 → Search |
| `LintPage.tsx` | 🎉 → Check |
| `WorkspacePage.tsx` | ⚠ → AlertTriangle |
| `GardenPage.tsx` | ✨ → Sparkles, 🕸️ → Network |
| `RawPanel.tsx` | ⏳ → Loader, ⚠️ → AlertTriangle |

**검증**: tsc -b --noEmit clean.

---

## C. 🔄 새로고침 + ✚ first vault `<Button>` 통일 (`12bc765`)

§13.1 (재사용 컴포넌트 우선) + §P (이모지 ❌) 동시 적용.

| 위치 | 변경 |
|---|---|
| `LintPage.tsx` 🔄 새로고침 | `<button className="btn-secondary" style={...}>` → `<Button variant="secondary" size="sm">` + `<EmptyIcon.Refresh />` |
| `LogPage.tsx` 🔄 새로고침 + 🗒 raw | 동일 패턴 |
| `WorkspacePage.tsx` 🔄 새로고침 | 동일 패턴 (`<button ` 후행 공백 drift 발견 — P43b 사례) |
| `HomePage.tsx` ✚ 첫 vault 만들기 | `<Link className="btn-pill-primary">` 안에 `<ActionIcon.Plus />` 추가 |

**`EmptyIcon.Refresh` icon**도 `emptyIcons.tsx`에 추가 (위 B 사이클 누락분 보완).

**§13.1**: `<Button>` 컴포넌트 v0.6.28+ 사용. 인라인 `<button>` + `className="btn-*"` 패턴 4곳 정리.

**검증**: tsc -b --noEmit clean.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `tsc -b --noEmit` | clean |
| `git push origin master` | 완료 |

---

## §2 — 잔여 §13 후보 (이번 사이클 제외)

| 우선순위 | 위치 | 항목 |
|---|---|---|
| P3 | `Sidebar 즐겨찾기 ★ 버튼` | hover/focus 상태 CSS 변수 통일, ★ glyph 자체는 intent 유지 |
| P3 | `HomePage.tsx:201-247` `Quick Action` (이미 v0.7.70 SVG 완료) ActionCard | 인라인 style 정리 (CSS 변수만 사용) |
| P3 | `VaultManage.tsx:630` `지침 당겨오기 🔄` label 옆 emoji | button과 별개로 label 옆 잔여 → 별도 패치 |

---

## §3 — 사이클 연속성 (§13 통일 7번째 사이클)

| 사이클 | §13 적용 |
|---|---|
| v0.7.69 | LogPage 디자인 토큰 통일 (input-base) |
| v0.7.70 | HomePage Quick Action SVG + Sidebar select 디자인 토큰 |
| v0.7.71 | Toast race 회피 + color-primary fallback 정리 |
| v0.7.72 | GardenPage Button 통일 + VaultManage icon SVG |
| v0.7.73 | **EmptyState SVG 13곳 + 새로고침/first vault Button 통일** |