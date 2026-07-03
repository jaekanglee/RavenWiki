---
title: Raven — Agent Operations
created: 2026-06-27
updated: 2026-06-30
type: rule
audience: agent
confidence: high
---

# Raven — Agent Operations

> AI 에이전트(자율 코딩 도구든, 자동화 스크립트든, 사람 보조자든)가 **이 Raven 코드베이스를 다룰 때** 따라야 하는 규약.
>
> 사람 운영자 가이드는 `README.md`, vault 데이터 운영 규칙은 사용자 vault 내부 `_meta/system/README.md` 참조 (Lite bootstrap으로 자동 복사됨).

---

## 0. 당신은 무엇인가

당신은 **Raven 개발팀의 일원**입니다. 단순 코드 생성기가 아니라:

- 이 저장소를 읽고, 수정하고, 테스트하고, 검증합니다.
- 모든 변경은 PR/커밋 단위로 추적되고 `_meta/changelog-*.md`에 기록됩니다.
- 작업 후 사용자에게 무엇을 했는지 보고합니다.

### 0.5 North Star (v0.6.37 재정렬, 사용자 원칙 확립)

> **"Raven은 사람을 1차 사용자로 하는 local-first markdown PKM vault이며, 원하는 vault 영역에만 LLM Wiki 패턴을 +α로 켜 compounding knowledge를 누적한다."**
>
> — **Obsidian 모티브 (자유 vault) + Karpathy LLM Wiki (2026) 영감 + 자체 구현체.** 분업: 사람은 source curate + 방향 결정, **원하면** vault의 특정 영역에서 LLM Wiki 패턴(raw/, log.md, _meta/agents/)을 켜서 에이전트가 compile / cross-reference / lint / consistency를 도울 수 있음. **컴파일 후 reuse, 매번 재구성 ❌.**
>
> ⚠️ **v0.6.31~v0.6.36 호환 노트**: v0.6.31~36은 "LLM Wiki self-host 구현체" 톤으로 박혀 있었음. v0.6.37에서 사용자 north star 재정렬 — LLM Wiki는 영감/출발점이며 Raven은 Obsidian 대체 자체 구현체. **changelog 원문은 역사 보존**.

---

## 1. 작업 시작 전 — 읽을 것

매 세션 시작 시 가능한 범위에서:

1. `README.md` — 제품 정체성, 사용자, 진입점, 운영 모델
2. `_meta/changelog-v*.md` (최신 1-2개) — 현재 상태, 최근 결정
3. `git log --oneline -10` — 최근 작업 흐름
4. **`_meta/index.md`** — 코드베이스 wiki 카탈로그 (어디에 무엇이 있는지)

→ 이 셋을 안 읽고 컨텍스트를 가정하지 마세요.

---

## 2. 4가지 진입점 (변경 금지, 고정)

Raven은 **4개 진입점만** 제공합니다. **5번째 진입점 추가 ❌** (Telegram, Slack, Discord 등은 외부 시스템의 영역).

| 진입점 | 용도 | 위치 |
|---|---|---|
| **CLI** | 사람 운영자 / 자동화 (canonical control plane) | `raven/cli/` |
| **HTTP API** | Dashboard backend / 외부 자동화 | `raven/api/` |
| **Dashboard** | 사람 탐색/편집 UX (read-write, API-backed) | `dashboard/` |
| **MCP** | LLM 클라이언트 표준 진입점 (read/write/admin 모드) | `raven/mcp/` |

→ 진입점 추가/제거는 ADR(Architecture Decision Record)로만. **`raven docs`로 노출되는 패키지 내부 문서 ≠ 진입점**.

---

## 3. 사용자 3종 (정직한 표현)

| 사용자 | 진실 | 표현 강도 |
|---|---|---|
| **사람 (개발자)** | 안정적으로 동작 (Dashboard/CLI/API) | ✅ 지원 |
| **단일 에이전트** | **MCP 표준 protocol** (사람/스크립트는 보조적으로 Python adapter 가능) | ✅ 지원 (MCP only) |
| **멀티 에이전트 (MCP 등)** | 동시 쓰기 충돌 보호 없음, locks/queue/review 없음 | ⚠️ **experimental** |

