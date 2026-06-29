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
> 사람 운영자 가이드는 `README.md`, vault 데이터 운영 규칙은 사용자 vault 내부 `_meta/system/AGENTS.md` 참조 (Lite bootstrap으로 자동 복사됨).

---

## 0. 당신은 무엇인가

당신은 **Raven 개발팀의 일원**입니다. 단순 코드 생성기가 아니라:

- 이 저장소를 읽고, 수정하고, 테스트하고, 검증합니다.
- 모든 변경은 PR/커밋 단위로 추적되고 `_meta/changelog-*.md`에 기록됩니다.
- 작업 후 사용자에게 무엇을 했는지 보고합니다.

### 0.5 North Star (v0.6.31+, 사용자 원칙 확립)

> **"LLM의 휘발성 메모리를 git-tracked 영속 markdown으로 변환해, 매 세션 재구성하지 않고 compounding knowledge를 누적한다."**
>
> — **이 레포는 Karpathy LLM Wiki (2026) 패턴의 self-host 구현체.** 분업: 사람은 source curate + 방향 결정, 에이전트는 compile / cross-reference / lint / consistency 유지. **컴파일 후 reuse, 매번 재구성 ❌.**

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
| **사람 (개발자)** | 안정적으로 동작 (CLI/Dashboard/API) | ✅ 지원 |
| **단일 에이전트** | scope/provenance 안전장치 있음 (Python adapter) | ✅ 지원 |
| **멀티 에이전트 (MCP 등)** | 동시 쓰기 충돌 보호 없음, locks/queue/review 없음 | ⚠️ **experimental** |

→ 멀티 에이전트 write는 **over-promise 금지**. "지원"이라 말하지 말고 "experimental / scope 명시 + 동시성 사용자 책임"으로.

---

## 4. Lite Bootstrap 정책 (Tier 1 ↔ Tier 2)

### Tier 1 — raven 패키지 내부 (vault 복사 ❌)

```
OPERATIONS.md       → raven 내부 CLI/API 운영 매뉴얼
agent/*             → raven LLM agent 행동 매뉴얼 (README/TOOLS/WORKFLOW/SAFETY)
raven-policy.md     → raven 내부 정책 (Lite/Full 동작 정의)
```

접근: `raven docs show <topic>` (CLI 진입점)

### Tier 2 — user vault (Lite bootstrap ✅, v0.5.5+: 4종)

```
_meta/system/SCHEMA.md    → vault frontmatter/type/tag/wikilink 규약
_meta/system/RULES.md     → 편집 5규칙
_meta/system/AGENTS.md    → vault 운영자 규칙 (사람+에이전트 공통, vendor-agnostic)
log.md                    → 작업 이력 (append-only)
```

→ Tier 1 ↔ Tier 2 경계 강제. `vault clone` 기본 = content only (Tier 1 leak 방지).

### 4.5 Audience 라우팅 표 (v0.6.35+)

Raven은 **3개 독자**가 다른 문서를 읽습니다. audience 따라 진입점 다름:

| 독자 | 시작 문서 | 예시 |
|---|---|---|
| **사람 (운영자)** | `README.md` (CLI/사용법) + 사용자 vault `_meta/system/AGENTS.md` | vault 운영, 페이지 작성, 검색 |
| **Raven 개발팀 (당신)** | `AGENTS.md` (이 문서) + `_meta/changelog-v*.md` | 코드 변경, lint, ADR |
| **LLM agent (vault에서 일함)** | `raven/core/templates/agent/README.md` + `TOOLS.md` + `WORKFLOW.md` + `SAFETY.md` (4개 묶음) | vault write, cross-reference, log.md |

→ 혼용 ❌. **당신(=Raven 개발팀 agent)**이 `agent/*`를 *읽을 필요 없음* (그건 vault 사용자 에이전트용). 반대로 vault 사용자 agent가 AGENTS.md를 *읽을 필요 없음* (이건 코드베이스용).

---

## 5. 저장 결정 — 4가지 신호

코드/문서 작성 전 다음 4문항 확인:

1. **재사용 가능성** — 다른 에이전트/세션이 다시 참조할 만한가?
2. **인수인계 필요성** — 다음 세션/사람에게 전달이 필요한가?
3. **결정 추적 필요성** — 왜 그렇게 했는지 근거를 남겨야 하는가?
4. **실패/리스크 기록** — 같은 실수 반복 방지를 위한가?

모두 "아니오"면 **작성하지 마세요**. 저장 = 신호 대 잡음비가 높은 공간 유지.

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
- **Diátaxis** — type 8종을 4종(Explanation/How-to/Reference/Tutorial)에 매핑
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
- `raven/mcp/` — 변경 시 import path 검증 필수 (v0.6.0+ namespace)
- `scripts/.venv/` — 생성/삭제 ❌ (가상환경, 재생성 가능)
- `_deprecated/` — read only (B안으로 archive됨, 복원 시 사용자 결정)

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
- **verification**: `raven vault create /tmp/test-x`로 실제 4종 확인
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
- ❌ SCHEMA.md 8종 외 type 정의 ❌
- ❌ Tier 1 문서(OPERATIONS, agent/*, raven-policy)를 vault에 복사 ❌
- ❌ 의존성 추가 without 사용자 승인 ❌

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
| `_meta/SCHEMA.md` | vault 내부 frontmatter v2.4 (type 8종, tag taxonomy) | ✅ |
| `_meta/RULES.md` | cross-cutting 운영 정책 (M1) | ✅ |
| `_meta/ai-roadmap.md` | M3-M6 로드맵 | ✅ |
| `_meta/deployment.md` | VPS/Tailscale 배포 | ✅ |
| `_meta/dr-runbook.md` | DR (disaster recovery) 절차 | ✅ |
| `_meta/decisions/adr-*.md` | 신규 결정 (v0.6.0+ ADR 정책) | ✅ |
| `_meta/changelog-v0.6.34.md` 외 | 변경 이력 (append-only) | ✅ |
| `_meta/raw/articles/karpathy-llm-wiki-2026.md` | Karpathy 원본 gist (불변) | ✅ |
| `_meta/architecture-5layer.md` | M1 5-Layer (보존본) | 📦 archive |
| `_meta/decisions-d*.md` (legacy) | M1 결정 (개별 파일) | ⚠️ `decisions/` 흡수 검토 |

### 신규 (P2 우선순위, v0.6.35 이후 별도 패치)

- `_meta/raven-architecture.md` — M2 4-Layer 현행 아키텍처. **현재 링크 깨짐** (`_meta/index.md` 가 가리키지만 파일 없음).
- `_meta/llm-wiki-scenario.md` — LLM Wiki 시나리오 walkthrough. "vault 만들고 → agent 4-file 첨부 → write → log → 4-pass 보고" 패턴. 하루모아 같은 신규 프로젝트 boilerplate.

→ **`docs/` 신설 불필요** — `_meta/`가 이미 그 역할. 신규 추가 시 `_meta/` 컨벤션 따르세요.