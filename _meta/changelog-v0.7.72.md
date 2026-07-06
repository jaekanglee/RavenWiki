# Changelog v0.7.72 — GardenPage Button 통일 + VaultManage icon SVG (2026-07-06)

> **BLUF**: v0.7.71 RAG 후속 — §13.1 (재사용 컴포넌트 우선) + §13 §P (이모지 ❌) 두 가지 연속 적용. per-feature commit 2개.
>
> 이전 changelog: `_meta/changelog-v0.7.71.md`

---

## §0 — commit 2개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `2d61057` | A. GardenPage 인라인 button 5곳 → `<Button variant>` 통일 | `dashboard/src/routes/GardenPage.tsx` | +25/−50 |
| `0538c8d` | B. VaultManage 4개 action icon SVG 마이그레이션 | `dashboard/src/routes/VaultManage.tsx` | +46/−4 |

---

## A. GardenPage 인라인 button → `<Button>` 통일 (`2d61057`)

`GardenPage`에 자체 정의된 `neutralButtonStyle` / `dangerButtonStyle` 모듈 상수 + 5개 `<button style={...}>` 패턴 → `<Button variant="secondary|danger" size="sm">` 컴포넌트 사용.

| 위치 | 변경 전 | 변경 후 |
|---|---|---|
| L243 (선택 아카이브, batch) | `<button style={...dangerButtonStyle}>` | `<Button variant="danger" size="sm">` |
| L341 (편집) | `<button style={...neutralButtonStyle, width:...}>` | `<Button variant="secondary" size="sm" style={width?}>` |
| L350 (아카이브) | `<button style={...dangerButtonStyle, width:...}>` | `<Button variant="danger" size="sm" style={width?}>` |
| L516 (취소) | `<button style={...neutralButtonStyle, width:...}>` | `<Button variant="secondary" size="sm" style={width?}>` |
| L530 (수동 연결) | `<button style={...neutralButtonStyle, padding:..., fontSize:11}>` | `<Button variant="secondary" size="sm" style={{padding, fontSize}}>` |

모듈 상수 `neutralButtonStyle`, `dangerButtonStyle`는 모두 제거 (코드 25줄 감소).

**§13.1 정신**: `<Button>` 컴포넌트 v0.6.28+ 이미 존재, 동일 패턴 재사용.

**검증**: tsc -b --noEmit clean.

---

## B. VaultManage 4개 action icon SVG 마이그레이션 (`0538c8d`)

| 액션 | 이전 (이모지) | 이후 (SVG) |
|---|---|---|
| 지침 검증 | 🔍 | `<ActionIcon.Search />` |
| 지침 당겨오기 | 🔄 | `<ActionIcon.Refresh />` |
| 이름 변경 | ✏️ | `<ActionIcon.Edit />` |
| 보관소 삭제 | 🗑️ | `<ActionIcon.Trash />` |

**§P ui-ux 스킬**: HomePage(v0.7.70)와 동일 패턴 — `currentColor` → `var(--color-ink)` 자동 상속. delete 버튼 빨간 색은 `style={{color: ...}}` 그대로 유지.

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
| P3 | `HomePage.tsx:338` | `✚ 첫 vault 만들기` button text → `<Button variant="pillPrimary">` + icon |
| P3 | `GardenPage.tsx:543` | `🔎 수동 연결...` 잔여 이모지 (위 5개 교체 시 남은 1개) |
| P3 | `EmptyState` 6곳 (GraphPage/PageView/DashboardDigest 등) | `icon="🔍"`, `icon="⚠️"` props — EmptyState 자체 컴포넌트 emoji → SVG 옵션 추가 검토 |
| P3 | `VaultManage.tsx:62,66,94,...` Toast 메시지 안 `✅ ⚠️` | (text 안쪽이므로 의도적 — 유지) |

---

## §3 — 사이클 연속성 (§13 통일 6번째 사이클)

| 사이클 | §13 적용 |
|---|---|
| v0.7.69 | LogPage 디자인 토큰 통일 (input-base) |
| v0.7.70 A | HomePage Quick Action SVG |
| v0.7.70 B | Sidebar vault select 디자인 토큰 |
| v0.7.71 A | GardenPage + VaultManage Toast race 회피 |
| v0.7.71 B | color-primary fallback 7곳 정리 |
| v0.7.72 A | GardenPage 인라인 button → `<Button>` 통일 |
| v0.7.72 B | VaultManage action icon SVG 마이그레이션 |