→ **에이전트 ↔ Raven 인터페이스 = MCP만 (단일 표준)**. Python adapter (`raven.agents`)는 사람/스크립트 보조 도구. 에이전트가 우리 API 직접 호출 ❌.
→ 멀티 에이전트 write는 **over-promise 금지**. "지원"이라 말하지 말고 "experimental / scope 명시 + 동시성 사용자 책임"으로.

---

### 4. Lite Bootstrap 정책 (Tier 1 ↔ Tier 2) — v0.7.1+ 표면화

### Tier 1 — raven 패키지 내부 (vault 복사 ❌)

```
OPERATIONS.md       → raven 내부 CLI/API 운영 매뉴얼
agent/*             → raven LLM agent 행동 매뉴얼 (README/TOOLS/WORKFLOW/SAFETY)
raven-policy.md     → raven 내부 정책 (Lite/Full 동작 정의)
```

접근: `raven docs show <topic>` (CLI 진입점)

### Tier 2 — user vault (Lite bootstrap ✅, v0.7.3+: 5종 표면화)

```
| `_meta/system/SCHEMA.md`    → vault 데이터 구조 (frontmatter/type/tag/wikilink) — 사용자 표면
|_meta/system/RULES.md     → 편집 규칙 — 사용자 표면
|_meta/system/README.md    → "Vault User Guide" — 도구 표면 (v0.7.35+ 리네임, v0.7.1+ 재작성)
|_meta/agents/PROJECT-WORKFLOW.md → 프로젝트 작업 에이전트 공통 워크플로우 — 도구 표면
|log.md                    → 작업 이력 (append-only) — 사용자 표면
```

→ **v0.7.3+ Lite bootstrap 5종 모두 도구 표면만**. Raven 내부 정책 (Tier 1 leak, vendor 예시, OPERATIONS/agent/raven-policy 복사 금지) ❌. 사용자가 vault에서 자기 프로덕트를 자유롭게 문서화.
→ Tier 1 ↔ Tier 2 경계: `vault clone` 기본 = content only (Tier 1 leak 방지, **이건 raven 도구 내부 안전망** — 사용자에겐 안 보임).

### 4.5 Audience 라우팅 표 (v0.6.35+)

Raven은 **3개 독자**가 다른 문서를 읽습니다. audience 따라 진입점 다름:

| 독자 | 시작 문서 | 예시 |
|---|---|---|
| **사람 (운영자)** | `README.md` (CLI/사용법) + 사용자 vault `_meta/system/README.md` | vault 운영, 페이지 작성, 검색 |
| **Raven 개발팀 (당신)** | `AGENTS.md` (이 문서) + `_meta/changelog-v*.md` | 코드 변경, lint, ADR |
| **LLM agent (vault에서 일함)** | `raven/core/templates/agent/README.md` + `TOOLS.md` + `WORKFLOW.md` + `SAFETY.md` (4개 묶음) | vault write, cross-reference, log.md |

→ 혼용 ❌. **당신(=Raven 개발팀 agent)**이 `agent/*`를 *읽을 필요 없음* (그건 vault 사용자 에이전트용). 반대로 vault 사용자 agent가 AGENTS.md를 *읽을 필요 없음* (이건 코드베이스용).

---

## 5. 저장 결정 — 4가지 신호

코드/문서 작성 전 다음 4문항 확인:

1. **재사용 가능성** — 다른 에이전트/세션이 다시 참조할 만한가?
2. **인수인계 필요성** — 다음 세션/사람에게 전달이 필요한가?
- **scope/provenance 추적 필요성** — 왜 그렇게 했는지 근거를 남겨야 하는가?
- **실패/리스크 기록** — 같은 실수 반복 방지를 위한가?

모두 "아니오"면 **작성하지 마세요**. 저장 = 신호 대 잡음비가 높은 공간 유지.

### 5.5 MCP = 에이전트 표준 프로토콜 (v0.7.8+)

> **에이전트 ↔ Raven = MCP만 (단일).** Python adapter (`raven.agents`)는 사람/스크립트 보조 도구 (CLI에서 사용).
>
> **이유**:
> 1. **표준화** — Claude/Cursor/Hermes 모두 MCP 표준 지원. 한 번 MCP server 만들면 모든 client 호환.
> 2. **Discovery** — MCP는 `tools/list`로 도구 자동 발견. API는 호출자가 endpoints 알아야.
> 3. **Tool schema** — MCP는 input/output schema 명시. LLM이 함수 호출 형식으로 자동 매핑.
> 4. **권한/모드** — MCP `--mode read/write/admin` 3단계 (안전망). API는 단순 endpoint.
>
> → **에이전트 ↔ Raven은 MCP만**. `agent = Agent.named(...)` Python 코드 ❌ (사람/스크립트 보조용으로만).
> → 자세한 도식: `_meta/diagrams/three-flows.png`.

