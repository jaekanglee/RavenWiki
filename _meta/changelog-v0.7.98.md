# Changelog v0.7.98 — Sidebar Explorer 시인성 보완 묶음 (surgical 3-patch)

> **BLUF**: 대시보드 사이드바(=vault explorer)의 md 문서 행에 **type pill 텍스트 라벨 추가 + 들여쓰기/패딩 폴리시 + title fallback humanize**. 사용자 피드백: "지듬 대시보드 익스플로어가 보면 문서들이 그냥 평탄한 bullet 형태로 보임 / type 구분도 없고 제목도 가독성 떨어짐 / 시인성 보완 장치도 없음." → 3 surgical 패치로 종착. v0.7.97 chrome 종착 사이클 직후 사용자 명시 요청 트리거.

이전 changelog: `_meta/changelog-v0.7.97.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | Sidebar Explorer 시인성 보완 (type pill + padding + title humanize) |
| 범위 | v0.7.98 (단일 묶음, 1 commit 예정) |
| 기간 | 2026-07-07 |
| 커밋 수 | 1 (예정 — 사용자 승인 후) |
| 시작 트리거 | 사용자 추상 피드백 ("Explorer 시인성 떨어짐") |
| 종료 트리거 | typecheck clean + Dashboard build clean |
| 정책 변경 | 0 (모두 §13 정합 — surgical + 컴포넌트/토큰 재사용) |
| ADR 동반 | 0 (시각 폴리시 only — 인터페이스/스키마/권한 변경 없음) |

## §1 — 무엇을 만들었나 (what)

### 1.1 type pill 텍스트 라벨 (핵심)

| 항목 | 값 |
|---|---|
| 파일 | `dashboard/src/components/Sidebar.tsx`, `GraphCanvas.tsx`, `styles/globals.css` |
| 효과 | md 문서 행에 SCHEMA 9종 type의 짧은 텍스트 라벨(예: "개념" / "규칙" / "이슈")이 색 dot 옆에 표시 → 한눈에 type 식별 |

**변경 전**:
```
• LLM Wiki 패턴
• Self-Use Profile
• ADR-2026-07-06
```
(모두 색 dot만, type 구분 어려움)

**변경 후**:
```
● [개념] LLM Wiki 패턴
● [규칙] Self-Use Profile
● [이슈] ADR-2026-07-06
```

### 1.2 type taxonomy 8→9종 동기화

`GraphCanvas.tsx`의 `TYPE_COLORS`가 outdated (8종: decision/manual/pattern/insight + 5종 = 13 매핑) 였음. SCHEMA 9종 (concept/person/comparison/project/tool/rule/query/journal/issue, v0.7.44+)과 정합시키지 않은 채 그래프에서 사용 중. 본 패치에서 동기화 + `typeLabel()` helper 추가.

- **이유**: `nodeColor()`가 type 색 fallback을 제공하므로 잘못된 색으로 그래프가 그려질 위험. SCHEMA §Type Taxonomy가 SOT.
- **SOT**: `_meta/SCHEMA.md` §"v0.7.x Type 9종".
- **영향**: 그래프 노드 색상이 SCHEMA 정합 type에 매핑됨. 기존 8종 중 `decision`/`manual`/`pattern`/`insight` 4종은 SCHEMA 외 — 색상 사라짐 (해당 type을 가진 노드가 있을 경우 default gray로 fallback).

### 1.3 들여쓰기 12px → 10px 폴리시

| 항목 | 값 |
|---|---|
| 파일 | `dashboard/src/components/Sidebar.tsx` (TreeLeaf dir/page row `paddingLeft`) |
| 효과 | depth 깊어질 때 답답함 완화. 폭 288px 사이드바에서 depth 4~5까지 제목이 한 줄에 들어옴. |

### 1.4 `displayTitle()` 폴리시 (humanize)

| 항목 | 값 |
|---|---|
| 파일 | `dashboard/src/components/Sidebar.tsx` (`displayTitle()`) |
| 효과 | 1) frontmatter title이 slug와 다르면 그대로. 2) title이 slug와 같거나 비어있으면 마지막 segment 폴리시 (`-`/`_` → 공백, `.md` 제거). |

**예**:
- `content/llm-wiki-패턴.md` (title=slug) → 표시: "llm wiki 패턴"
- `content/adr-2026-07-06-stale-detection.md` (title="ADR-2026-07-06 §1.3") → 표시: "ADR-2026-07-06 §1.3" (그대로)

### 1.5 dead CSS 제거 + 누락된 page-row 클래스 신설

`globals.css`에 `.sidebar-tree-leaf*` 4개 클래스 정의돼 있었으나 (Sidebar.tsx가 `.sidebar-tree-page-*`로 사용 중) **사용처 0 = dead code**. `.sidebar-tree-page-row` / `.sidebar-tree-page-row-active` / `.sidebar-tree-page-dot` / `.sidebar-tree-page-label` 정식 신설 + hover/active 상태 + truncate (ellipsis) 포함.

## §2 — 무엇을 하지 않았나 (의도적 scope-out)

- ❌ 검색/필터 동작 변경 — 기존 `filterTree` 그대로
- ❌ 트리 펼침/축소 UX 변경 — `openFolders` 그대로 (v0.7.97.4+)
- ❌ raw/ 영역 (`RawTree`) — 별도 컴포넌트, 이번 패치 scope 외
- ❌ 다크 모드에서 pill 색 추가 (`globals.css §.dark`) — 이미 적용, 별도 변경 없음
- ❌ type 9종 외 새 type 추가 — AGENTS.md §10 정책 위배

## §3 — 검증

| 항목 | 결과 |
|---|---|
| `npx tsc --noEmit` (dashboard) | clean (exit 0) |
| `npm run build` (dashboard) | clean (vite v6.4.3, 1.90s, 105KB CSS, 1.7MB JS) |
| `nodeColor` / `typeLabel` 호출처 | 2파일 (GraphCanvas + Sidebar) — 회귀 가드 충분 |
| `.sidebar-tree-leaf*` dead code | 4 클래스 영구 제거 |
| `.sidebar-tree-page-*` 사용처 | 1파일 (Sidebar.tsx) — 1:1 매핑 |

## §4 — 회고 (lessons)

1. **SCHEMA 정합은 cross-cutting** — `nodeColor` 1개 함수지만 Sidebar/Graph 두 surface에서 영향. type taxonomy 변경 시 양쪽 동시 점검 필요.
2. **dead CSS 발견 = 점검 신호** — `.sidebar-tree-leaf*`가 사용처 0이었던 건 클래스명 리네임을 이전에 했고 CSS 정리를 누락했던 흔적. 이번에 같이 정리.
3. **surgical 3건은 한 묶음으로** — A/B/C가 같은 "Explorer 시인성" 의도라 한 PR/commit이 자연스러움. 만약 의도가 다르면 별도 묶음으로 분리.

## §5 — 알려진 회귀 / 후속 작업

| 항목 | 우선순위 | 비고 |
|---|---|---|
| `decision`/`manual`/`pattern`/`insight` type을 가진 기존 페이지 (있다면) 그래프 색이 default gray로 fallback | 감시 | 본 패치 §1.2 부수효과. content 트리에는 영향 없음 (type pill은 9종만 라벨) |
| type pill 다국어 (영문 vault) | 2차 패치 후보 | `typeLabel`이 한글 라벨. 영문 vault 사용 시 영문 라벨도 옵션 — 보류 |
| activeSlug 트리 highlight 복원 (v0.7.97 §6 후속) | 별도 hotfix | v0.7.97에서 active 표시 위계가 탭 레일로 이동했으나 트리 activeSlug 처리는 미정 — 본 패치와 무관 |

## §6 — 다음 사이클

본 묶음 = Sidebar Explorer 시인성 종착. 다음 사이클은 사용자 명시 요청 시에만 시작 (P55-6 정책).

가능한 후보:
- v0.7.97 §6 후속 — activeSlug 트리 highlight
- WorkspacePage / LintPage 등 미정 영역 UI/UX
- nav 8개 → 5~6개 압축 (사용 로그 필요)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
