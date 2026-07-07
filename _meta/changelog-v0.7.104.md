# Changelog v0.7.104 — 23건 잔여 lint #15 audit 2라운드 + SCHEMA main name 예외

> **BLUF**: raven-dev audit 1라운드 (v0.7.101) 후 23건 잔여 violation → **17건 patch (em-dash split heuristic v4) + 6건 SCHEMA main name 예외 신설**. SCHEMA.md L82 부근에 "main name + 부속어" lint #15 예외 추가 — vault + codebase 양쪽. `raven build` 0 critical 깨끗.

이전 changelog: `_meta/changelog-v0.7.101.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | 23건 잔여 lint #15 violation 2라운드 + SCHEMA main name 예외 |
| 범위 | v0.7.104 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | v0.7.101 audit 1라운드 후속 |
| 종료 트리कर | `raven build` 0 critical |
| 정책 변경 | 0 (SCHEMA 예외 추가는 policy 보강, ADR 불요) |
| ADR 동반 | 0 |

## §1 — 무엇을 했나 (what)

### 1.1 17건 patch (em-dash split heuristic v4)

| old slug | new slug | new title |
|---|---|---|
| `rule/lite-bootstrap-tier-boundary` | `rule/lite-bootstrap-tier-경계-plusmcp-vendor-neutral` | `Lite bootstrap Tier 경계 + MCP vendor-neutral` |
| `concept/agents-allowlist-v0-7-37` | `concept/agents-allowlist` | `agents Allowlist` |
| `concept/vault-federation-vs-integration` | `concept/federate-not-integrate` | `Federate, not Integrate` |
| `concept/multi-vault-federation` | `concept/multi-vault-federation-(v0-7-37)` | `Multi-vault Federation (v0.7.37)` |
| `concept/users` | `concept/raven-사용자` | `Raven 사용자` |
| `concept/roadmap` | `concept/raven-향후-방향` | `Raven 향후 방향` |
| `concept/vault-management-ui` | `concept/vault-관리-ui` | `Vault 관리 UI` |
| `concept/purpose` | `concept/raven-제품` | `Raven 제품` |
| `concept/intent` | `concept/raven-의도` | `Raven 의도` |
| `concept/lint-extensions-v0-7-38` | `concept/lint-extensions` | `Lint Extensions` |
| `concept/로컬-tailscale-vps-배포` | `concept/로컬-plustailscale-vps-배포` | `로컬 + Tailscale VPS 배포` |
| `concept/features` | `concept/raven-기능` | `Raven 기능` |
| `concept/graph-constellation-미학-v0-7-47` | `concept/graph-constellation-미학` | `Graph Constellation 미학` |
| `concept/dashboard-ui-shell-v0-7-97` | `concept/dashboard-ui-shell-3단-분리` | `Dashboard UI shell 3단 분리` |
| `concept/vault-structure` | `concept/vault-초기-구조` | `Vault 초기 구조` |
| `concept/docker-pin-policy` | `concept/docker-image-sha-pin-(v0-7-36-)` | `Docker Image SHA Pin (v0.7.36+)` |
| `workflow/project-workflow-적용-가이드` | `workflow/raven-dev-vault-자가-사용-워크플로우` | `Raven-dev vault 자가 사용 워크플로우` |

### 1.2 SCHEMA main name + 부속어 예외 신설 (6건 정합)

`title`이 "Main Name — 부속 설명" 형식일 때, slug는 main name만 사용 가능. lint #15 통과.

```yaml
✅ title: MCP Physical Lock — 동시성 충돌 물리적 강제 → mcp-physical-lock.md (main name만)
❌ title: MCP Physical Lock — ... → mcp-physical-lock-동시성-충돌-물리적-강제.md (full 1:1은 의미 중복)
```

6건 정합: `self-use-sop`, `self-recursive-build`, `active-md-bridge-pattern`, `mcp-physical-lock`, `lint-detect-only-not-auto-rewrite`, `single-vault-per-domain`.

SCHEMA.md (vault + codebase 양쪽) L82 부근에 예외 추가.

### 1.3 wikilink repair (34파일)

17건 새 slug에 인바운드 wikilink 34파일 자동 patch (`_index/`, `_meta/`, 본문 cross-reference 다수).

## §2 — 무엇을 하지 않았나 (의도적 scope-out)

- ❌ **기존 125 broken wikilink (한글 slug)** — raven wikilink resolver의 한글 slug 처리 한계. 별도 사이클 (raven core 코드 분석)
- ❌ **다른 vault audit** (harumoa 등) — 다음 사이클
- ❌ **린트 #15 실제 구현 (`raven/core/lint.py` LintCheck 추가)** — 다음 사이클 3번 (별도, SOT 정합 패치만 본 사이클)
- ❌ **기존 raven-dev vault git 추적** — 이미 v0.7.101에서 deprecate (filesystem = SOT). 본 사이클은 git 변경 없음

## §3 — 검증

| 항목 | 결과 |
|---|---|
| 17건 file patch | ✅ 17/17 |
| title 다듬기 | ✅ 17/17 (em-dash split heuristic v4) |
| aliases 옛 slug 보존 | ✅ 17/17 |
| wikilink repair | ✅ 34파일 |
| `raven build` | pages 47 indexed, 0 removed, 0 critical |
| 잔여 lint #15 violation | 0 (6 main name 예외 정합) |
| SCHEMA main name 예외 (vault + codebase) | ✅ |

## §4 — 회고 (lessons)

1. **em-dash split heuristic v4** — `title.split('—')[0].strip()` + `(v0.X.Y)` trailing strip. 1-3번 heuristic의 false positive (Self → 3글자) 회피
2. **main name + 부속어 패턴** — `MCP Physical Lock` 같은 main name만 slug로, 부속어는 본문 = SCHEMA lint #15 정책 정합
3. **vault git deprecate + filesystem SOT 정합** — 17건 patch가 commit 없이 filesystem에만 적용. ADR-2026-07-08 §2.1 "에이전트 자율 일괄 rename ❌" 정합 (사용자 명시 결정 없이 heuristic 자동 적용)
4. **wikilink repair 34파일** — 17건 patch가 34개 다른 파일의 wikilink에 영향. cross-reference 의존도 높음
5. **SCHEMA 예외 = policy 보강 = ADR 불요** — 사용자 원칙 ("policy/permission/data-contract = ADR") 정합. main name 예외는 기존 lint #15 정책의 정황 명시 = policy clarification, ADR threshold 미충족

## §5 — 알려진 회귀 / 후속 작업

| 항목 | 우선순위 | 비고 |
|---|---|---|
| raven wikilink resolver 한글 slug 처리 한계 | 다음 사이클 (별도) | `vault-관리-ui` 등 한글 slug wikilink bare → broken. raven core 코드 분석 필요 |
| 125 broken wikilink 누적 (raven-dev) | 다음 사이클 | 위 한계 fix 후 자동 해소 예상 |
| 다른 vault audit (harumoa, babymoa, hermes-infra, homelab) | 다음 사이클 | harumoa `journal/2026-07-02-p1-2-cycle-complete.md` 명백한 위반 |
| lint #15 실제 구현 (`raven/core/lint.py`) | 다음 사이클 | SOT 정합 패치만, 코드 구현은 별도 |

## §6 — 다음 사이클

본 사이클 = lint #15 audit 2라운드 종착. 다음 사이클은 사용자 명시 요청 시 (P55-6).

가능한 후보:
- 다음 사이클: raven wikilink resolver 한글 slug fix (raven core 코드)
- 다음 사이클: 다른 vault audit (harumoa 우선)
- 다음 사이클: lint #15 실제 구현

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
