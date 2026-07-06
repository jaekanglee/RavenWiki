---
title: Project Workflow — vault 진입 가이드
created: 2026-06-30
updated: 2026-07-06
type: rule
tags: [system, workflow, meta, mcp]
audience: agent
confidence: high
---

# Project Workflow — vault 진입 가이드

> "Raven is the IDE; the LLM is the programmer; the wiki is the codebase."
> 사람이 원본 소스를 공급하면, 당신은 이를 정돈하고 요약해 기존 지식과
> 연결·누적합니다. 아래는 이 vault/도구를 다룰 때 필요한 사실입니다.

## 0. 이 vault를 맡았을 때 읽는 순서 (고정)

1. `log.md` 최근 5-10줄 (`grep "^## \[" log.md | tail -5`)
2. (있다면) `content/index.md` — vault 전체 구조 카탈로그
3. 요청과 직접 관련된 폴더/페이지 3-5개 (`project`, `issue`, 결정 기록(`type: rule`), 최근 `journal`)
4. `_meta/agents/SCHEMA.md` — 데이터 계약

→ 이 순서를 건너뛰고 컨텍스트를 가정하지 마세요. 폴더명만 보고 도메인을
추측하지 말고, 이미 쓰이는 용어/분류/구조를 이 vault 기준으로 재사용하세요.
기준이 모호하면 새 구조를 만들기 전에 사용자에게 확인합니다.

**당신이 받는 vault에 포함된 것**: `_meta/agents/` (SCHEMA.md + PROJECT-WORKFLOW.md),
`log.md`, `content/`. 이 외 경로(예: `_meta/system/`, 운영자 README, raven 패키지
내부 CLI 매뉴얼)는 **Lite bootstrap 정책(v0.7.65+)에 의해 포함되지 않습니다**.
vault 안에 보이지 않는 폴더가 있다고 가정하지 마세요 — 보인다면 오염 가능성이
있으므로 사용자에게 보고하세요.

### 파악 완료 기준

"파악했다"고 말하기 전에 최소한 다음은 설명 가능해야 합니다:
- 이 vault/프로젝트의 현재 목표
- 최근 무엇이 바뀌었는지
- 어떤 폴더/페이지를 source of truth로 봤는지
- 바로 수정해도 되는지, 먼저 물어야 하는지

## 1. MCP 도구 9종 (요약)

Raven MCP 서버는 권한 모드(`--mode read|write|admin`)에 따라 다음 9개 도구를 제공합니다.
각 도구의 full 시그니처는 **클라이언트의 `tools/list` 응답**(MCP 표준 자동 discovery)으로
확인할 수 있습니다 — 별도 문서 참조 없이 schema가 자동 제공됩니다.

| 모드 | 도구 | 용도 | 키워드 |
|---|---|---|---|
| `read` | `wiki_search(query, top_k=10)` | BM25 전문 검색 | `query` |
| `read` | `wiki_get_page(slug)` | 페이지 본문/frontmatter/backlinks 조회 | `query` |
| `read` | `wiki_lint()` | 14개 무결성 검사 결과 | `lint` |
| `read` | `wiki_graph(project?)` | 페이지 간 링크 그래프 | `query` |
| `read` | `wiki_log(tail_n=20)` | log.md 최근 N개 구조화 JSON | `query` |
| `read` | `wiki_stale_detect()` | ADR-2026-07-06 §1.3 — stale 후보 + evidence + suggested_action | `lint` |
| `write` | `wiki_update(slug, content, frontmatter?, actor?, idempotency_key?)` | 페이지 생성/갱신 (upsert) | `save` |
| `write` | `wiki_ingest(source, project?, mode="auto", actor?, idempotency_key?)` | raw/ 외부 자료 일괄 정리 (사람 명시 명령 시에만) | `ingest` |
| `write` | `wiki_archive(slug, reason?)` | ADR-2026-07-06 §1.3 — `_archive/` 격리 (1.5배 본문 가드 회피) | `archive` |
| `admin` | `wiki_delete(slug, actor?, idempotency_key?)` | 페이지 영구 삭제 (archive와 다름 — 사람 운영자 전용) | `delete` |
| `admin` | `wiki_rename(old_slug, new_slug, actor?, idempotency_key?)` | slug 변경 + 인바운드 wikilink 재작성 | `rename` |

