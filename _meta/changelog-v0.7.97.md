# Changelog v0.7.97 — Dashboard UI Shell 3단 분리 묶음 회고 (v0.7.97.1~97.4.2)

> **BLUF**: Dashboard 상단 chrome을 **헤더(utility) + 탭 레일(section nav) + 사이드바(explorer) 3단으로 분리**. Codex 안 1 채택. 사이드바 resize 핸들 추가 + drag 성능 2단계 최적화. 3-party (Codex/Claude/Antigravity) 검토 후 결정. **본 묶음 = Dashboard chrome 종착**. 다음 사이클은 사용자 명시 요청 시에만 시작.

이전 changelog: `_meta/changelog-v0.7.96.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | Dashboard UI Shell 3단 분리 (헤더 / 탭 레일 / 사이드바) |
| 범위 | v0.7.97 ~ v0.7.97.4.2 (7 commit) |
| 기간 | 2026-07-07 (1일) |
| 커밋 수 | 7 |
| 시작 트리거 | 사용자 추상 피드백 (헤더 정돈 안됨 / 가운데 공간 비는 듯 / 검색 위치 의문) |
| 종료 트리거 | 사용자 명시 만족 ("좋아 확인했어") |
| 정책 변경 | 0 (모두 §13 정합) |
| ADR 동반 | 1 (`adr-2026-07-07-dashboard-header-tab-rail-sidebar-v0-7-97.md`) |

## §1 — 무엇을 만들었나 (what)

### 1.1 3단 분리 (v0.7.97.3 — `8bb6df9`, **핵심 결정**)

| Zone | Role | 위치 | 내용 |
|---|---|---|---|
| **Header** | utility state | 52px sticky 풀폭 | 좌(☰ 🐦 Raven) / 우(☀️🌙 theme) |
| **Section Nav Rail** | section nav | 44px sticky 헤더 아래 | 8개 가로 탭 (홈/그래프/검색/로그/린트/정원/워크스페이스/관리) |
| **Sidebar** | vault explorer | 288px (resize 200~480) 데스크탑 상시 노출 | 검색 + 보관소 + 트리 필터 + 트리 + raw + stats widget |

이전: 헤더 1줄 풀폭에 8개 컴포넌트 동급 (가운데 빈 공간 ❌) / 사이드바는 off-canvas drawer (항상 숨김)

### 1.2 Sidebar Resize (v0.7.97.4 ~ 4.2)

- **97.4** (`18450bc`): 우측 6px 핸들, drag로 200~480px 조정, 더블클릭 → 기본값(288)
- **97.4.1** (`4575a9c`): drag 중 React re-render 우회 (ref 기반 DOM 직접 조작)
- **97.4.2** (`1ce8b20`): drag 중 transition/layout containment 차단 (paint 비용 폭증 해결)

### 1.3 기타

- **97.0** (`e34cccd`): 1차 패치 — 헤더 그룹화 + 검색 사이드바 통합
- **97.1** (`3488835`): 3-zone 헤더 (user reject: 가운데 비는 듯)
- **97.2** (`5b7c957`): 헤더 슬림화 + nav 사이드바 통합 (user reject: 사이드바에 우겨넣은거 병신같아)

## §2 — 왜 이렇게 (why)

### 2.1 user feedback 패턴 (3번 reject → 1번 합의)

| Round | 시도와 user feedback |
|---|---|
| 1차 | 헤더 그룹화 + 검색 사이드바 통합 → "아이콘이 버튼보다 커 다듬어" (별개) |
| 97.1 | 3-zone sticky 헤더 → **"가운데 공간 비는구만"** |
| 97.2 | 헤더 슬림 + nav 사이드바 vertical pill → **"이 방식도 별로야, 사이드바에 우겨넣은거"** |
| **97.3** | 3단 분리 (Codex 안 1) → **"좋아 확인했어"** ✅ |

3번 reject가 결정 후보군을 좁히는 가드 역할.

### 2.2 3-party 검토

- **Codex (Codex CLI)**: 안 1 (유틸리티 헤더 + 탭 레일) 권장
- **Claude (Claude Code)**: 안 2 (통합 사이드바 재정렬) 권장 — surgical, user reject 패턴 직접 위반
- **Antigravity (MCP)**: timeout, 무효

ADR §Decision에서 Codex 안 1 채택 이유 3개:
1. user reject 패턴 (가운데 빈 / 우겨넣기) 직접 회피
2. PKM 정체성 부합 (Obsidian/Bear vs Linear/Vercel)
3. 3단 정보위계 명확 (utility / section / explorer)

## §3 — 어떻게 만들었나 (how)

### 3.1 surgical 단계 분리

| 단계 | 변경 | 파일 |
|---|---|---|
| 1차 | SearchBar variant prop, Sidebar에 통합 | SearchBar.tsx, Sidebar.tsx, Layout.tsx |
| 97.1 | Layout 헤더 3-zone grid | Layout.tsx, globals.css |
| 97.2 | Layout 헤더 슬림 + Sidebar SIDEBAR_NAV 추가 | Layout.tsx, Sidebar.tsx |
| 97.3 | Layout 탭 레일 + Sidebar SIDEBAR_NAV 제거, 데스크탑 상시 노출 | Layout.tsx, Sidebar.tsx, globals.css |
| 97.4 | Sidebar resize 핸들 | Sidebar.tsx, globals.css |
| 97.4.1 | ref 기반 DOM 직접 조작 | Sidebar.tsx |
| 97.4.2 | drag 중 transition 무력화 + layout containment | Sidebar.tsx, globals.css |

### 3.2 §13 준수

- **§13.1**: SearchBar variant (header/sidebar 재사용), GLOBAL_NAV 정의 1곳 (Layout.tsx)
- **§13.2**: .section-nav-tab, .app-header-theme-btn CSS 변수 위임
- **§13.3**: vault-row button → div+role=button (중첩 <button> 회귀 해결)
- 즐겨찾기 hover JS 이벤트 → CSS class 토큰화 (.sidebar-favorite-btn)

## §4 — 검증 (verification)

| 단계 | tsc | vite build | 비고 |
|---|---|---|---|
| 1차 | 0 | 0 | — |
| 97.1 | 0 | 0 | — |
| 97.2 | 0 | 0 | Folder-hover-menu 테스트 회귀 1건 (v0.6.22부터 잠재) |
| 97.3 | 0 | 0 | — |
| 97.4 | 0 | 0 | — |
| 97.4.1 | 0 | 0 | — |
| 97.4.2 | 0 | 0 | drag 매끄러움 확인 |

## §5 — 회고 (lessons)

1. **3-party 검토는 가치가 있으나 시간 비용 큼** — 갈릴 때 ADR로 명시적 결정 + 이유 기록이 안전
2. **사용자 거부 패턴이 결정의 정합성 가드** — "가운데 빈 ❌", "우겨넣기 ❌" 두 번의 거부가 3안 후보군을 좁힘
3. **PKM 정체성 부합도가 패턴 선택의 1차 기준** — Linear/Vercel식 아름다움보다 Obsidian/Bear식 정보위계 우선
4. **surgical 변경은 좋되 방향이 명확할 때 한 번에** — 3번 뒤집기보다 1번 합의 후 가는 게 총 비용 ↓
5. **성능 디버깅은 단계적으로** — 4.1 (state 우회) → 4.2 (CSS 우회). 한 번에 다 적용해도 되지만 단계별 검증으로 회귀 가드 ↑

## §6 — 알려진 회귀 / 후속 작업

| 항목 | 우선순위 | 비고 |
|---|---|---|
| Folder-hover-menu 테스트 회귀 | hotfix | v0.6.22부터 잠재, TreeLeaf dir case에 NewPageButton 없음 |
| nav 8개 부담 (사용 빈도 낮은 항목 secondary 분리) | 2차 패치 후보 | 사용 로그 없이 추측성 결정이므로 보류 |
| activeSlug 위계 분리 후 트리 highlight 분리 | 별도 hotfix | 탭 레일로 active 표시 위계 이동했으나 트리 activeSlug 처리 정리 필요 |

## §7 — 다음 사이클

**본 묶음 = Dashboard chrome 종착**. 다음 사이클은 사용자 명시 요청 시에만 시작 (P55-6).

가능한 후보:
- Folder-hover-menu 회귀 hotfix (가벼움)
- nav 사용 로그 수집 → 8개 → 5~6개 압축 검토 (UX 결정 필요)
- WorkspacePage/LintPage 등 별도 페이지 UI/UX (다음 큰 사이클)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>