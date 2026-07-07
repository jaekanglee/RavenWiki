---
title: 헤더+탭 레일+사이드바 3단 분리 — UI shell 재구성 (v0.7.97)
created: 2026-07-07
type: adr
status: accepted
scope: dashboard/src/components/{Layout,Sidebar,SearchBar}.tsx + globals.css
audience: agent
---

# ADR: Dashboard UI Shell 3단 분리 (v0.7.97)

> **결론**: Dashboard 상단 chrome을 **헤더(utility) + 탭 레일(section nav) + 사이드바(explorer) 3단으로 분리**. Codex 안 1 채택.

## Context

Raven Dashboard는 옵시디언 대안 PKM 도구로, 사람 1차 사용자의 vault 탐색 표면이다.
v0.7.97 이전 헤더는 1줄 풀폭에 8개 컴포넌트가 동급으로 배치되어:

1. 정보위계 부재 (브랜드 / vault / 검색 / nav 8개 / theme가 한 줄)
2. 시각 노이즈 과다 (좌측정렬 + 가운데 빈 공간 + 우측 nav tabs 비대칭)
3. PKM 정체성 불일치 (Linear/Vercel식 SaaS 헤더 chrome)

검색을 헤더에서 사이드바로 이관한 1차 패치 이후도, "가운데 빈 공간", "사이드바에 nav 8개 우겨넣기" 두 번의 user rejection 후 본 ADR의 결정으로 종착.

## Decision

**헤더 / 탭 레일 / 사이드바 3단 분리**. Codex 안 1 채택.

```
┌────────────────────────────────────────────────────────────┐
│ Header (52px, sticky)                                      │
│  [☰ 🐦 Raven]                            [☀️🌙 theme]    │
├────────────────────────────────────────────────────────────┤
│ Section Nav Rail (44px, sticky)                            │
│  [홈] [그래프] [검색] [로그] [린트] [정원] [WS] [관리]    │
├──────────┬─────────────────────────────────────────────────┤
│ Sidebar  │                                                 │
│ (288px,  │  Page Content                                   │
│ drag로   │  (max-width 1440, center)                       │
│ 200~480) │                                                 │
│          │                                                 │
│ - 검색   │                                                 │
│ - vault  │                                                 │
│ - 트리   │                                                 │
│ - raw    │                                                 │
│ - stats  │                                                 │
└──────────┴─────────────────────────────────────────────────┘
```

**각 zone의 역할 (관건)**:
- **헤더 = 유틸리티 상태** (brand / theme). role: "현재 무엇이 켜져있는가"
- **탭 레일 = 앱 섹션 전환** (8개). role: "어디로 갈 것인가"
- **사이드바 = vault explorer** (검색/트리/raw). role: "무엇을 볼 것인가"

이 3축은 Obsidian/Bear/Craft의 PKM 표면 정통 패턴이며, Linear/Vercel식 "운영 콘솔" 패턴과 구분된다.

## Alternatives Considered

### A. 유틸리티 헤더 + 별도 탭 레일 (Codex 권장, 채택)

- 헤더: brand + theme만
- 탭 레일: 헤더 아래 1줄 좌정렬 가로 탭, 가로 스크롤
- 사이드바: explorer 역할 복귀
- **장점**: 3단 정보위계 명확, 가운데 빈 공간 ❌, 8개 nav 헤더에서 부담 ❌
- **단점**: 2줄 구조 (사이드 패널 96px 차지), 좁은 화면 가로 스크롤
- **합격**: PKM 정체성 + Obsidian/Bear 정통 패턴 부합

### B. 통합 사이드바 재정렬 (Claude 권장)

- 헤더: brand만
- 사이드바 1개에 nav 8개 + 트리 + 검색
- **장점**: surgical 변경 (Sidebar.tsx만), 신규 컴포넌트 ❌
- **단점**: "사이드바에 nav 8개 우겨넣기"가 user가 이미 거부한 패턴
- **탈락**: user feedback 직접 위반

### C. 커맨드 바 헤더 + 사이드바 (3rd party)

- 헤더: brand + command palette
- **장점**: 빠른 탐색, 액션 중심
- **단점**: "운영 콘솔" 느낌, PKM 정체성 부합도 낮음
- **탈락**: 제품 정체성 mismatch

## Consequences

### Positive