> **모든 도구는 `vault=<등록된 vault 이름>` 인자 필수** — Raven MCP 서버는 다중 vault 등록을
> 지원하며, 도구 호출 시 어떤 vault를 조작할지 명시해야 합니다.

`wiki_update` 사용 규약 (v0.7.66+):
- `content` = 본문 마크다운. 메타데이터는 **`frontmatter` 파라미터**로 전달 (권장).
  content 선두에 `---` frontmatter 블록을 넣으면 자동으로 메타로 승격되지만,
  파라미터 분리가 정확하다.
- 신규 slug는 생성된다 (upsert). 단, 이 vault에서는 frontmatter의 `type`이
  9종 중 하나여야 생성/수정이 통과한다 (`SCHEMA.md` 참조).
- `raw/`, `_meta/`, `log.md`는 생성/수정 모두 거부된다 (§2 권한).

ADR-2026-07-06 신규: `wiki_stale_detect` (read) + `wiki_archive` (write) — 사람 north star
"에이전트가 스테일 갱신·격리 루프" 실행 기반. `wiki_update`는 본문이 기존 1.5배 초과 시
`large_rewrite_blocked` 거부 — north star "원문 보존 + 증분 누적" 가드.

## 1.5 MCP 도달법 (Raven vault에 어떻게 연결하는가)

Raven은 표준 **Model Context Protocol (JSON-RPC)** 서버입니다. 당신의 MCP 호환 클라이언트가
다음 transport 중 하나로 자동 도달 가능합니다.

| transport | 용도 | 서버 실행 |
|---|---|---|
| **stdio** (권장) | 로컬 sub-process. MCP 클라이언트가 직접 spawn | `python -m raven.mcp.cli --transport stdio --mode <read|write|admin>` |
| **streamable-http** | 원격 (Tailscale, LAN, 공인). HTTP 클라이언트 | `python -m raven.mcp.cli --transport http --host <0.0.0.0|127.0.0.1> --port 8765 --mode <...>` |

**연결 후 즉시 할 일**: `tools/list` 호출 — MCP 표준 자동 discovery로 9개 도구의
full schema(input/output)가 제공됩니다. 별도 "전체 도구 목록" 문서 참조는 불필요.

**구체적 endpoint / command / 환경별 snippet**은 이 vault의 운영자에게 받으세요.
- 운영자가 Dashboard의 신규 vault 마법사를 사용했다면, 마법사 결과 화면에
  환경별 snippet (stdio/HTTP + 클립보드 복사 버튼)이 자동 생성됩니다.
- 운영자가 CLI/Tailscale/Docker 등 다른 환경에서 운영한다면, 같은 정보가
  운영자 가이드(`README.md`) 또는 vault 운영자에게 직접 요청하세요.

**왜 Tier 1 내부 CLI를 가리키지 않는가**: 이 문서는 **외부 MCP 클라이언트가 받는
vault 내용**에 포함됩니다 (Lite bootstrap 정책, v0.7.65+). raven 패키지 내부
CLI(`raven docs show ...` 류)는 Tier 1 — 외부 에이전트가 호출할 수 없습니다.
대신 MCP 표준 discovery(`tools/list`)를 쓰면 vendor/환경에 종속되지 않습니다.

### 1.5.1 표준 MCP 클라이언트 설정 패턴 (vendor-neutral)

당신의 MCP 호환 클라이언트는 다음 두 표준 패턴 중 하나를 지원합니다. 둘 다
Model Context Protocol (JSON-RPC) 표준이라 **어떤 클라이언트든 동일하게 동작**합니다.

