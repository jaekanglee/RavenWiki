---
title: Project Workflow — vault 진입 가이드
created: 2026-06-30
updated: 2026-07-07
type: rule
tags: [system, workflow, meta, mcp]
audience: agent
confidence: high
---

# Project Workflow — vault 진입 가이드

> "사람이 원본을 공급하고, Raven이 그 원본을 정리·누적하는 공간입니다.
> 당신(에이전트)은 그 공간의 옵션 손님입니다."
> 아래는 이 vault/도구를 다룰 때 필요한 사실입니다.

---

## §0. Quick Start (30초) — 행동 시작 7단계

> **첫 줄 인지**: 본 문서 §1+ 는 **Layer 2**(에이전트 활용 레이어) 가이드입니다. 당신의 위치 인지가 이후 모든 행동의 해석 전제입니다. (상세: §0.5)

1. **Layer 1 / Layer 2 인지** — 나는 어디서 일하는가? (→ §0.5)
2. `log.md` 읽기 — 이 vault의 최근 5-10줄 (`grep "^## \[" log.md | tail -5`)
3. (있다면) `content/index.md` 또는 content tree — vault 전체 구조 카탈로그
4. 요청과 직접 관련된 폴더/페이지 3-5개 (project, issue, 결정 기록(`type: rule`), 최근 `journal`)
5. `_meta/agents/SCHEMA.md` — 데이터 계약 (frontmatter / type 9종 / tag taxonomy)
6. `content/` 만 쓰기 — `_meta/system/` 절대 ❌, `_meta/agents/`는 read-only (→ §0.5 §5)
7. `wiki_lint` 실행 — 커밋 전 필수, 새 무결성 에러 0 확인 (§6)

> "파악했다"고 말하기 전에 §0 **파악 완료 기준** 충족 확인.

### 파악 완료 기준

- 이 vault/프로젝트의 현재 목표
- 최근 무엇이 바뀌었는지
- 어떤 폴더/페이지를 source of truth로 봤는지
- 바로 수정해도 되는지, 먼저 물어야 하는지

---

## §0.5 North Star — Layer 1 / Layer 2 + 제품 정체성

> **Normative 5건 (single source of truth)**: 본 절이 본 문서 전체의 규범 정의 위치입니다. 다른 모든 절에서 같은 규범이 반복될 때, 본 절의 표현이 표준이며 나머지는 `→ §0.5` 한 줄로 참조합니다.

### 1) Layer 정의 (Layer 1 = 제품, Layer 2 = 활용)

- **제품 (= Layer 1, "Raven 본체")**: 사람이 1차 사용자로 쓰는 local-first markdown PKM 도구. 당신(LLM 에이전트) 없이도 완성됩니다.
- **활용 (= Layer 2, "에이전트 활용 레이어")**: 당신이 속한 레이어. 당신 자신의 cwd 작업 과정·산출물·인사이트 — 사람 입력이 있을 때도 없을 때도 — 를 vault에 위키화해서, 다음 세션·다음 에이전트·사람이 즉시 활용 가능한 형태로 영구 위임합니다. 사람 curation은 옵션일 뿐, 전제조건이 아닙니다.

### 2) North Star (제품이 정의, Layer 2가 따름)

- **제품(=Layer 1) north star**: **원문 보존 + 증분 누적**. 사람이 만든 원문을 보존하고, 시간에 따라 증분으로 누적되는 형태로 운영됩니다. Raven이 정의합니다.
- **활용(=Layer 2) north star**: 휘발성 메모리 극복 + 살아있는 RAG 진화. 본 문서 §1+ 가 이 north star 시점의 가이드입니다.

### 3) 제품 정체성 변경 금지

제품(=Layer 1)의 정체성 — vault 구조, 데이터 규격(스키마), 운영 패턴, north star — 을 당신이 "더 나은 방식"으로 교체하려 하지 마세요. 당신은 Layer 2에서 일하며, Layer 1이 정의한 north star("원문 보존 + 증분 누적")를 따릅니다.

### 4) 추측 금지 (도메인/구조/타입)

