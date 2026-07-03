---
title: Vault Lite Bootstrap Redesign — Agent-Only Injection
created: 2026-07-03
type: rule
tags: [system, bootstrap, vault, agent, design]
confidence: high
---

# Vault Lite Bootstrap Redesign — Agent-Only Injection

> **BLUF**: `llm-wiki` profile 볼트 생성 시 자동 주입되는 5개 파일(SCHEMA/RULES/README/PROJECT-WORKFLOW/log.md)을 2개(계약 문서 + 운영 사실 문서) + log.md로 재구성한다. 사람 안내문 톤을 전부 제거하고, "이 vault/도구에 대한 사실"만 남기며, "에이전트가 스스로 판단해야 할 영역(soul/memory)"은 내용을 채우는 대신 그 경계를 명시적으로 선언한다.

---

## 1. 배경 및 문제의식

- Raven의 north star는 "사람 1차 사용자, Obsidian처럼 자유로운 vault". 사람은 안내문 없이 그냥 md를 씀.
- 그런데 현재 `llm-wiki` profile(기본값)은 5개 파일을 주입하며, 그중 `_meta/system/README.md`는 제목이 "Vault User Guide"라 사람용처럼 보였음.
- 실제로 내용을 열어보니 `audience: agent`이고 100% 에이전트 운영 사실(읽기 순서, MCP 도구 매핑, 권한 매트릭스, 저장 결정 기준)이었음 — 이름만 사람용이었지 삭제 대상이 아니었음.
- 반대로 `_meta/agents/PROJECT-WORKFLOW.md`에는 다른 에이전트 프로필("Hermes Constitution")의 자가평가 기준까지 박혀 있어, vendor-neutral 원칙(AGENTS.md §11)과 충돌하는 "에이전트 소울/판단력 콘텐츠"가 섞여 있었음.
- 사용자 결정: **vault 문서 = 이 vault/도구에 대한 사실만. 에이전트 자신의 일반 판단력·습관은 vault가 아니라 에이전트 자신의 soul/memory에 있어야 한다.** 다만 그 경계를 조용히 생략하지 않고, "이건 의도적으로 안 담았다"는 선언을 남긴다.

## 2. 최종 파일 구성

`llm-wiki` profile 부트스트랩 결과물: **5개 → 2개 + log.md**

| 파일 | 위치 | 성격 |
|---|---|---|
| **SCHEMA.md** (SCHEMA+RULES 병합, type 템플릿 흡수) | `_meta/agents/SCHEMA.md` | 데이터 계약 — "이 형태를 안 지키면 lint가 깨진다" |
| **PROJECT-WORKFLOW.md** (system/README.md 흡수, dedup, 소울 콘텐츠 제거) | `_meta/agents/PROJECT-WORKFLOW.md` | 운영 사실 — "이 vault/도구를 어떻게 다루는가" |
| **log.md** (변경 없음) | vault 루트 | 인프라 — append-only 작업 이력 |

`_meta/system/` 디렉토리는 Lite bootstrap에서 완전히 제거된다 (basic profile의 `WELCOME.md`는 이번 스코프 밖, `system/OPERATIONS.md`는 Tier 1로 그대로 유지).

### 2.1 `SCHEMA.md` 목차

1. frontmatter 필수 필드 (title/type/created/updated/sources/confidence/agents)
2. type taxonomy 9종 + 용도
3. tag core/custom
4. wikilink 문법 (`[[x]]` / `[[x]]!` / `[[x]]?`)
5. slug 규칙 (vault-relative path) + 파일명-title 언어 1:1 대응 (기존 RULES R7)
6. raw/ 권한 모델 (사람 1차 CRUD, 에이전트 read-only, `wiki_ingest` 예외) — 기존 RULES R6
7. 검증 명령 (`raven link check`, `raven build`)
8. type별 페이지 템플릿 9종 (기존 PROJECT-WORKFLOW §3에서 이동 — 데이터 형태 정의이므로 계약 문서가 더 적합)

### 2.2 `PROJECT-WORKFLOW.md` 목차

1. 읽는 순서 (log.md 최근 줄 → content/index.md → 관련 문서 3-5개 → SCHEMA.md) — 기존 두 파일에 중복 서술되던 것 dedupe
2. 4가지 명령 키워드 → MCP 도구 매핑 (save/ingest/query/lint → wiki_update/wiki_ingest/wiki_search/wiki_lint)
3. 권한 매트릭스 (raw/content/_meta × 사람/에이전트)
4. 저장 결정 4가지 신호 (재사용성/인수인계/근거추적/실패기록) — Raven 고유 데이터 큐레이션 정책이므로 유지
5. 분업·트리거 사실만 (철학적 설명 제거) — "사용자 X 요청 → journal/concept 자동 작성" 류의 매핑만
6. 폴더 구조 권장 (content/decisions, concepts, journal, issues, projects, people, raw/)
7. 형식 요구사항 (BLUF 시작, 운영 메타 본문 노출 금지, 자연어 헤더) — "왜 좋은가" 설명 없이 요구사항만
8. 위키링크 작성 기준 (맥락 있는 링크 + outbound ≥1)
9. 멀티 에이전트 협업 규칙 (폴더 격리, log.md 동시쓰기 프로토콜, wiki.db/collections.yaml 직접 수정 금지)
10. 하지 말 것 (통합 forbidden list)
11. MCP 연결 signpost — "연결 정보/도구 목록은 `raven docs show agent-tools` 참고" (호스트/포트는 하드코딩하지 않음 — Tier 1이 단일 출처)
12. 다음 단계 — `docs/vault-patterns.md` 포인터 (raw/log.md/_meta/agents opt-in 확장 패턴)
13. **"이 문서에 없는 것 — 에이전트 스스로 판단/기억할 영역"** (신규 섹션, §3 참조)