| 패턴 | 용도 | JSON 스니펫 |
|---|---|---|
| **`command` 기반** (stdio) | 로컬 sub-process. 클라이언트가 직접 spawn | `{"command": "python", "args": ["-m", "raven.mcp.cli", "--transport", "stdio", "--mode", "read"]}` |
| **`url` 기반** (streamable-http) | 원격 HTTP. 클라이언트가 URL로 호출 | `{"url": "http://<vault-host>:8765/mcp"}` |

> **vault 운영자가 표준 MCP 클라이언트라면** 위 두 스니펫을 자기 클라이언트의 MCP
> 서버 설정 (보통 JSON 파일 또는 UI)에 그대로 추가하면 됩니다. 운영 환경에 따라
> 실제 호스트/포트/mode 값은 wizard 결과 화면 또는 운영자에게 받으세요 (§1.5 안내).

#### 첫 도구 호출 — `vault` 인자

Raven MCP 서버는 *다중 vault 등록*을 지원합니다. 모든 도구 호출 시 **`vault=<등록된 이름>`**
인자가 필수 — 어떤 vault를 조작할지 명시해야 합니다.

```
1. tools/list 호출 (자동 discovery)
2. 발견된 도구 중 하나로 첫 호출 시:
   wiki_search(vault="<이름>", query="...", top_k=10)
3. 응답으로 vault의 페이지/링크/그래프 등 자유롭게 탐색
```

**`vault=<이름>` 모를 때**: vault 운영자에게 직접 요청하거나, 운영자가 Dashboard의
신규 vault 마법사를 사용했다면 마법사 결과 화면에 등록된 이름이 표시됩니다. (Lite
bootstrap 정책상 외부 에이전트는 vault 이름을 *자동으로* 알 수 없습니다 — 운영자에게
확인이 필요합니다.)

#### 권한 모드 (read / write / admin)

서버 시작 시 `--mode`로 고정되며, 한 프로세스 내에서 변경 불가:

| 모드 | 제공 도구 | 일반 사용 |
|---|---|---|
| `read` | 6종 (검색/조회/lint/graph/log/stale_detect) | 기본. 안전. 권장 시작점 |
| `write` | + `wiki_update`, `wiki_ingest`, `wiki_archive` | vault 페이지 생성/수정/격리 |
| `admin` | + `wiki_delete`, `wiki_rename` | 사람 운영자 전용 — 위험 액션 (삭제/이름변경) |

> **자율 운영 정책**: `admin` 모드 MCP 서버를 *에이전트가* 운영하지 마세요 — 사람 운영자
> 전용입니다. 일반 에이전트는 `read` (기본) 또는 `write` (필요 시)로 충분합니다.

#### 연결 안 될 때 (트러블슈팅)

| 증상 | 원인 (가능성) | 해결 |
|---|---|---|
| "command not found: python" | PATH에 python 없음 | 운영자에게 `python3` 또는 venv path 확인 |
| "address already in use" (HTTP 모드) | vault가 다른 모드로 실행 중 | 다른 포트 사용 또는 기존 프로세스 종료 |
| "permission_denied" 응답 | 모드 부족 (예: `read`로 `wiki_update` 호출) | 운영자에게 `write` 모드로 재시작 요청 |
| "vault not found" | `vault` 인자 오타 또는 미등록 | 운영자에게 등록된 이름 확인 |

## 2. 권한 — vault 내부 영역

| 경로 | 주체 | 권한 |
|---|---|---|
| `raw/` | 사람 | full CRUD |
| `raw/` | 에이전트 | read-only (`wiki_ingest`는 사람 명시 명령 시에만) |
| `content/` | 에이전트 | read/write (자유) |
| `_meta/` | 에이전트 | read-only (직접 수정 금지 — `raven meta sync`만, `index.md`는 `raven build`) |
| `log.md` | 에이전트 | append만 (도구가 자동 기록, 직접 수정 금지) |

허용되지 않은 쓰기 시도는 API/MCP 수준에서 `permission_denied`로 차단됩니다.
상세 데이터 계약은 `SCHEMA.md` 참조.