도메인, 팀, 프로젝트, 폴더명, 분류, 구조, type — 무엇이든 모르면 **이미 쓰이는 것을 보고** 그대로 따르세요. **컨텍스트를 가정하지 마세요.** 기준이 모호하면 새 구조를 만들기 전에 사용자에게 확인합니다. (실제 사례: §1 MCP 도구 표, §6.5 정리 절차, §7.5 멀티 에이전트 — 모두 본 원칙을 따름.)

### 5) `_meta/system/` 절대 수정 금지 + `_meta/agents/` read-only

Lite bootstrap 정책(v0.7.65+): vault 진입 시 받는 것은 `_meta/agents/` (SCHEMA.md + PROJECT-WORKFLOW.md), `log.md`, `content/` 입니다. **`_meta/system/`는 Raven 내부 Tier 1** — 외부 에이전트에게 노출되지 않으며, vault에 보이지 않는 폴더가 있다고 가정하지 마세요. 보인다면 오염 가능성이 있으므로 사용자에게 보고하세요. `_meta/agents/`는 직접 수정 금지 (변경 필요 시 `type: issue` 발의 또는 사람 승인). 자세한 권한: §2.

---

> **본 문서 자체는 Layer 1(=Raven)에 의해 자동 제공됩니다.** 내용(§1+)은 Layer 2(에이전트 활용) 가이드이지만, **문서 제공은 Layer 1이 담당합니다**.

---

## §0. 목차

| § | 주제 |
|---|---|
| §0 | Quick Start (30초) — 행동 시작 7단계 |
| §0.5 | North Star — Layer 1/2 + 제품 정체성 (normative 5건) |
| §1 | MCP 사용법 (도구 10종 + 도달법 + 권한 모드) |
| §2 | 권한 — vault 내부 영역 (raw/ / content/ / _meta/ / log.md) |
| §3 | 저장 결정 — 4가지 신호 (쓰기 전 체크) |
| §4 | 문서 작성 규칙 (BLUF, 슬러그, 요약) |
| §5 | 폴더 구조 권장 |
| §6 | 검증 절차 (체크리스트 + 자율점검 + 큐레이션) |
| §7 | 분업 / 트리거 (사실) |
| §7.5 | 멀티 에이전트 협업 규칙 |
| §8 | 하지 말 것 (→ §0.5 / §2 / §3) |
| §8.5 | 부록: 에이전트 스스로 판단/기억할 영역 |
| §9 | 다음 단계 (raw/log.md/_meta/agents opt-in 확장) |

---

## §1. MCP 사용법 (도구 10종 + 도달법 + 권한 모드)

Raven MCP 서버는 권한 모드(`--mode read|write|admin`)에 따라 다음 10개 도구를 제공합니다.
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
| `read` | `wiki_get_guide(kind)` | **v0.7.91+** Lite bootstrap 3종 read-only (`_meta/agents/SCHEMA.md` / `_meta/agents/PROJECT-WORKFLOW.md` / `log.md`). 화이트리스트 외 403, `wiki_stale_detect`로 stale 정책 확인 가능 | `query` |
| `read` | `wiki_get_guide_diff(kind)` | **v0.7.95+** Lite bootstrap 3종 vs raven 설치 템플릿 unified diff (200줄 truncation, v0.7.94 REST 1:1). "내 vault 지침이 왜 mismatch?" 진단 | `lint` |
| `write` | `wiki_update(slug, content, frontmatter?, actor?, idempotency_key?)` | 페이지 생성/갱신 (upsert) | `save` |
| `write` | `wiki_ingest(source, project?, mode="auto", actor?, idempotency_key?, user_command=False)` | raw/ 외부 자료 일괄 정리 (사람 명시 명령 시에만, ADR-2026-07-02) | `ingest` |
| `write` | `wiki_archive(slug, reason?, actor?, idempotency_key?)` | ADR-2026-07-06 §1.3 — `_archive/` 격리 (1.5배 본문 가드 회피) | `archive` |
| `admin` | `wiki_delete(slug, actor?, idempotency_key?)` | 페이지 영구 삭제 (archive와 다름 — 사람 운영자 전용) | `delete` |
| `admin` | `wiki_rename(old_slug, new_slug, actor?, idempotency_key?)` | slug 변경 + 인바운드 wikilink 재작성 | `rename` |