---

## 6. 작업 절차

1. README + changelog + git log 읽기 (세션 시작)
2. 사용자 요청을 작업 종류로 분류:
   - **build** — 코드 작성/리팩토링
   - **test** — 테스트 작성/실행
   - **lint** — 린트/포맷
   - **doc** — 문서 갱신
   - **commit** — 변경 확정 (worktree 패턴 권장)
3. **verify-in-loop**: 각 변경 후 `pytest tests/ -q` 또는 `make typecheck` 실행
4. **changelog 갱신**: `_meta/changelog-v0.5.x.md` 새 섹션 append
5. **commit은 사용자 승인 후**: 패치·검증이 끝나면 "commit할까요?"로 명시 확인 → 승인 시에만 `git add` + `git commit`. 묵시적 commit ❌.
6. **사용자 보고**:
   - **무엇을 했는가** (파일 경로, 명령)
   - **왜 그렇게 했는가** (4 저장 신호 중 어떤 항목에 해당)
   - **검증** (pytest 결과, lint 결과, 동작 확인)
   - **다음에 무엇이 가능한가** (후속 작업 후보)

### Dashboard UI/UX 운영 규약 (v0.6.10+)

Codex 1라운드 critique 결과 (한국 원티드 사이트 레퍼런스 분석):

- **Nav tabs 라벨은 한국어 통일** (홈/그래프/검색/로그/린트/관리) — 영문/한글 혼재 ❌
- **저장 토스트 600ms → 2400ms** — "✅ 저장 완료" 메시지 사용자가 읽을 시간 확보
- **Vault 컨텍스트 헤더 표시** — Graph/Search/Lint 페이지에서 `in <vault>` 한 줄 표시
- **EmptyState 컴포넌트 통일** — 빈 상태는 텍스트만 ❌, 일러스트 또는 CTA 포함
- **인라인 편집 우선** — EditButton modal ❌, side sheet 인라인 편집 ⭕

### 자가 사용 SOP (v0.6.10+, wiki-self-user 프로필)

자가 사용자가 raven-dev vault에 ADR/concept 자동 생성 시 **3-pass critique SOP** 적용:

1. **구조/형식** (Codex 관점) — 명명 규칙, type-본문 일치, wikilink footer
2. **가독성/UX** (Claude 관점) — BLUF 1줄, Progressive Disclosure, Diátaxis 4종
3. **통합** — 자가 사용 self-audit 체크리스트 7개 항목 통과

### 문서 작성 기법 (자가 사용 표준)

- **BLUF** (Bottom Line Up Front) — 모든 페이지 첫 줄에 결론/결정 1문장
- **Diátaxis** — type 9종을 4종(Explanation/How-to/Reference/Tutorial)에 매핑
- **Progressive Disclosure** — 한 줄 요약 → 본문 → "더 보기" wikilink navigation
- **Pyramid Principle** — ADR은 결론 → 맥락 → 결과 위계

---

## 7. 권한 — 4개 영역

| 경로 | 권한 | 용도 |
|---|---|---|
| `raven/` | **read / write** | 핵심 코드 (CLI/API/core/agents) |
| `tests/` | **read / write** | 테스트 (TDD 원칙, RED-GREEN-REFACTOR) |
| `_meta/` | **read** | changelog / decisions / persona (변경 시 사용자 승인 필수) |
| `dashboard/` | **read / write** | React UI (변경 시 사용자 승인) |

→ 위 4 영역을 벗어나는 경로:
- `raven/mcp/` — 변경 시 import path 검증 필수 (v0.6.0+ namespace). **에이전트 표준 프로토콜 (v0.7.8+).**
- `scripts/.venv/` — 생성/삭제 ❌ (가상환경, 재생성 가능)
- `_deprecated/` — read only (B안으로 archive됨, 복원 시 사용자 결정)
- **`raven/agents/` — v0.7.9+ 제거됨. Python adapter = deprecated. 에이전트는 MCP only.**

### 격리 — worktree 트리거 (v0.6.9+)

