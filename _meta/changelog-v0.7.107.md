# Changelog v0.7.107 — Claude 평가 통합 (3-party 합의) + G5 audit log + C4 누적 가드 + lint #16/#17 정의

> **BLUF**: 2-party (Codex + Antigravity) 합의 시 빠뜨린 Claude 평가 통합 — G5 (content/ 외 영역 audit log) + C4 (4신호+orphan 누적 가드) 추가. SCHEMA.md lint 운영 표에 #16 (vault growth rate) + #17 (duplicate title candidate) 정의. PWW §6.5 C4 / §8.4 audit log 정책 보강. **Claude 결과 (`docs/evaluations/2026-07-08-agent-signal-evaluation.md`) 본 합의에 정직 통합**.

이전 changelog: `_meta/changelog-v0.7.106.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | 3-party 합의 (Codex + Antigravity + Claude) + G5 audit log + C4 누적 가드 + lint #16/#17 SOT 정의 |
| 범위 | v0.7.107 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | 사용자 명시 (Claude 평가 통합, 3-party 합의 충분성 확인) |
| 종료 트리거 | patch 6 file + pytest Lite bootstrap surface/Tier boundary pass |
| 정책 변경 | 0 (SOT 보강) |
| ADR 동반 | 0 (기존 ADR 인용) |

## §1 — 무엇을 했나 (what)

### 1.1 Claude 평가 결과 통합 (3-party 합의)

사용자 명시로 **2-party 합의에 빠진 Claude 평가 결과** 정직 통합:

- **Gap G5 (content/ 외 영역 변조 audit)** = Claude 고유 (2-party G1-G4와 별개). **3-party 합의에 추가** → PWW §8.4 audit log 정책 신설
- **Conflict C4 (lint #10 4신호 미달 + lint #4 orphan 7일 후 통과)** = Claude 고유. **3-party 합의에 추가** → PWW §6.5 #10+#4 누적 가드 3단계 (info → warning → stale)
- 나머지 Gap G1-G4, Conflict C1-C3 = 2-party와 동일 (v0.7.106에서 적용 완료)

### 1.2 PWW §6.5 #9 신규 — #10 + #4 누적 위험 (C4)

L313 다음에 1줄 추가:

> **#10 + #4 누적 위험 (C4)** — §3 4신호 미달로 작성된 페이지가 7일 유예 후 #4 통과로 누적될 수 있음. **90일+ 미갱신**이면 §1.1의 status 4종 머신으로 **`stale`** 자동 전이 (사람 review → `current` 복귀 가능). lint #10 (info) + lint #4 (warning) + lint #7 (stale) 3단계 누적 가드.

### 1.3 PWW §8.4 audit log 정책 신설 (G5)

L365 다음에 §8.4 신설:

> 에이전트가 다음 경로에 write 시도 시, **MCP/API는 `permission_denied`로 차단**하되, **시도 자체를 `log.md`에 audit 레코드로 기록** (north star "원문 보존" 직접 보호):
> - `raw/`, `_meta/system/`, `_meta/agents/` → `actor`, `attempted_path`, `result`, `reason`, `timestamp`
> - `log.md` 기존 줄 삭제/수정 → `actor`, `line_no`, `result`
> - **Why**: API/MCP 차단만으로는 "어떤 에이전트가 어떤 경로에 시도했는지" 파악 불가. audit log는 **시도 패턴 분석** + **반복 위반 감지** 기반.
> - **Lint #14 (tier integrity, critical)** + audit log = 1차 차단 + 2차 audit.

### 1.4 SCHEMA.md lint 운영 표 #16/#17 추가 (vault + codebase 양쪽)

**vault SCHEMA.md L248 부근**:
- 14 → 17개로 갱신
- **#16 vault growth rate anomaly** (🔵 info) — 7일 rolling page count 증가율 > 3σ (과거 30일 기준)
- **#17 duplicate title candidate** (🟡 warning) — title 유사도 > 0.8 페이지 2개+

**codebase `_meta/SCHEMA.md` L211 부근**:
- 14 → 17개로 갱신 + 동일 정의

### 1.5 AGENTS.md §10 audit log cross-ref

L262 다음에 1줄 추가:

> ❌ `_meta/system/` / `_meta/agents/` / `raw/` / `log.md` 변조 시도 ❌ — MCP/API는 `permission_denied`로 차단 + **시도 자체를 `log.md`에 audit 레코드** 기록 (PWW §8.4, v0.7.107+)

### 1.6 test_v0_7_1_lite_bootstrap_surface.py — SOT 보강 키워드 검증

`test_new_project_workflow_has_operating_facts`에 6개 키워드 추가:
- `Layer 2` (Layer 2 정체성)
- `사람 1차 운영 인덱스`
- `lint 자동 수리` (§3 면제)
- `wiki_archive` (§6.5 archive 권한)
- `type별 에이전트 write` (§7.1)
- `Audit log` + `permission_denied` (§8.4)

## §2 — 무엇을 하지 않았나 (의도적 scope-out)

- ❌ **lint #16/#17 실제 코드 구현** (`raven/core/lint.py` LintCheck 추가) — SOT 정의만, 구현은 다음 사이클 (사용자 명시 시)
- ❌ **audit log 실제 구현** (`wiki_update` permission_denied + log.md append 로직) — 정책 정의만
- ❌ **다른 vault audit** (babymoa, hermes-infra, homelab) — 다음 사이클
- ❌ **1.5배 soft limit override** (Conflict C5) — 1-party 권고, 2-party 미합의

## §3 — 검증

| 항목 | 결과 |
|---|---|
| PWW §6.5 #9 (#10+#4 누적 위험) 추가 | ✅ (L313) |
| PWW §8.4 audit log 정책 신설 | ✅ (L368-380) |
| SCHEMA.md lint #16/#17 (vault) | ✅ (L248-249) |
| SCHEMA.md lint #16/#17 (codebase) | ✅ (L229-230) |
| AGENTS.md §10 audit log cross-ref | ✅ (L263) |
| test_v0_7_1_lite_bootstrap_surface.py SOT 키워드 검증 | ✅ (L76-86) |
| pytest Lite bootstrap surface | (아래 검증) |
| pytest Tier boundary | (아래 검증) |

## §4 — 회고 (lessons)

1. **3-party 합의의 가치** — 2-party만으로 빠진 G5 (audit log) + C4 (4신호+orphan) = **Claude가 보완**. 2-party 합의는 **blind spot 가짐**. 3-party 합의로 정직 통합
2. **사용자 신호 (충분한가?)** — 사용자가 정직히 물어봄. **"G5 + C4만으로 충분?"** 답: **충분하지 않음** + 빠진 부분 정직 표기 (사용자 권한/에스컬레이션/백업/lifecycle). 본 사이클은 G5 + C4만 보강
3. **SOT 보강 vs 코드 구현** — 본 사이클은 **SOT 정의 + 정책 박기**만. 실제 audit log / lint #16/#17 코드 구현은 별도 사이클. 정직 분리
4. **"정직 보고" 약속 재지킴** — Claude 결과 별도 보존 후 사용자 명시로 본 합의 통합. 평가 party count 정직

## §5 — 알려진 회귀 / 후속 작업

| 항목 | 우선순위 | 비고 |
|---|---|---|
| lint #16/#17 코드 구현 (`raven/core/lint.py`) | 다음 사이클 (사용자 명시) | SOT 정의됨, 구현 미완 |
| audit log 정책 코드 구현 (MCP permission_denied + log.md append) | 다음 사이클 | SOT 정의됨 |
| 1.5배 soft limit override (Conflict C5) | 별도 | 1-party 권고, 2-party 미합의 |
| 다른 vault audit | 다음 사이클 | |
| 3-party 합의 시 빠진 부분 (사용자 권한, 백업, lifecycle) | 별도 | Claude 평가 + 2-party 합의가 모두 빠뜨림 |

## §6 — 다음 사이클

본 사이클 = 3-party 합의 통합 (G5 + C4 + lint #16/#17 SOT 정의) 종착. 다음 사이클은 사용자 명시 요청 시 (P55-6).

가능한 후보:
- 다음 사이클: lint #16/#17 코드 구현 + audit log 코드 구현
- 다음 사이클: 다른 vault audit
- 다음 사이클: 1.5배 soft limit override

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