> **모든 도구는 `vault=<등록된 vault 이름>` 인자 필수** — Raven MCP 서버는 다중 vault 등록을 지원하며, 도구 호출 시 어떤 vault를 조작할지 명시해야 합니다.

### §1.1 `wiki_update` 사용 규약 (v0.7.66+)

- `content` = 본문 마크다운. 메타데이터는 **`frontmatter` 파라미터**로 전달 (권장).
  content 선두에 `---` frontmatter 블록을 넣으면 자동으로 메타로 승격되지만,
  파라미터 분리가 정확하다.
- 신규 slug는 생성된다 (upsert). 단, 이 vault에서는 frontmatter의 `type`이
  9종 중 하나여야 생성/수정이 통과한다 (`SCHEMA.md` 참조).
- `raw/`, `_meta/`, `log.md`는 생성/수정 모두 거부된다 (→ §2).
- **에러/제약 발생 시 대응**: 1.5배 초과 차단(`large_rewrite_blocked`)은 제품 north star
  "원문 보존 + 증분 누적" 가드입니다 (→ §0.5). 본문을 억지로 채우지 말고, 기존 문서를
  `wiki_archive` 처리한 뒤 세부 문서로 분할 생성하거나 사용자에게 구조 조정을 제안하십시오.
  `permission_denied` 등 권한 에러 시 즉시 조작을 중단하고 사용자에게 보고하십시오.
- **멱등성 키(`idempotency_key`) 활용**: 네트워크 불안정으로 동일 요청을 재시도할 때는
  반드시 이전 요청과 동일한 `idempotency_key`를 전달하여 볼트 내에 불필요한 중복 데이터가
  쌓이지 않도록 하십시오.

> ADR-2026-07-06: `wiki_stale_detect` (read) + `wiki_archive` (write) — 사람 north star
> "에이전트가 스테일 갱신·격리 루프" 실행 기반. `wiki_update`의 1.5배 가드는 §0.5
> north star 구현.

### §1.2 MCP 도달법 — HTTP localhost (v0.7.81+)

Raven은 표준 **Model Context Protocol (JSON-RPC)** 서버입니다. **HTTP localhost 방식만
지원합니다** — 단일 흐름으로 단순화 (v0.7.81+ HTTP-only 재설계).

#### 운영자가 서버 띄우기 (1회)

```bash
python -m raven.mcp.cli --transport http --host 127.0.0.1 --port 8766 --mode <read|write|admin>
```

- 서버 lifecycle은 운영자가 관리 (직접 띄우거나 launchd/systemd 등록)
- 모드 (read/write/admin) 한 번 정하면 프로세스 수명 동안 고정
- **포트 8766 기본값** (API 8765는 Dashboard backend) — 변경 가능하지만 운영자가 일관성 유지 권장

#### 외부 MCP 클라이언트에 URL 등록 (1줄)

```json
{"url": "http://localhost:8766/mcp"}
```

이 한 줄이면 충분:
- 파이썬 경로 의존성 0
- raven 패키지 위치 의존성 0
- vault 디렉토리 경로 의존성 0
- stdio spawn 보안 sandbox 우회 (일부 클라이언트는 stdio 차단)

#### 표준 흐름

1. `tools/list` 호출 → MCP 표준 자동 discovery → 10개 도구 schema 즉시
2. 첫 호출 시 `vault=<이름>` 인자 필수 (다중 vault 지원)
   - `vault` 이름 = 디렉토리 basename (예: `~/Raven/my-vault/` → `my-vault`)
3. `wiki_search(vault="my-vault", query="...", top_k=10)` 등으로 자유 탐색

> **도메인/구조/타입 추측 ❌** (→ §0.5). `wiki_search`로 먼저 확인.

### §1.3 권한 모드 (read / write / admin)

서버 시작 시 `--mode`로 고정, 한 프로세스 내에서 변경 불가:

