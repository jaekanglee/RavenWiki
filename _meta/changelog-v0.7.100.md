# Changelog v0.7.100 — PROJECT-WORKFLOW.md SOT 평가 패치 + lint #15 신설

> **BLUF**: 3-party cross-verification (Antigravity/Codex/Claude) + 사용자 관찰 3건 (날짜 title / 한글 매칭 / 사이클 코드) → P1 8건 + P2 1건 정합 패치 + **lint #15 신설 (data-contract ADR 동반)**. SCHEMA.md L81-85 강화 (title 1:1 매칭 + 언어 보존 + 의미 슬러그 3원칙). 다음 사이클 2번 (별도) = 기존 파일 audit + wiki_rename 일괄.

이전 changelog: `_meta/changelog-v0.7.99.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | PROJECT-WORKFLOW.md SOT 평가 패치 + ADR-2026-07-08 (lint #15) |
| 범위 | v0.7.100 (단일 묶음, 1 commit) |
| 기간 | 2026-07-08 |
| 커밋 수 | 1 |
| 시작 트리거 | 3-party cross-verification 평가 + 사용자 관찰 (title 날짜 / 한글 / 사이클 코드) |
| 종료 트리거 | pytest 32/33 pass (mcp SDK 환경 이슈 1건은 무관), 1-cycle audit 완료 |
| 정책 변경 | 1 (lint #15 = data-contract) |
| ADR 동반 | 1 (`adr-2026-07-08-slug-title-1to1-lint-15.md`) |

## §1 — 무엇을 만들었나 (what)

### 1.1 PWW §1 MCP 도구 표 정합 (P1-1, P1-2, P1-3, P1-4, P1-6, P1-7)

3-party cross-verification 평가 결과 — **SOT 자기모순 + 코드 정합 깨짐** 6건 일괄 정정:

| # | 위치 | 변경 |
|---|---|---|
| P1-1 | PWW L94/L96/L100 | "도구 10종" → **"13종"** (실제 read 8 + write 3 + admin 2) |
| P1-2 | PWW L180 | "read 6종" → **"8종"** (wiki_get_guide + wiki_get_guide_diff 추가) |
| P1-3 | PWW L110/L111/L120 | `frontmatter?` → **`frontmatter_data?`** (write.py L323 시그니처 정합) |
| P1-4 | PWW L112 | "`_archive/` 격리" → **`archive/<YYYY-MM-DD>/<slug>.md` 격리** (stale.py L323 실제 경로 정합) |
| P1-6 | PWW L108 | `wiki_get_guide` 설명에서 *"내 vault 지침이 왜 mismatch?"* 문구 제거 (해당 기능은 L109 `wiki_get_guide_diff`로 이동) |
| P1-7 | PWW L108 표 | `wiki_rename` 행에 *(lint #15 자동 수리)* 표시 추가 |

### 1.2 PWW §7.5 advisory lock 명시 (P1-8)

PWW L321 *"락 획득 상태/에러 반환을 확인하고, 실패 시 백오프 후 재시도"* → **advisory** 정보로 명확화:
- `wiki_update` 응답의 `_lock_holder` 필드는 **advisory** — write는 락과 무관하게 진행
- 동시성 보호 ❌, **충돌 감지/감사 목적**만
- AGENTS.md §3 "멀티 에이전트 write = experimental" cross-ref
- idempotency_key로 네트워크 재시도만 보장

### 1.3 PWW §6.2 RAG 4원칙 AGENTS.md §15.2 정합 (P1-5)

PWW L284-288 vs AGENTS.md L373-376. *"Root-Cause Investigation (컴파일 전 원인 조사)"* → **"Root-Cause Investigation prior to Compiling (지식 컴파일 전 원인 조사)"** (AGENTS.md 정합).

### 1.4 PWW §6.5 큐레이션 #15 항목 추가 (사용자 관찰 #1)

PWW L290-308 큐레이션 8단계 → **9단계**로 확장. 8번: **#15 slug-title 불일치 → `wiki_rename(new_slug)` 자동 수리**. 단 vault 운영자 명시 결정 (에이전트 자율 일괄 ❌, north star "원문 보존" 위배 회피).

### 1.5 PWW §6.1 wiki_lint 후킹 모호 정정 (P2-2)

L276 *"모든 쓰기 완료 후 `wiki_lint`를 실행"* → **"별도로 `wiki_lint()` 도구를 호출"** (write.py는 wiki_lint 자동 호출 안 함, 독립 도구).

### 1.6 SCHEMA.md L81-85 강화 — title 1:1 매칭 (사용자 관찰 #2, #3)

3원칙 명시:
1. **title 1:1 매칭 (필수, ADR-2026-07-08 lint #15)** — title 슬러그화 = 파일명
2. **언어 보존 (필수)** — title의 언어 = 파일명의 언어
3. **의미 있는 슬러그 (필수)** — 약어/시스템 코드만으로 구성된 slug 지양

journal/ADR 컨벤션 예외:
- `journal/{title-slug}.md` — 사건일은 frontmatter `event_date: YYYY-MM-DD` (선택)
- `decision/adr-YYYY-MM-DD-{title-slug}.md` — 결정일은 slug에 박되 `created`와 정합

**codebase `_meta/SCHEMA.md` (Tier 1 SOT) + vault `templates/agent/SCHEMA.md` (Lite bootstrap) 양쪽 정합 패치**.

### 1.7 lint #15 신설 (ADR-2026-07-08)

| 항목 | 값 |
|---|---|
| 번호 | #15 |
| 이름 | `slug-title 1:1 매칭` |
| 심각도 | 🟡 warning (자동 일괄 수정 ❌) |
| 규칙 | frontmatter `title` 슬러그화 결과 ≠ 파일명 |
| 제외 | `_meta/`, `raw/`, `content/_index/`, `content/index.md`, `decision/adr-*` |
| action | `wiki_rename` 자동 수리. `aliases`에 옛 slug 보존 가능 |

**codebase `_meta/SCHEMA.md` + vault `templates/agent/SCHEMA.md` 양쪽 lint 표에 추가**.

## §2 — 무엇을 하지 않았나 (의도적 scope-out)

- ❌ **기존 raven-dev vault 파일 일괄 rename** — 다음 사이클 2번 (별도, 운영자 명시 결정)
- ❌ **lint #15 실제 구현** (코드) — 본 사이클은 **SOT 정합 패치 + lint 정의** only. 구현은 다음 사이클 3번 (별도, `raven/core/lint.py` LintCheck 추가)
- ❌ **다른 vault audit** (babymoa, harumoa, hermes-infra, homelab) — 다음 사이클
- ❌ **`_archive/` vs `archive/` 실제 코드 통일** — PWW L112만 정합 (stale.py L323은 `archive/` 사용, 구현 정합). stale.py 자체 수정은 별도 사이클
- ❌ **`event_date` field lint 추가** — 선택 필드, lint 미검증 (over-spec 회피)
- ❌ **다이어트 6건 (이전 평가 §1.4 포트 매트릭스 등)** — 본 사이클은 정합 패치 우선, 다이어트는 다음 사이클

## §3 — 검증

| 항목 | 결과 |
|---|---|
| `pytest tests/test_v0_7_1_lite_bootstrap_surface.py tests/test_tier_boundary.py tests/test_v0_7_89_guide_endpoint.py` | **32/33 pass** (mcp.server 모듈 부재 1건은 본 패치와 무관) |
| `pytest tests/test_v0_7_91_mcp_wiki_get_guide.py` | fail (mcp SDK 환경 이슈) — 본 패치 전에도 동일 |
| SHA256 변경 확인 | SCHEMA.md/PROJECT-WORKFLOW.md/README.md 정상 hash |
| byte-identical 회귀 | `verify.py` 통과 (테스트 자동 검증) |
| Lite bootstrap surface 가드 | 통과 (PWW 표 13개 정합) |
| Tier boundary 가드 | 통과 |

## §4 — 회고 (lessons)

1. **3-party cross-verification 가치** — Codex/Antigravity의 P0 "dead ref" 의심이 모두 **잘못** (orchestrator 사전 검증으로 정정). 반면 3-party 합의의 P1 (frontmatter_data, 10→13종, get_guide_diff 오귀속)은 **모두 정확**. **3-party는 P0 single-source보다 안정적**.
2. **사용자 관찰 = 진짜 P0** — 3-party 평가에서 못 잡은 **slug 컨벤션 부재** + **journal/ADR 명시 없음**을 사용자가 정확히 짚어줌. **3-party 평가 후 사용자 검증**이 효과적.
3. **lint 신설 = data-contract = ADR 필수** — 사용자 원칙 ("policy/permission/data-contract = ADR") 정확히 적용. ADR 본문도 사용자 관찰을 인용하여 동기화.
4. **신규 lint는 자동 일괄 ❌** — north star "원문 보존" 위배 회피. 운영자 명시 결정 시만 일괄 (`wiki_rename`). 큐레이션 §6.5에 통합으로 발견→신호 흐름 자연.
5. **vault + codebase SOT 양쪽 패치** — Tier 1 (`_meta/SCHEMA.md`) + Tier 2 (`templates/agent/SCHEMA.md`) 동기화. verify.py SHA256로 자동 검증.

## §5 — 알려진 회귀 / 후속 작업

| 항목 | 우선순위 | 비고 |
|---|---|---|
| 기존 raven-dev 파일 audit + `wiki_rename` 일괄 | 다음 사이클 2번 (별도) | 운영자 명시 결정 시 진행. 위반 사례: `port-matrix-local-dev.md` (title=한글, slug=영문) 등 4+ 파일 |
| lint #15 실제 구현 (`raven/core/lint.py` LintCheck 추가) | 다음 사이클 3번 (별도) | 본 사이클은 lint 정의만 |
| 다른 vault audit (babymoa, harumoa, hermes-infra, homelab) | 다음 사이클 | harumoa `journal/2026-07-02-p1-2-cycle-complete.md` 명백한 위반 (slug에 `p1-2` 약어) |
| `stale.py` L323 `_archive/` vs `archive/` 실제 코드 통일 | 별도 hotfix | 본 사이클은 SOT만 정합. stale.py는 `archive/` 사용. Raven 제품이 어느 쪽 채택할지 결정 필요 |
| 다이어트 6건 (PWW §1.4 포트 매트릭스, §0.5 중복 등) | 별도 사이클 | 이전 평가 §4 |
| `docs/vault-patterns.md` Tier 1 leak (PWW L361) | 별도 hotfix | 1-round 평가 P1-3. SOT 정합 패치 미포함 |

## §6 — 다음 사이클

본 묶음 = PWW SOT 정합 패치 종착. 다음 사이클은 사용자 명시 요청 시에만 시작 (P55-6).

가능한 후보:
- **다음 사이클 2번**: raven-dev 기존 파일 audit + `wiki_rename` 일괄 (lint #15 기반)
- 다음 사이클 3번: lint #15 실제 코드 구현 (`raven/core/lint.py`)
- 다음 사이클 4번: 다른 vault audit (babymoa, harumoa, hermes-infra, homelab)
- 다음 사이클 5번: `matchMedia` jsdom stub + Folder-hover-menu 회귀 hotfix (v0.7.97 §6 잔여)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