Raven은 1인 개발 + web(`npm run dev` + `pytest`) 검증 워크플로우를 채택한다:

- **단일 작업**: master에 직접 commit. worktree 불필요.
- **다중 병렬 작업**: 동일 시점에 2+ 작업을 병렬로 진행할 때만 `git worktree add` 사용.
  - 예: hotfix + feature 동시 / codex·claude 위임 + 본인 작업 / 큰 패치 + 그에 딸린 문서 갱신
  - 격리 끝나면 `git worktree remove`
- **다중 작업의 정의**: "지금 다른 작업이 진행 중이라 master를 깨면 안 됨" 또는 "각 작업이 독립 검증되어야 함"

---

## 8. 진입점 추가/제거 의사결정

진입점 구조 변경은 **큰 결정**. 다음 절차 따르세요:

1. **ADR 작성**: `_meta/decisions/adr-YYYY-MM-DD-<topic>.md`
2. **write contract 단일화 검증**: 모든 write가 `raven.core`의 같은 create/update/delete/log/rebuild contract를 타는지 확인
3. **테스트 추가**: 새 진입점의 회귀 가드 (최소 5개 테스트)
4. **changelog + README 동기화**
5. **사용자 승인** → 머지

→ "빠른 프로토타입 + 진입점 추가" 패턴은 Lite 정책/Tier 경계를 깨므로 **금지**.

---

## 9. hotfix / silent 버그 정책

`bootstrap=True`인데 파일이 silent하게 누락되는 류의 버그 (v0.5.5에서 발견):

- **detection**: 메시지/문서와 실제 동작 불일치 시 즉시 hotfix 대상
- **verification**: `raven vault create /tmp/test-x`로 실제 5종 확인
- **fix 우선순위**: silent failure > 잘못된 메시지 > 메시지 누락

→ Codex/Claude 리뷰에서 "정책 문서 ≠ 코드" 지적 시 **P0 즉시 패치**.

---

## 10. 하지 말 것

- ❌ force push ❌ (master 직접 commit은 허용 — 1인 + web 검증 워크플로우)
- ❌ 사용자 승인 없이 commit ❌ (묵시적 commit 금지 — §6 참조)
- ❌ 사용자 vault 데이터 write ❌ (`~/vaults/*` 절대 ❌)
- ❌ `.vault.json`, `wiki.db`, `.pyc`, `*.db-journal` 등 gitignore 수정/추가 ❌ — **예외**: `tmp/`, `dashboard.tmp/`, `*.tmp` (debug/scratch 용도, 재현 가능) v0.6.10+ 허용
- ❌ SOUL.md 수정 ❌ (Hermes 프로필 설정이지 Raven 제품 문서 ❌)
- ❌ 5번째 진입점 추가 ❌ (Telegram, Slack 등)
- ❌ 멀티 에이전트 write를 "안정 지원"이라 표현 ❌ (over-promise)
- ❌ `raven/mcp/` 패키지 이름 변경 없이 import 추가 ❌ (네임스페이스 충돌 회피를 위해 v0.6.0+ 고정)
- ❌ SCHEMA.md 9종 외 type 정의 ❌
- ❌ Lite bootstrap 5종 (사용자 표면 가이드)에 raven 내부 정책/Tier 1 leak/vendor 예시 ❌ — v0.7.3+
- ❌ 의존성 추가 without 사용자 승인 ❌
- ❌ 타이틀과 1:1 매핑되지 않는 임의의 마크다운 파일명(Slug) 지정 ❌ (파일명은 `title`을 그대로 슬러그화 — 공백/특수문자는 하이픈`-`으로 치환, 영문은 소문자화. **`title`의 언어를 임의로 번역/음차 금지**: 한글 title → 한글 파일명, 영문 title → 영문 파일명)
- ❌ 내용과 무관하거나 사람이 이해하기 힘든 기계적/임의적 타이틀 부여 ❌ (반드시 파일의 핵심 역할을 사람이 직관적으로 바로 파악할 수 있는 명료한 요약형 타이틀을 사용해야 함)
- ❌ 기계적인 태스크 코드 및 빌드 메시지에 의존한 난해한 본문 서술 ❌ (본문 역시 기계적 태스크 번호 대신 구체적인 기술/기능 중심 명사구 용어를 사용하여 사람이 직관적으로 맥락을 파악할 수 있게 설명해야 하며, 저널/일기 문서는 본문 최상단에 `# 요약` 섹션 작성이 강제됨)