| 모드 | 제공 도구 | 일반 사용 |
|---|---|---|
| `read` | 6종 (검색/조회/lint/graph/log/stale_detect) | 기본. 안전. 권장 시작점 |
| `write` | + `wiki_update`, `wiki_ingest`, `wiki_archive` | vault 페이지 생성/수정/격리 |
| `admin` | + `wiki_delete`, `wiki_rename` | 사람 운영자 전용 — 위험 액션 |

> **자율 운영 정책**: `admin` 모드 MCP 서버를 *에이전트가* 운영하지 마세요 — 사람 운영자
> 전용입니다. 일반 에이전트는 `read` (기본) 또는 `write` (필요 시)로 충분합니다.

#### 트러블슈팅

| 증상 | 해결 |
|---|---|
| "address already in use" | 다른 포트 사용 또는 기존 프로세스 종료 |
| "permission_denied" | 운영자에게 `write`/`admin` 모드로 재시작 요청 |
| "vault not found" | `vault` 인자가 디렉토리 basename과 일치하는지 확인 |

### §1.4 포트 매트릭스 (v0.7.83+)

- **API**: `http://localhost:8765` (Dashboard backend)
- **MCP**: `http://localhost:8766/mcp` (외부 에이전트 표준 endpoint)
- **Dashboard**: `http://localhost:5173`

운영자가 `./raven.sh` 또는 `make restart-all`로 3개 모두 자동 관리 — silent stale 방지
(AGENTS.md §9). MCP는 *별도 띄울 필요 없음*.

### §1.5 vault 운영자가 외부 에이전트에게 전달해야 할 것

**vault 경로 한 가지만** 전달하면 충분합니다 (예: `~/Raven/my-vault/`).

- **vault 이름** = 디렉토리 basename — 자동 인식
- **HTTP URL** = `http://localhost:8766/mcp` (API 8765는 Dashboard backend) (위 2단계 스니펫)
- **모드** = 운영자 정책 (read/write/admin)

→ 운영자가 추가로 알려줘야 할 것은 *없음*.

**R9 cross-link**: Raven 소스 코드(`raven/`, `dashboard/` 패키지)를 *직접 조회하지
마세요* — vault 외부 시스템이며 R9 ("vault 외부 시스템/폴더 수정 ❌") 위반입니다.
필요한 모든 정보는 본 문서 + 운영자 README에 있습니다.

## §2. 권한 — vault 내부 영역

> **제품 정체성 (north star "원문 보존 + 증분 누적") 구현**: 영역별 권한 경계는
> §0.5 Layer 1/2 정의의 직접적 구현입니다.

| 경로 | 주체 | 권한 |
|---|---|---|
| `raw/` | 사람 | full CRUD |
| `raw/` | 에이전트 | read-only (`wiki_ingest`는 사람 명시 명령 시에만) |
| `content/` | 에이전트 | read/write (자유) |
| `_meta/` | 에이전트 | read-only (직접 수정 금지 — `raven meta sync`만, `index.md`는 `raven build`) |
| `log.md` | 에이전트 | append만 (도구가 자동 기록, 직접 수정 금지) |

허용되지 않은 쓰기 시도는 API/MCP 수준에서 `permission_denied`로 차단됩니다.
상세 데이터 계약은 `SCHEMA.md` 참조.

## §3. 저장 결정 — 4가지 신호

`save`/`ingest` 받으면 페이지 만들기 **전에** 다음 4문항 확인:

1. **재사용 가능성** — 다시 찾게 될 정보인가?
2. **인수인계 필요성** — 다음 세션/사람/에이전트에게 전달이 필요한가?
3. **결정 근거** — 왜 그렇게 했는지 추적이 필요한가?
4. **실패/리스크 기록** — 같은 실수 반복 방지를 위한가?

모두 "아니오"면 저장하지 마세요. vault는 신호 대 잡음비가 높은 공간입니다.

## §4. 문서 작성 규칙

