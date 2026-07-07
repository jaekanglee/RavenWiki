# Changelog v0.7.99 — Sidebar activeSlug 트리 highlight (v0.7.97 §6 후속)

> **BLUF**: v0.7.97 §6 알려진 회귀 "activeSlug 위계 분리 후 트리 highlight 분리" 종착. PageView 진입 시 사이드바 트리에서 해당 md 문서 행이 active 강조되고, nested 폴더 안의 문서면 부모 폴더들이 자동 펼침. 1 commit 4 files.

이전 changelog: `_meta/changelog-v0.7.98.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | Sidebar activeSlug 트리 highlight (v0.7.97 §6 후속) |
| 범위 | v0.7.99 (단일 묶음, 1 commit) |
| 기간 | 2026-07-07 |
| 커밋 수 | 1 |
| 시작 트리거 | v0.7.97 회고 §6 후속, 사용자 명시 요청 |
| 종료 트리거 | tsc clean / vite build clean / 기존 테스트 회귀 0 |
| 정책 변경 | 0 (모두 §13 정합) |
| ADR 동반 | 0 (시각/네비게이션 폴리시 only) |

## §1 — 무엇을 만들었나 (what)

### 1.1 activeSlug 인프라 연결 (v0.7.97 §6 후속)

v0.7.97.3에서 탭 레일로 active 표시 위계 이동했으나 사이드바 트리는 `activeSlug={null}`로 끊겨 있었음 (`Sidebar.tsx:375` 주석). 본 패치에서 Layout→Sidebar→VaultTreeGroup→TreeLeaf로 activeSlug 데이터 흐르게 연결.

| 파일 | 변경 |
|---|---|
| `dashboard/src/components/Layout.tsx` | `useMatch("/page/:vault/*")`로 현재 URL의 slug 추출 → `activeSlug` 계산 → Sidebar prop |
| `dashboard/src/components/Sidebar.tsx` | `SidebarProps.activeSlug: string \| null` 신설 → `VaultTreeGroup` prop 전달 (기존 `null` placeholder 교체) |
| `dashboard/src/components/Sidebar.tsx` | `VaultTreeGroup` useEffect로 activeSlug 변경 시 부모 폴더들 자동 펼침 + localStorage 영속화 |

**데이터 흐름**:
```
URL /page/<vault>/<slug>  →  useMatch  →  activeSlug
  → Layout outlet context
  → Sidebar activeSlug prop
  → VaultTreeGroup activeSlug prop
  → TreeLeaf.slugMatchesActive() 비교
  → 활성 행은 .sidebar-tree-page-row-active (background + font-weight 600)
  → useEffect로 부모 폴더 자동 펼침