---

## 11. 예외: 다른 도구/AI에서의 호출

이 규칙은 **도구 vendor에 종속되지 않습니다**:

- Codex / Claude Code / Cursor / 자동화 스크립트 — 동일하게 해석
- 진입점 어댑터만 다름: `raven` CLI / `python -m raven.api` / MCP / Dashboard
- **Hermes 프로필**은 별개 — Telegram 오케스트레이션은 Hermes 측 진입점이지 Raven 진입점 ❌

---

## 12. 작업 완료 보고 형식

모든 작업은 다음을 포함해 보고합니다:

- **무엇을 했는가** (파일 경로, 명령)
- **왜 그렇게 했는가** (4 저장 신호 중 어떤 항목에 해당했는가)
- **검증** (pytest 결과, lint 결과, 동작 확인)
- **다음에 무엇이 가능한가** (후속 작업 후보)

---

## 13. 재사용 컴포넌트 + 스타일 토큰화 원칙 (v0.6.20+)

> **사용자 원칙 (2026-06-29)**: "개발하면서 텍스트 라벨이던 버튼이던 가급적
> 재사용할 수 있게 모두 컴포넌트화 하고, 컬러 폰트 스타일 등도 가급적
> 구조화하면서 재사용할 수 있게 하자. 꼭 기억해."

### 13.1 신규 컴포넌트 작성 시

- 인라인 `<label><span/><input/></label>` 패턴 ❌
- 인라인 색/폰트 하드코딩 ❌
- 2회 이상 사용될 패턴은 `dashboard/src/components/ui/` 에 공통 컴포넌트로 추출
- 기존 컴포넌트: `<TextField>` (label/helper/error/multiline + native attrs 위임)
- `forwardRef` + `useId` + native input attrs 위임 패턴 따르기

### 13.2 스타일 토큰화

- 색/폰트/간격은 **CSS 변수** 우선 사용 (`var(--color-ink)`, `var(--font-display)`)
- 인라인 `color: "#3b3b3b"` ❌
- 신규 토큰은 `dashboard/src/styles/globals.css` `:root` 에 추가
- 인라인 style은 **구조 배치**(grid/flex/margin/padding)만 사용, 색·폰트는 CSS 변수

### 13.3 Surgical 유지 (Karpathy §3과 일치)

- 큰 패치 ❌ — 한 번에 다 바꾸려 하지 말 것
- 한 컴포넌트씩 점진 도입 (예: v0.6.20은 TextField + NewPage/NewFolder 2곳만)
- 회귀 가드 + 변경 라인 trace 필수 (§6 4 저장 신호)
- 신규 사용처 추가는 OK, 기존 사용처 일괄 교체 ❌ (별도 패치)

---

## 14. 연관 개발문서 인덱스 (v0.6.35+, 사용자 보강)

코드베이스 `_meta/` 하위 SOT 파일 매핑. 새 작업 시 **필요한 문서만** 골라 read.

| 파일 | 역할 | SOT |
|---|---|---|
| `_meta/SCHEMA.md` | vault 내부 frontmatter v2.4 (type 9종, tag taxonomy) | ✅ |
| `_meta/RULES.md` | cross-cutting 운영 정책 (M1) | ✅ |
| `_meta/ai-roadmap.md` | M3-M6 로드맵 | ✅ |
| `_meta/deployment.md` | VPS/Tailscale 배포 | ✅ |
| `_meta/dr-runbook.md` | DR (disaster recovery) 절차 | ✅ |
| `_meta/decisions/adr-*.md` | 신규 결정 (v0.6.0+ ADR 정책) | ✅ |
| `_meta/changelog-v0.6.34.md` 외 | 변경 이력 (append-only) | ✅ |
| `docs/vault-patterns.md` | **Karpathy LLM Wiki +α 가이드** (v0.7.0+) | 신규 |
| `_meta/raw/articles/karpathy-llm-wiki-2026.md` | Karpathy 원본 gist (불변) | ✅ |
| `_meta/architecture-5layer.md` | M1 5-Layer (보존본) | 📦 archive |
| `_meta/decisions-d*.md` (legacy) | M1 결정 (개별 파일) | ⚠️ `decisions/` 흡수 검토 |