- **BLUF**: 페이지 첫 줄에 결론/결정 1문장
- frontmatter는 구조화, 본문은 자연스러운 문장으로 작성
- 필수 섹션 최소화(`요약`/`내용`/`관련` 정도), 타입별 상세 섹션은 선택
- **슬러그 번역/음차 금지**: 파일명(Slug)은 Frontmatter의 `title`을 그대로 파일명(slug)으로 하되, 공백/특수문자는 하이픈(`-`)으로 치환하며, 영문은 소문자화하여 1:1로 매핑해야 합니다. 한글 제목을 영문 파일명으로 임의 번역하거나 로마자 음차로 치환해선 안 됩니다.
- **저널 요약 강제**: 일지(`journal`) 및 저널 성격의 문서를 작성할 때는 본문 최상단에 **반드시 3줄 이내의 `# 요약` 섹션을 명확히 작성**해야 합니다. 기계적인 태스크 코드나 빌드 메시지에 의존한 서술은 금지됩니다.
- **빈 섹션 생성 금지**: 채울 내용 없으면 섹션 자체를 삭제 (`TBD`/`N/A` 금지)
- 본문에 `actor`/`run_id`/`tool`/`idempotency_key` 같은 운영 메타 노출 금지
- 헤더는 순수 자연어 (`## 결론`, 영문 괄호 병기 금지)
- 위키링크는 맥락 설명과 함께: `- [[content/x]] — 이 링크가 본문과 어떤 관계인지 1줄`

## §5. 폴더 구조 권장

- `content/decisions/`, `content/concepts/`, `content/journal/`, `content/issues/`, `content/projects/`, `content/people/`
- `raw/` — source material (LLM Wiki +α 켠 경우)
- vault가 이미 다른 구조면 그 구조를 따르세요 (강제 아님, → §0.5 추측 금지)

## §6. 검증 절차 (체크리스트 + 자율점검 + 큐레이션)

### §6.1 일관성 체크리스트

페이지 작성 후 확인:

- [ ] 첫 줄이 결론/결정 1문장 (BLUF)
- [ ] frontmatter: `title`/`type`/`created`/`updated` 채워짐
- [ ] type이 9종 중 하나
- [ ] 슬러그(파일명)가 title과 1:1 매핑되어 일치함 (임의 번역/음차 없음)
- [ ] 일지/저널 문서의 경우 최상단에 3줄 이내의 `# 요약` 섹션이 포함됨
- [ ] wikilink ≥ 1 + 맥락 설명 (Orphan 방지)
- [ ] 본문이 사람 문장으로 읽힘 (운영 메타/JSON/빈 TBD 금지)
- [ ] 모든 쓰기 완료 후 `wiki_lint`를 실행하여 새로운 무결성 에러가 발생하지 않는지 셀프 검증함
- [ ] §3 저장 신호 4가지 통과

### §6.2 에이전트 자율 점검 가이드 (Self-Verification Checklist)

작업 완료 보고 전에 스스로 다음 기준을 만족했는지 재검증하십시오:

*   **지식 밀도**: 이 문서가 훗날 다른 에이전트나 사람이 참고할 만큼 지식 밀도가 높은가?
*   **RAG 4원칙**:
    *   **Think Before Searching (검색 전 사색)**: 뇌피셜로 지식 유무를 추정하지 않고 가정을 검증하기 위해 전문 검색(`wiki_search`)을 계획하여 실행했는가?
    *   **Surgical Retrieval (외과 수술식 조회)**: 불필요한 대량 컨텍스트 대신 정밀한 키워드로 최소한의 정밀한 탐색을 수행했는가?
    *   **Goal-Driven Knowledge Extraction (목표 지향 지식 추출)**: 단순히 검색 결과를 나열하는 대신 문제 해결의 성공 기준에 직접 trace되는 정보만 정밀 추출했는가?
    *   **Root-Cause Investigation (컴파일 전 원인 조사)**: 문서 간 정보 충돌 시 임의로 덮어쓰지 않고, 히스토리(`log.md` 등)를 역추적해 충돌의 근본 원인을 파악한 뒤 지식을 업데이트했는가?

### §6.5 큐레이션 기본 점검 (정리 모드 표준 순서)

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

## §7. 분업 / 트리거 (사실)

