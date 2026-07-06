# Changelog v0.7.70 — Dashboard Quick Action SVG + Sidebar select 통일 (2026-07-06)

> **BLUF**: v0.7.69에서 LogPage 액션 필터 디자인 토큰 통일한 흐름 연속 — HomePage Quick Action 4개 이모지를 Lucide SVG로 마이그레이션하고, Sidebar vault select도 동일하게 `.input-base` 토큰 통일. per-feature commit 2개.
>
> 이전 changelog: `_meta/changelog-v0.7.69.md`

---

## §0 — commit 2개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `57c623d` | A. HomePage Quick Action 4개 이모지 → Lucide SVG | `dashboard/src/routes/HomePage.tsx` | +49/−5 |
| `a6abd82` | B. Sidebar vault select `.input-base` 토큰 통일 | `dashboard/src/components/Sidebar.tsx` | +1/−1 |

---

## A. HomePage Quick Action SVG 마이그레이션 (`57c623d`)

`dashboard/src/routes/HomePage.tsx` 의 4개 Quick Action icon을 Lucide SVG로 교체:

| 액션 | 이전 (이모지) | 이후 (SVG) |
|---|---|---|
| 검색 | 🔍 | `<ActionIcon.Search />` (Circle + Line) |
| 새 vault | ✚ | `<ActionIcon.Plus />` (path cross) |
| 그래프 | ⬡ | `<ActionIcon.Graph />` (4 circles + 연결선) |
| 디제스트 | ◐ | `<ActionIcon.Digest />` (원 + 시계 바늘) |

**§P ui-ux 스킬**: "이모지 ❌ — OS별 렌더링 차이, 다크모드 깨짐". 
InlineMarkdownEditor(v0.7.51)와 동일 패턴 (`currentColor` → 
`var(--color-ink)` 자동 상속, hover 시 `var(--color-accent)`).

**API 변경**: `QuickAction.icon` 타입이 `string` → `React.ReactNode`. 
ActionCard는 `{action.icon}` JSX 렌더링이라 호환 0.

**검증**: tsc -b --noEmit clean.

---

## B. Sidebar vault select 디자인 토큰 통일 (`a6abd82`)

v0.7.69 D(LogPage)와 같은 패턴 — `className="sidebar-vault-select-native"` →
`className="input-base"`. globals.css 디자인 토큰 재사용.

**§13.2 정신**: 색/배경/테두리는 CSS 변수(`.input-base`), 구조 배치
(`flex:1`, `margin:0`)만 인라인 유지.

**검증**: tsc -b --noEmit clean.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `tsc -b --noEmit` | clean |
| `git push origin master` | 완료 |

> ⚠️ pytest `test_mcp_multi_vault.py` collection error는 기존 환경 문제,
> Dashboard 변경과 무관.

---

## §2 — 사이클 연속성 정리

Dashboard 디자인 토큰 통일 3단계 진행:

| 사이클 | 페이지 | 위치 |
|---|---|---|
| v0.7.69 D | LogPage 액션 필터 | `LogPage.tsx:185-210` |
| v0.7.70 A | HomePage Quick Action | `HomePage.tsx:65-94` |
| v0.7.70 B | Sidebar vault select | `Sidebar.tsx:217` |

후속 후보:
- P3: Sidebar 즐겨찾기 ★ 버튼 색상도 토큰 통일 (var(--color-primary) 직접 참조 → CSS 변수만)
- P3: WorkspacePage / GardenPage / VaultManage RAG 점검