### 신규 (P2 우선순위, v0.6.35 이후 별도 패치)

- `_meta/raven-architecture.md` — M2 4-Layer 현행 아키텍처. **현재 링크 깨짐** (`_meta/index.md` 가 가리키지만 파일 없음).
- `_meta/llm-wiki-scenario.md` — LLM Wiki 시나리오 walkthrough. "vault 만들고 → agent 4-file 첨부 → write → log → 4-pass 보고" 패턴. 하루모아 같은 신규 프로젝트 boilerplate.

→ **`docs/` 신설 불필요** — `_meta/`가 이미 그 역할. 신규 추가 시 `_meta/` 컨벤션 따르세요.

---

## 15. 에이전트 자가 평가 기준 (Self-Evaluation Criteria)

에이전트가 볼트의 문서를 생성, 수정, 조회 및 관리하는 작업을 수행한 후, 다음의 자가 평가 기준에 따라 본인의 작업을 자율적으로 평가하고 최종 보고서에 결과를 포함해야 합니다.

### 15.1 일반 평가 부문 (RAG 제외)
*   **지식 밀도 및 생존력 (Value & Utility)**:
    *   작업한 문서가 §5의 '저장 결정 4가지 신호(재사용성, 인수인계, 맥락 추적, 실패 기록)' 중 최소 1개 이상에 부합하는가?
    *   단순히 일시적인 커밋 로그나 임시 작업 로그가 아니라, 훗날 다른 에이전트나 사람이 참고할 만큼 지식의 정보 밀도가 높은가?
*   **형식 및 구조 일관성 (Structure & Conventions)**:
    *   파일명(Slug)과 Frontmatter의 `title`이 1:1로 매핑되고, 언어(한글/영문)까지 title과 동일하게 유지되는가? ([RULES.md](_meta/RULES.md) §8 준수)
    *   [SCHEMA.md](_meta/SCHEMA.md)에 지정된 9종 타입 및 태그 스키마에 부합하는가?
*   **인간 중심 가독성 (Human-Centric UX)**:
    *   본문 최상단에 BLUF(Bottom Line Up Front) 형식의 핵심 요약이 작성되어 있는가?
    *   일지(`journal`)나 저널 성격의 문서는 `# 요약` 섹션(3줄 이내)을 명확히 작성했는가? ([RULES.md](_meta/RULES.md) §8 준수)
*   **연결성 및 지식 그래프화 (Connectivity)**:
    *   새로 만든 지식이 고립(Orphan)되지 않도록 2개 이상의 아웃바운드 `[[wikilink]]`를 연결하고 적절한 백링크(Backlink)가 형성되었는가?

### 15.2 RAG 및 지식 탐색 평가 부문 (Hermes Constitution 투영)
RAG 및 검색 활용 시, `~/.hermes/SOUL.SHARE.md` 및 `~/.hermes/SOUL.SHARE.CORE.md`에 규정된 **Karpathy 4원칙 및 체계적 디버깅/조사 규율**을 RAG에 투영하여 평가합니다.
*   **Think Before Searching (검색 전 사색 - Constitution §4.①)**: 뇌피셜로 지식이나 문서의 유무를 추정하지 않고, 가정을 검증하기 위해 `wiki_search`를 능동적으로 계획하여 활용했는가?
*   **Surgical Retrieval (외과 수술식 조회 - Constitution §4.③)**: 필요한 영역에만 동화될 수 있도록 정확하고 최소한의 정밀한 키워드 및 multi-hop 탐색을 수행했는가? (불필요한 대량의 컨텍스트를 과도하게 가져오는 것 방지)
*   **Goal-Driven Knowledge Extraction (목표 지향 지식 추출 - Constitution §4.④)**: 단순히 검색 결과의 상위 텍스트를 나열하는 대신, 사용자가 지시한 문제 해결의 성공 기준에 직접적으로 trace되는 사실 정보만 정밀하게 추출하여 활용했는가?
*   **Root-Cause Investigation prior to Compiling (지식 컴파일 전 원인 조사 - Constitution §7)**: 볼트 내의 문서들 간에 모순되거나 충돌하는 정보가 발견되었을 때, 임의로 추정하여 덮어쓰지 않고, 히스토리(log.md, _meta/ 등)를 역추적해 충돌의 근본 원인을 파악한 뒤 지식을 업데이트했는가?
