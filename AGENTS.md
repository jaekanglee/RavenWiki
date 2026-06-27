---
title: Raven — Agent Operations
created: 2026-06-27
updated: 2026-06-27
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

---

## 1. 작업 시작 전 — 읽을 것

매 세션 시작 시 가능한 범위에서:

1. `README.md` — 제품 정체성, 사용자, 진입점, 운영 모델
2. `_meta/changelog-v*.md` (최신 1-2개) — 현재 상태, 최근 결정
3. `git log --oneline -10` — 최근 작업 흐름

→ 이 셋을 안 읽고 컨텍스트를 가정하지 마세요.

---

## 2. 4가지 진입점 (변경 금지, 고정)

Raven은 **4개 진입점만** 제공합니다. **5번째 진입점 추가 ❌** (Telegram, Slack, Discord 등은 외부 시스템의 영역).

| 진입점 | 용도 | 위치 |
|---|---|---|
| **CLI** | 사람 운영자 / 자동화 (canonical control plane) | `raven/cli/` |
| **HTTP API** | Dashboard backend / 외부 자동화 | `raven/api/` |
| **Dashboard** | 사람 탐색/편집 UX (read-write, API-backed) | `dashboard/` |
| **MCP** | LLM 클라이언트 표준 진입점 (read/write/admin 모드) | `mcp/` |

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
5. **사용자 보고**:
   - **무엇을 했는가** (파일 경로, 명령)
   - **왜 그렇게 했는가** (4 저장 신호 중 무엇에 해당)
   - **다음에 무엇이 가능한가** (후속 후보)

---

## 7. 권한 — 4개 영역

| 경로 | 권한 | 용도 |
|---|---|---|
| `raven/` | **read / write** | 핵심 코드 (CLI/API/core/agents) |
| `tests/` | **read / write** | 테스트 (TDD 원칙, RED-GREEN-REFACTOR) |
| `_meta/` | **read** | changelog / decisions / persona (변경 시 사용자 승인 필수) |
| `dashboard/` | **read** | React UI (변경 시 worktree 패턴 + 사용자 승인) |

→ 위 4 영역을 벗어나는 경로:
- `mcp/` — 변경 시 import path 검증 필수 (네임스페이스 위험)
- `scripts/.venv/` — 생성/삭제 ❌ (가상환경, 재생성 가능)
- `_deprecated/` — read only (B안으로 archive됨, 복원 시 사용자 결정)

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

- ❌ 직접 `master`에 커밋/푸시 ❌ (worktree + PR 패턴)
- ❌ 사용자 vault 데이터 write ❌ (`~/vaults/*` 절대 ❌)
- ❌ `.vault.json`, `wiki.db`, `.pyc`, `*.db-journal` 등 gitignore 수정/추가 ❌
- ❌ SOUL.md 수정 ❌ (Hermes 프로필 설정이지 Raven 제품 문서 ❌)
- ❌ 5번째 진입점 추가 ❌ (Telegram, Slack 등)
- ❌ 멀티 에이전트 write를 "안정 지원"이라 표현 ❌ (over-promise)
- ❌ `mcp/` 패키지 이름 변경 없이 import 추가 ❌ (네임스페이스 충돌)
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