### 2.3 완전히 제거되는 내용

- `system/README.md`의 "정원사/Karpathy 인용" 철학적 도입부 → 1줄로 압축
- `PROJECT-WORKFLOW.md` §10 자가평가 기준 전체, 특히 "Hermes Constitution 투영" — vendor-neutral 원칙 위반 + 에이전트 소울 영역
- BLUF/사람우선원칙의 "왜 좋은가" 정당화 설명 — 형식 요구사항만 남기고 제거
- §0/§1 읽기 순서 중복 서술 (두 파일 다 갖고 있었음) → 1곳으로 통합

## 3. "이 문서에 없는 것" 섹션 (신규)

`PROJECT-WORKFLOW.md` 마지막에 아래 내용을 명시적으로 선언한다. 목적: 조용히 생략하지 않고 "왜 없는지 + 에이전트가 뭘 해야 하는지"를 남겨 향후 재유입(scope creep)을 막는다.

```
## 이 문서에 없는 것 — 에이전트 스스로 판단/기억할 영역

아래는 이 vault 문서가 의도적으로 다루지 않는 영역입니다.
Raven은 "무엇이 있는지(사실)"까지만 알려주고, "언제/어떻게 판단할지"는
당신 자신의 운영 원칙(soul) 또는 메모리 시스템에 있어야 합니다.
그런 판단 기준이 아직 없다면, 이 vault가 아니라 당신 자신의 메모리에
저장하십시오.

- **검색 판단**: `wiki_search`가 있다는 사실은 여기 있지만,
  "새 페이지 쓰기 전에 중복을 확인할지"는 당신의 판단입니다.
- **정리/폐기 판단**: `raven garden --stale/--orphan`, `raven curator run`이
  있다는 사실은 여기 있지만, "언제 돌릴지"는 당신의 판단입니다.
- **글쓰기 품질 판단**: 이 vault는 BLUF로 시작하는 형식을 요구하지만,
  "왜 그게 좋은 글쓰기인가"는 여기서 가르치지 않습니다.
- 이 vault를 반복해서 다루며 얻은 **이 vault 특유의 교훈**은 문서를
  직접 고치지 말고(`_meta/`는 에이전트 write 금지) 당신의 메모리에
  쌓으십시오.
```

## 4. 영향 범위 (구현 시 함께 수정)

| 파일 | 변경 내용 |
|---|---|
| `raven/core/vault.py` | `_LITE_BOOTSTRAP_FILES` 튜플을 3-entry(`_meta/agents/SCHEMA.md`, `_meta/agents/PROJECT-WORKFLOW.md`, `log.md`)로 축소, `_bootstrap_lite()` template_map 갱신 (system_dir mkdir 제거) |
| `raven/core/verify.py` | 파일 목록을 template_map과 mirror 유지 |
| `raven/core/templates/system/SCHEMA.md`, `RULES.md`, `README.md` | 삭제 (내용은 병합되어 `templates/agent/`로 이동) |
| `raven/core/templates/agent/SCHEMA.md` | 신설 (§2.1 목차 반영) |
| `raven/core/templates/agent/PROJECT-WORKFLOW.md` | 전면 재작성 (§2.2 목차 반영, 소울 콘텐츠 제거) |
| `raven/core/templates/system/WELCOME.md` | "더 필요하면 SCHEMA/RULES/README/PROJECT-WORKFLOW/log.md" 안내 문구를 새 2-파일 구성으로 수정 |
| `raven/api/server.py` | bootstrap 필드 설명 문구의 파일 목록 갱신 |
| `raven/mcp/resources.py` | `wiki_schema` 리소스가 `<vault>/SCHEMA.md`(루트)를 읽는 기존 버그를 `_meta/agents/SCHEMA.md`로 수정하면서 동시에 해결 |
| `dashboard/src/routes/VaultManage.tsx` (L718 부근) | "지침 당겨오기" 확인 다이얼로그의 파일 목록 문구 갱신 |
| 루트 `README.md` | "Lite bootstrap" 표 (5종 → 2종+log.md) |
| `AGENTS.md` §4 | Tier 2 표 갱신 |
| 기존 bootstrap 관련 테스트 | 파일 목록/경로 assertion 갱신 |

## 5. 스코프 밖 (이번엔 안 건드림)

- `basic` profile의 `WELCOME.md` — 동일 원칙 적용 여지 있으나 별도 논의로 미룸
- MCP `FastMCP(instructions=...)` 필드 활용 — 사용자가 직접 프롬프팅으로 MCP 위치를 안내하는 방식을 쓰기로 함
- profile 기본값(`llm-wiki`) 변경 — 그대로 유지, "무엇을 주입하는가"만 바뀜

## 6. 검증 기준

- `raven vault create <name> <path>` (기본 profile) 실행 후 vault에 `_meta/agents/SCHEMA.md`, `_meta/agents/PROJECT-WORKFLOW.md`, `log.md` 3개만 생성되고 `_meta/system/`은 없어야 함
- `raven vault verify <name>` 이 새 2-파일 기준으로 통과해야 함
- Dashboard "지침 당겨오기" 실행 시 새 파일 목록으로 diff-and-overwrite 되어야 함
- `wiki://{vault}/schema` MCP 리소스가 실제 `_meta/agents/SCHEMA.md` 내용을 반환해야 함 (기존 dead-code 버그 해결 확인)