## 3. 저장 결정 — 4가지 신호

`save`/`ingest` 받으면 페이지 만들기 **전에** 다음 4문항 확인:

1. **재사용 가능성** — 다시 찾게 될 정보인가?
2. **인수인계 필요성** — 다음 세션/사람/에이전트에게 전달이 필요한가?
3. **결정 근거** — 왜 그렇게 했는지 추적이 필요한가?
4. **실패/리스크 기록** — 같은 실수 반복 방지를 위한가?

모두 "아니오"면 저장하지 마세요. vault는 신호 대 잡음비가 높은 공간입니다.

## 4. 분업 / 트리거 (사실)

- 사람: 결정(rule), 컨셉(concept), 사람(person) — 사람 review 후 확정
  - 에이전트가 이 타입을 작성할 땐 `tags`에 `draft`를 넣어 시작하고, 사람
    확인 후 `review` → `final`로 승격한다 (draft 태그는 lint #13 면제)
- 에이전트: 저널(journal), 빌드/링크체크 — 자동 가능
- 트리거: 사용자 "X 정리해줘" → journal/concept 작성(사람 confirm) / 새 raw/ 파일 → 사람 명시 명령 시 compile / 새 결정 → 관련 페이지에 wikilink 추가

## 5. 형식 요구사항

- **BLUF**: 페이지 첫 줄에 결론/결정 1문장
- frontmatter는 구조화, 본문은 자연스러운 문장으로 작성
- 필수 섹션 최소화(`요약`/`내용`/`관련` 정도), 타입별 상세 섹션은 선택
- **빈 섹션 생성 금지**: 채울 내용 없으면 섹션 자체를 삭제 (`TBD`/`N/A` 금지)
- 본문에 `actor`/`run_id`/`tool`/`idempotency_key` 같은 운영 메타 노출 금지
- 헤더는 순수 자연어 (`## 결론`, 영문 괄호 병기 금지)
- 위키링크는 맥락 설명과 함께: `- [[content/x]] — 이 링크가 본문과 어떤 관계인지 1줄`

## 6. 폴더 구조 권장

- `content/decisions/`, `content/concepts/`, `content/journal/`, `content/issues/`, `content/projects/`, `content/people/`
- `raw/` — source material (LLM Wiki +α 켠 경우)
- vault가 이미 다른 구조면 그 구조를 따르세요 (강제 아님)

## 7. 일관성 체크리스트

페이지 작성 후 확인:

- [ ] 첫 줄이 결론/결정 1문장 (BLUF)
- [ ] frontmatter: `title`/`type`/`created`/`updated` 채워짐
- [ ] type이 9종 중 하나
- [ ] wikilink ≥ 1 + 맥락 설명
- [ ] 본문이 사람 문장으로 읽힘 (운영 메타/JSON/빈 TBD 금지)
- [ ] §3 저장 신호 4가지 통과

## 7.5 큐레이션 기본 점검 (정리 모드 표준 순서)

vault를 점검/정리할 때는 `wiki_lint`를 돌린 뒤 아래 순서로 처리한다.
각 항목의 괄호는 **에이전트가 실제로 할 수 있는 조치 수준**이다.

1. critical(#1 깨진 링크, #2 intent 오표기, #14 Tier leak) 0건 확인 —
   content/ 내 링크는 `wiki_update`로 직접 수리 (수리 가능), Tier leak은 즉시 보고
2. #5 모순 — 충돌 페이지를 덮어쓰지 말고 양쪽에 `contested: true` +
   `contradictions` 상호 링크, 원인은 log.md 역추적 (수리 가능)
3. #4 orphan(유예 경과) — 관련 페이지에서 인바운드 링크 연결 시도, 불가 시
   아카이브 후보로 `type: issue` 발의 (발의만)
4. #7 stale — 사실이 바뀐 페이지는 갱신, 판단 불가면 `type: issue` 발의
5. #10 frontmatter 불완전 — `wiki_update`의 frontmatter 파라미터로 보수 (수리 가능)
6. #8 200줄 초과 — 분할안 제안 (발의만)
7. #12 log 500건 도달 — 사람에게 `raven log rotate` 요청 (사람 전용)
8. 점검 결과가 §3 저장 신호를 통과하면 journal로 기록

`raven garden` / `raven curator`는 **사람 운영자 전용 CLI**다 — 에이전트는
실행할 수 없으므로, 정리가 필요한 항목은 위 절차대로 감지·발의까지만 한다.

## 8. 멀티 에이전트 협업 규칙

- **폴더 분리**: 프로필별 `content/{profile_name}/` 전용 서브폴더 내에서만 작성. 타 프로필 영역 수정 필요 시 사용자 승인 또는 `_meta/`에 교차 참조.
- **락/재시도**: MCP 쓰기 도구의 락 획득 상태/에러 반환을 확인하고, 실패 시 백오프 후 재시도. 병렬 작업이 빈번하면 프로필별 독립 브랜치/워크트리 후 순차 통합.
- **log.md**: 액션 뒤에 프로필 식별자 접두사 (`## [YYYY-MM-DD] create | slug [profile-name]`). 동시 대량 작업 시 기록 시점을 미세하게 엇갈리게.
- **wiki.db**: 직접 SQL 수정 금지 — 반드시 `raven build`로 마크다운에서 재컴파일.
- **`_meta/index.md`**: 직접 파싱/수정 금지 — `raven build`의 index builder만 갱신 가능.
- **`SCHEMA.md`**: 에이전트가 임의 수정 금지 — 변경 필요 시 사용자 승인 또는 `type: issue` 문서로 발의.
- **`_meta/collections.yaml`**: 변경 전 `raven collection validate` 필수.

## 9. 하지 말 것

- ❌ 도메인/팀/프로젝트를 임의로 가정 (모르면 사용자에게 묻기)
- ❌ raw/ 자율 쓰기
- ❌ `_meta/` 직접 수정 (`raven meta sync`만, `index.md`는 `raven build`)
- ❌ `log.md` 기존 줄 삭제/수정
- ❌ type 9종 외 새 타입 정의
- ❌ §3 저장 신호 모두 미통과 노트 작성
- ❌ vault 외부 시스템/폴더 수정
- ❌ 한글 title 문서를 영문/로마자 파일명으로 저장

## 10. 다음 단계

LLM Wiki 패턴을 더 켜고 싶다면 → `docs/vault-patterns.md` (raw/log.md/_meta/agents opt-in 확장).

## 이 문서에 없는 것 — 에이전트 스스로 판단/기억할 영역

아래는 이 vault 문서가 의도적으로 다루지 않는 영역입니다. Raven은 "무엇이
있는지(사실)"까지만 알려주고, "언제/어떻게 판단할지"는 당신 자신의 운영
원칙(soul) 또는 메모리 시스템에 있어야 합니다. 그런 판단 기준이 아직
없다면, 이 vault가 아니라 당신 자신의 메모리에 저장하십시오.

- **검색 판단**: `wiki_search`가 있다는 사실은 여기 있지만, "새 페이지
  쓰기 전에 중복을 확인할지"는 당신의 판단입니다.
- **정리/폐기 판단**: 무엇을 점검하는지는 §7.5에 있지만, "언제 정리를
  시작할지"는 당신의 판단입니다. (`raven garden`/`raven curator`는 사람
  전용 CLI — 당신의 조치 수단은 `wiki_lint` 감지 + `wiki_update` 수리 +
  `type: issue` 발의까지입니다.)
- **글쓰기 품질 판단**: 이 vault는 BLUF로 시작하는 형식을 요구하지만,
  "왜 그게 좋은 글쓰기인가"는 여기서 가르치지 않습니다.
- 이 vault를 반복해서 다루며 얻은 **이 vault 특유의 교훈**은 문서를
  직접 고치지 말고 당신의 메모리에 쌓으십시오.