- 정보위계 명확 (utility / section / explorer 3축)
- "가운데 빈 헤더" 구조적 해결 (탭 레일이 1줄 채움)
- "사이드바 nav 우겨넣기" 구조적 해결 (탭 레일로 분리)
- 검색·테마·사이드바 위치 일관 (관심사 분리)
- 데스크탑 사이드바 상시 노출 → 트리 탐색 안정성 ↑ (이전엔 모바일/데스크탑 동일하게 off-canvas drawer였음)
- 사이드바 resize (200~480px) → 사용자별 선호 폭 영속화

### Negative

- 상단 chrome 52+44 = 96px 차지 (이전 56px → +40px). 모바일은 부채꼴 압박 적음
- 8개 nav 좁은 화면에서 가로 스크롤 affordance 필요 (responsive 처리 완료)
- 사이드바 상시 노출 → 작은 노트북에서 가로 1024~1100px 구간은 답답할 수 있음
  - 단, drawer 모드 fallback은 유지 (≤744px)

### Trade-offs Accepted

- 사이드바 nav 8개 부담은 헤더/탭 레일 어느 쪽에 두든 동일 → 본 결정은 "탭 레일로" 정한 것뿐, 근본 해결 ❌
- 2차 패치 후보: nav 8개 중 사용 빈도 낮은 항목 (관리/정원) 사이드바 하단 secondary group 분리 → 사용 로그 없이 추측성 결정이므로 보류

## Compliance & Constraints

### §13 (Raven 컴포넌트/토큰 원칙)

- **§13.1 재사용 컴포넌트**: SearchBar variant prop (header/sidebar), GLOBAL_NAV 정의 1곳 (Layout.tsx)
- **§13.2 색/폰트 토큰화**: .section-nav-tab, .app-header-theme-btn CSS 변수 위임
- **인라인 style**: 구조적 다양성 팔레트 외에는 inline 금지 준수

### NOT breaking constraints

- 5번째 진입점 추가 ❌ (없음)
- SOUL.md 수정 ❌ (없음)
- 사용자 vault 데이터 write ❌ (없음)
- Lite bootstrap 2종+log.md (에이전트 표면) 위반 ❌ (없음)

## Implementation Summary

| commit | step |
|---|---|
| `e34cccd` | 1차: 헤더 그룹화 + 검색 사이드바 통합 |
| `3488835` | 97.1: 3-zone 헤더 (가운데 비는 문제) |
| `5b7c957` | 97.2: 헤더 슬림화 + nav 사이드바 통합 (우겨넣기 문제) |
| `8bb6df9` | 97.3: **3단 분리 (Codex 안 1)** — 본 ADR 결정 |
| `18450bc` | 97.4: 사이드바 resize 핸들 |
| `4575a9c` | 97.4.1: drag 중 React re-render 우회 (ref 기반) |
| `1ce8b20` | 97.4.2: drag 중 transition/layout containment 차단 |

3-party 검토: Codex (Codex CLI, 채택) / Claude (Claude Code, 대안 제시 후 사용자 거부로 탈락) / Antigravity (timeout, 무효).

## Verification

- tsc -b exit 0
- vite build exit 0 (994 modules, ~1.9s)
- 7 commit 모두 사용자 명시 승인 후 진행 (묵시적 commit ❌)
- Folder-hover-menu 테스트 회귀 1건 별도 hotfix (v0.6.22부터 잠재, 본 사이클과 무관)

## Related

- `_meta/plans/2026-07-07_220000-header-restructure-v0-7-97.md` (초기 plan)
- `_meta/changelog-v0.7.97.md` (회고)
- 메모리 §Raven v0.7.96 + P55-6 (묶음 종착 후 = 사용자 명시 요청 시 새 사이클)

## Lessons

1. **3-party 검토는 가치가 있으나 시간 비용 큼** — Codex/Claude 의견 갈릴 때 ADR로 명시적 결정 + 이유 기록이 안전
2. **사용자 거부 패턴이 결정의 정합성 가드** — "가운데 빈 ❌", "우겨넣기 ❌" 두 번의 거부가 3안 후보군을 좁힘
3. **PKM 정체성 부합도가 패턴 선택의 1차 기준** — Linear/Vercel식 아름다움보다 Obsidian/Bear식 정보위계 우선
4. **surgical 변경은 좋되 방향이 명확할 때 한 번에** — 3번 뒤집기보다 1번 합의 후 가는 게 총 비용 ↓