- 사람: 결정(rule), 컨셉(concept), 사람(person) — 사람 review 후 확정
  - 에이전트가 이 타입을 작성할 땐 `tags`에 `draft`를 넣어 시작하고, 사람
    확인 후 `review` → `final`로 승격한다 (draft 태그는 lint #13 면제)
- 에이전트: 저널(journal), 빌드/링크체크 — 자동 가능
- 트리거: 사용자 "X 정리해줘" → journal/concept 작성(사람 confirm) / 새 raw/ 파일 → 사람 명시 명령 시 compile / 새 결정 → 관련 페이지에 wikilink 추가

## §7.5 멀티 에이전트 협업 규칙

- **폴더 분리**: 프로필별 `content/{profile_name}/` 전용 서브폴더 내에서만 작성. 타 프로필 영역 수정 필요 시 사용자 승인 또는 `_meta/`에 교차 참조.
- **락/재시도**: MCP 쓰기 도구의 락 획득 상태/에러 반환을 확인하고, 실패 시 백오프 후 재시도. 병렬 작업이 빈번하면 프로필별 독립 브랜치/워크트리 후 순차 통합.
- **log.md**: 액션 뒤에 프로필 식별자 접두사 (`## [YYYY-MM-DD] create | slug [profile-name]`). 동시 대량 작업 시 기록 시점을 미세하게 엇갈리게.
- **wiki.db**: 직접 SQL 수정 금지 — 반드시 `raven build`로 마크다운에서 재컴파일.
- **`_meta/index.md`**: 직접 파싱/수정 금지 — `raven build`의 index builder만 갱신 가능.
- **`SCHEMA.md`**: 에이전트가 임의 수정 금지 — 변경 필요 시 사용자 승인 또는 `type: issue` 문서로 발의.
- **`_meta/collections.yaml`**: 변경 전 `raven collection validate` 필수.

## §8. 하지 말 것

> 각 항목의 normative 정의 위치: §0.5, §2, §3.

- ❌ 도메인/팀/프로젝트를 임의로 가정 (모르면 사용자에게 묻기) → §0.5 §4
- ❌ raw/ 자율 쓰기 → §2
- ❌ `_meta/system/` / `_meta/agents/` 직접 수정 → §0.5 §5, §2
- ❌ `log.md` 기존 줄 삭제/수정 → §2
- ❌ type 9종 외 새 타입 정의 → §0.5 §3 (제품 정체성)
- ❌ §3 저장 신호 모두 미통과 노트 작성 → §3
- ❌ vault 외부 시스템/폴더 수정 → §0.5 §3 (제품 정체성)
- ❌ 한글 title 문서를 영문/로마자 파일명으로 저장 → §4

## §8.5 부록: 에이전트 스스로 판단/기억할 영역

아래는 이 vault 문서가 의도적으로 다루지 않는 영역입니다. Raven은 "무엇이
있는지(사실)"까지만 알려주고, "언제/어떻게 판단할지"는 당신 자신의 운영
원칙(soul) 또는 메모리 시스템에 있어야 합니다. 그런 판단 기준이 아직
없다면, 이 vault가 아니라 당신 자신의 메모리에 저장하십시오.

- **검색 판단**: `wiki_search`가 있다는 사실은 여기 있지만, "새 페이지
  쓰기 전에 중복을 확인할지"는 당신의 판단입니다.
- **정리/폐기 판단**: 무엇을 점검하는지는 §6.5에 있지만, "언제 정리를
  시작할지"는 당신의 판단입니다. (`raven garden`/`raven curator`는 사람
  전용 CLI — 당신의 조치 수단은 `wiki_lint` 감지 + `wiki_update` 수리 +
  `type: issue` 발의까지입니다.)
- **글쓰기 품질 판단**: 이 vault는 BLUF로 시작하는 형식을 요구하지만,
  "왜 그게 좋은 글쓰기인가"는 여기서 가르치지 않습니다.
- 이 vault를 반복해서 다루며 얻은 **이 vault 특유의 교훈**은 문서를
  직접 고치지 말고 당신의 메모리에 쌓으십시오.

## §9. 다음 단계

LLM Wiki 패턴을 더 켜고 싶다면 → `docs/vault-patterns.md` (raw/log.md/_meta/agents opt-in 확장).