```

### 1.2 부모 폴더 자동 펼침 (UX 보너스)

| 항목 | 값 |
|---|---|
| 트리거 | activeSlug 변경 (slug ≠ null) |
| 동작 | slug를 `/`로 split하여 leaf 제외, 모든 조상 폴더 path를 `openFolders`에 추가. `VAULT_OPEN_KEY`도 함께 추가 (루트 vault row 펼침 = 사이드바 펼침) |
| 영속화 | `writeOpenFolders(vault.name, next)` 호출 → 사용자 의도(수동 접기)와 충돌 시 다음 slug 변경에서 다시 펼쳐짐 |
| 회귀 가드 | `changed` 플래그로 setState 동일 참조 반환 → React reconciliation 비용 0 |

**예**: `activeSlug = "content/concept/llm-wiki-패턴"` →
- `["content", "content/concept"]` 둘 다 `openFolders`에 추가
- 사이드바 → vault row 펼침 → `content` 폴더 펼침 → `concept` 폴더 펼침 → 활성 행 노출

### 1.3 회귀 가드 — 기존 테스트 보강

| 항목 | 값 |
|---|---|
| 파일 | `dashboard/tests/Folder-hover-menu.test.tsx` |
| 변경 | `activeSlug={null}` prop 추가 (SidebarProps 신규 prop 따라) |
| 본 패치 전 동작 | tsc build fail (TS2741) — `activeSlug` 누락 |
| 본 패치 후 동작 | tsc clean, 기존 `matchMedia` 환경 이슈는 그대로 (v0.7.97 §6 hotfix 별도 후보) |

## §2 — 무엇을 하지 않았나 (의도적 scope-out)

- ❌ active 행으로 자동 scroll (트리가 길 때 활성 행이 viewport 밖이면 안 보임) — 별도 사이클 후보, 본 패치는 단순 highlight only
- ❌ GraphPage `FloatingGraphPanel`의 `isGraphRoute` active 처리 — 별도 컴포넌트, 본 사이클과 무관
- ❌ `matchMedia` jsdom stub 추가 — v0.7.97 §6 hotfix 후보 (Folder-hover-menu 회귀 + matchMedia stub 함께), 별도 사이클
- ❌ active 페이지의 FrontMatter 변경 시 자동 refresh — 현재는 수동 refresh로 충분
- ❌ 키보드 nav (↑/↓로 트리 행 이동) — 별도 사이클

## §3 — 검증

| 항목 | 결과 |
|---|---|
| `npx tsc --noEmit` (dashboard) | clean (exit 0) |
| `npm run build` (dashboard) | clean (vite v6.4.3, 1.94s, 1.7MB JS) |
| 기존 테스트 회귀 | 0 (`Folder-hover-menu.test.tsx`는 본 패치 전에도 `matchMedia` 이슈로 실패 중 — 회귀 아님) |
| `useMatch` 호출처 | 1 (Layout) — PageView만 매칭, 다른 라우트(/search 등)는 무관 |
| `activeSlug` prop chain | Layout → Sidebar → VaultTreeGroup → TreeLeaf — 1:1 흐름 |

## §4 — 회고 (lessons)

1. **인프라 다 갖춰놓고 prop이 끊긴 케이스** — v0.7.97에서 `slugMatchesActive` 로직 + `activeSlug` prop + `VaultTreeGroup` 사용처 다 있었는데 Layout→Sidebar 연결만 빠져 있었음. v0.7.97 §6 "별도 hotfix"로 예고된 정확한 케이스. **코드 자체는 옳고 wiring만 추가**.
2. **컴포넌트 props에 주석으로 `null` 박아두기 = 미완 표시** — `activeSlug={null /* 별도 로직 필요 */}` 주석이 의도를 명확히 했음. 다음 사이클에서 따라 잡기 좋은 신호.
3. **회귀 가드 = tsc + 기존 테스트** — 신규 prop 추가 시 기존 테스트가 tsc로 잡아냄 (이번처럼). 사람이 일일이 확인 안 해도 됨.
4. **자동 펼침 = UX 필수** — highlight만 추가하고 펼침 안 했으면 사용자가 매번 폴더 클릭해야 함. 1 useEffect로 끝나니 함께.

## §5 — 알려진 회귀 / 후속 작업

| 항목 | 우선순위 | 비고 |
|---|---|---|
| `matchMedia` jsdom stub 추가 | hotfix | v0.7.97 §6 후보. `Folder-hover-menu.test.tsx` + 신규 회귀 가드 테스트가 모두 이 이슈로 실패. 별도 패치 |
| active 행 자동 scroll (long tree viewport) | 2차 패치 후보 | `scrollIntoView` + 옵저버 1 useEffect — 본 패치는 highlight only |
| active 행 좌측 border-bar (가로형 highlight 강화) | 2차 패치 후보 | type pill 색과 별개로 "이 페이지" 시각화. 본 패치는 background만 |
| 키보드 nav (↑/↓) | 별도 사이클 | 트리 행 키보드 이동 + Enter로 페이지 열기 |

## §6 — 다음 사이클

본 묶음 = v0.7.97 §6 후속 종착. 다음 사이클은 사용자 명시 요청 시에만 시작 (P55-6).

가능한 후보:
- `matchMedia` jsdom stub + Folder-hover-menu 회귀 hotfix (v0.7.97 §6 잔여)
- active 행 자동 scroll (UX 강화)
- WorkspacePage / LintPage 등 미정 영역 UI/UX (큰 사이클)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
