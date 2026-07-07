# Changelog v0.7.101 — raven-dev lint #15 audit 1라운드 (5건 patch)

> **BLUF**: 사용자 north star "원문 보존 + 증분 누적" + ADR-2026-07-08 §2.1 (*에이전트 자율 일괄 rename ❌*) 정합으로 **lint #15 audit 1라운드** 진행. 명백한 5건 (한글 title → 영문 slug, 한+영 혼재) **사용자 명시 결정 후 patch**: file rename + title 다듬기 + aliases 옛 slug 보존 + wikilink 9건 repair. 23건 잔여 violation은 다음 사이클 2번 audit 대상.

이전 changelog: `_meta/changelog-v0.7.100.md` (다음 사이클 2번 = 본 사이클)

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | raven-dev vault lint #15 audit 1라운드 |
| 범위 | v0.7.101 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | v0.7.100 사용자 명시 (*"ㄱㄱ"*) |
| 종료 트리거 | 5건 patch 완료 + `raven build` 검증 (새 broken 0) |
| 정책 변경 | 0 (ADR-2026-07-08 §2.1 운영) |
| ADR 동반 | 0 |

## §1 — 무엇을 했나 (what)

### 1.1 lint #15 audit (초기 41건 → 5건 선정 → 0건 본 사이클, 23건 잔여)

**초기 audit 결과** (System Areas + ADR 컨벤션 제외): **41건** 1:1 매칭 위반. 본 사이클은 **사용자 명시 가장 시급 5건**만 patch:

| # | old slug | new slug | new title |
|---|---|---|---|
| 1 | `rule/port-matrix-local-dev` | `rule/로컬-개발-포트-매트릭스` | `로컬 개발 포트 매트릭스` |
| 2 | `concept/deployment-local-and-tailscale` | `concept/로컬-tailscale-vps-배포` | `로컬 + Tailscale VPS 배포` |
| 3 | `concept/graph-constellation-aesthetic` | `concept/graph-constellation-미학-v0-7-47` | `Graph Constellation 미학 (v0.7.47)` |
| 4 | `concept/agents-allowlist` | `concept/agents-allowlist-v0-7-37` | `agents Allowlist (v0.7.37)` |
| 5 | `concept/lint-extensions-v0.7.38` | `concept/lint-extensions-v0-7-38` | `Lint Extensions (v0.7.38)` |

### 1.2 wikilink repair (9건)

5개 새 slug에 인바운드 wikilink 9건 자동 patch:
- `concept/agents-allowlist-v0-7-37` ← 4건 (`self-use-sop`, `self-recursive-build`, `multi-vault-federation`, `_index/concept`)
- `concept/lint-extensions-v0-7-38` ← 5건 (`self-use-sop`, `self-recursive-build`, `docker-pin-policy`, `lint-detect-only-not-auto-rewrite`, `_index/concept`)
- `concept/로컬-tailscale-vps-배포` ← 1건 (`_index/rule`)
- `concept/graph-constellation-미학-v0-7-47` ← 1건 (`_index/concept`)
- `rule/로컬-개발-포트-매트릭스` ← 1건 (`_index/rule`)

`_index/concept.md` + `_index/rule.md`는 **System Areas** (SCHEMA L242-243) — `raven build`의 index builder만 갱신 가능 (직접 수정 ❌). **`raven build` 호출로 자동 재빌드**.

### 1.3 frontmatter 다듬기 + aliases 옛 slug 보존

5건 모두 `aliases: [<old_slug>]` 추가 — SCHEMA L74-75 + ADR-2026-07-08 §2.1 정합. 옛 slug로 인바운드 wikilink 도달 시 alias가 redirect 역할 (frontmatter alias resolution).

### 1.4 raven build 재호출

5건 patch 후 `~/.local/bin/raven build` 실행:
- `pages: 47 indexed, 0 removed` ✅
- 새 broken wikilink 0건 (본 사이클이 추가한 broken 없음)
- 기존 125 critical은 raven-dev 이전부터 있던 broken (multi-vault-federation, purpose, users 등) — **본 사이클과 무관, 별도 사이클 audit 대상**

## §2 — 무엇을 하지 않았나 (의도적 scope-out)

- ❌ **23건 잔여 violation 일괄 patch** — ADR-2026-07-08 §2.1 "에이전트 자율 일괄 rename ❌" 정합. 다음 사이클에서 사용자 명시 결정
- ❌ **기존 125 broken wikilink** — raven-dev 이전부터 누적, 본 사이클 scope 외
- ❌ **다른 vault audit** (babymoa, harumoa, hermes-infra, homelab) — 다음 사이클
- ❌ **`harumoa journal/2026-07-02-p1-2-cycle-complete.md` 같은 p1-2 약어 슬러그** — 다음 사이클

## §3 — 검증

| 항목 | 결과 |
|---|---|
| 5건 file rename | ✅ 5/5 (os.rename 사용, git mv 미사용 — 일부 untracked 파일 대응) |
| title 1:1 매칭 | ✅ 5/5 (lint #15 pass) |
| aliases 옛 slug 보존 | ✅ 5/5 |
| wikilink repair | ✅ 9/9 (8 inbound + 1 self-resolved) |
| `raven build` | pages 47 indexed, 0 removed |
| 새 broken wikilink | 0건 |
| 5건 alias resolution | ✅ 옛 slug로 도달 시 새 slug로 resolve (frontmatter alias) |

## §4 — 회고 (lessons)

1. **`git mv`는 untracked 파일에 동작 안 함** — raven-dev는 일부 파일만 git 추적. `os.rename` (plain file rename)이 안전. git 추적 여부와 무관
2. **frontmatter regex 단순화** — `re.DOTALL|MULTILINE` non-greedy + `^---$` anchor이 가장 robust. 첫 fix의 regex가 non-greedy 매치를 잘못 잡아 frontmatter 밖으로 aliases를 박았음
3. **복구 fallback** — git 추적 3건은 `git show HEAD:path`로 원본 복구. untracked 2건은 현재 파일에서 body 추출
4. **사용자 명시 결정 = ADR §2.1 정합** — "에이전트 자율 일괄 ❌" 정황. 41건 중 5건만 사용자 명시 → 본 사이클 scope 명확
5. **`_index/` System Area는 `raven build`로 자동 갱신** — 직접 patch ❌ (PWW L324 명시). wikilink repair 후 build 호출로 일괄 갱신
6. **lint #15 첫 운영** — 실제 발견 41건, 5건 patch로 `lint #15` 정의가 **실질적 신호**임을 검증. 23건 잔여는 audit backlog로 다음 사이클

## §5 — 알려진 회귀 / 후속 작업

| 항목 | 우선순위 | 비고 |
|---|---|---|
| 23건 잔여 lint #15 violation (concept/* 17 + decision/* 2 + rule/* 1 + workflow/* 1 + 2 misc) | 다음 사이클 2번 (별도) | 사용자 명시 결정 시 patch |
| 125 critical broken wikilink (raven-dev 누적) | 별도 사이클 | `_index/` 자동 갱신 의존 — 직접 wikilink repair 또는 page 생성 |
| 다른 vault audit (babymoa, harumoa, hermes-infra, homelab) | 다음 사이클 | harumoa `journal/2026-07-02-p1-2-cycle-complete.md` 명백한 위반 |
| `multi-vault-federation`, `lint-detect-only-not-auto-rewrite`, `single-vault-per-domain` 등 decision/ 페이지 (ADR 컨벤션 아님) | 별도 사이클 | 2건: lint-detect-only, single-vault-per-domain |

## §6 — 다음 사이클

본 사이클 = lint #15 audit 1라운드 종착. 다음 사이클은 사용자 명시 요청 시 (P55-6).

가능한 후보:
- 다음 사이클 2번: 23건 잔여 violation patch
- 다음 사이클 3번: 다른 vault audit (harumoa 우선 — 가장 명확한 p1-2 약어 위반)
- 다음 사이클 4번: 125 broken wikilink 일괄 repair (사용자 큐레이션 §6.5 #1)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
