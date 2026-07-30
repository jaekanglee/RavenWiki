---
created: 2026-07-06
sources:
  - raven/core/templates/agent/SCHEMA.md (Lite bootstrap 2-file, v0.7.65+)
  - _meta/decisions/adr-2026-07-04-schemasys-index-correction.md
tags:
- system
- schema
- meta
- v0.7.x
title: Wiki Schema (v0.7.x)
type: rule
updated: 2026-07-06
---

# Wiki Schema (v0.7.x)

> **v0.7.66+ 코드 SOT 동기화**: 이 문서는 `raven/core/templates/agent/SCHEMA.md` (Lite bootstrap Tier 2, v0.7.65+ 도입)의 내용과 정합.
> v2.4 (8 type) → v0.7.44 type 9종 통일 + v0.7.50+ raw/ 폴더 정책 + v0.7.66+ 14 lint 운영 반영.
>
> **Tier 1 ↔ Tier 2 경계**: 이 문서는 Tier 1 (codebase Raven 운영 SOT) — `raven` 디렉터리의 자체 정책.
> 사용자 vault의 SCHEMA는 Tier 2 (Lite bootstrap 2-file 또는 vault 운영자 문서) — 각 vault 별도 운영.

## Domain

**markdown PKM vault** — Obsidian 의존 없이 markdown + git + 자체 뷰어로 동작. LLM Wiki(Karpathy) 패턴을 차용하되 Obsidian/Sync/유료 플러그인 없이 자체 도구(Raven)로 대체.

## Architecture: SoT 명확화

| 역할 | 무엇 | 추적 | 비고 |
|---|---|---|---|
| **Source of Truth (SoT)** | **markdown 파일** | **git** | 인간/에이전트 모두 작성, 진짜 진실 |
| **Query Index** | **`wiki.db`** (SQLite) | **gitignore** | 빌드 산출물, 검색/조회용 |

## Directory Structure (v0.7.x)

```
<vault>/
├── .vault.json         # vault 메타 (name, path)
├── log.md              # 작업 이력 (chronological, append-only)
├── content/            # ⭐ 사용자 컨텐츠 (slug = vault-relative path)
│   ├── index.md        # 자동 카탈로그 (root)
│   ├── _index/         # 자동 카탈로그 (type별)
│   └── *.md
├── _meta/              # vault 운영 문서 (frontmatter 권장, type: rule)
│   ├── agents/         # Lite bootstrap 2-file (Tier 2, agent-only)
│   │   ├── SCHEMA.md
│   │   └── TOOLS.md
│   └── system/         # Tier 1 확장 (사용자 vault 운영, .gitignore 가능)
├── raw/                # v0.7.50+ 불변 1차 소스 (사람 1차 운영, 에이전트 read-only)
├── _archive/           # retired 페이지
└── wiki.db             # SQLite Query Index (gitignore)
```

### `_meta/` 정책 (v0.7.65+)

- `_meta/agents/` (Lite bootstrap 2-file): Tier 2 = 에이전트 표면. `raven meta sync`로 자동 동기화.
- `_meta/system/`: Tier 1 확장. 사용자 vault 운영자가 자유롭게 관리 (`.gitignore` 가능).
- Lite bootstrap 정책 §4: Tier 1 정책 / Tier 2 leak / vendor 예시 / 다른 에이전트 constitution → vault 주입 금지.

### v2.4 → v0.7.x 변경

- ❌ `concepts/`, `entities/`, `comparisons/`, `projects/` 분리 (v2.4)
- ✅ `content/` 1개 + `type:` frontmatter로 분류 (v0.7.x)
- ✅ `_meta/` 운영 문서 vs content 구분 (모두 type: rule 가능)
- ✅ `raw/` 폴더 정책 (v0.7.50+, 사람 1차 운영)
- ✅ 자동 카탈로그 (root index.md + content/_index/{type}.md)

## Frontmatter (필수 — content/ 안)

```yaml
---
title: Page Title                 # 필수 (한글 title → 한글 파일명, AGENTS.md §10)
type: concept                     # 필수: concept | person | comparison | project | tool | rule | query | journal | issue
tags: [from taxonomy]             # 권장: core = lint 대상
created: YYYY-MM-DD               # 자동
updated: YYYY-MM-DD               # 자동
sources: [raw/articles/source.md] # 선택: 인용된 1차 소스
confidence: high | medium | low   # 선택
contested: true                   # 선택: 모순 발견 시
slug: explicit-slug               # 선택 (v2.2: slug 전략)
aliases: [old-slug-1, old-slug-2] # 선택 (v2.3: rename 정책, v0.7.x title-to-slug 매핑 보존)
issue_status: open | feedback_done | edit_requested | closed # 선택 (type: issue 인 경우 상태 필드)
relations:                        # 선택 (v0.8.x Semantic Relation): 1급 관계망 정의
  - type: uses | depends_on | implements | implemented_by | related
    target: target-slug
    confidence:
      semantic: 0.95
      structural: 0.88
      provenance: 0.99
    verified_by: [human, ai]
    evidence: [repo/path, raw/session/...]
    reason: Contextual explanation
---
```

### v0.7.x Type 9종 (v2.4 8종 → +1 `issue`)

| type | 용도 | outbound ≥ 2 강제 | 예시 | 에이전트 write (PWW §7.1) |
|---|---|---|---|---|
| `concept` | 개념/아이디어 | ✅ 강제 | llm-wiki, mcp-server | ⚠️ draft → 사람 review |
| `person` | 인물 | ✅ 강제 | andrej-karpathy | ⚠️ draft → 사람 review |
| `tool` | 도구/소프트웨어 | ✅ 강제 | hermes-agent | ✅ 자유 |
| `comparison` | 비교 분석 | ❌ 면제 | rag-vs-llm-wiki | ✅ 자유 |
| `project` | 프로젝트 | ❌ 면제 | harumoa-overview | ✅ 자유 |
| `rule` | 규칙/정책 | ❌ 면제 | (SCHEMA 자체) | ⚠️ draft → 사람 review |
| `query` | Q&A 결과 | ❌ 면제 | search-result | ✅ 자유 |
| `journal` | 일기/메모 | ❌ 면제 | daily-2026-06-24 | ✅ 자율 (event_date + §3 4신호) |
| `issue` | v0.7.44+ 문제 분석 / 장애 / 추적 | ❌ 면제 | docs/issues/*.md | ❌ 발의만 (PWW §6.5 #4/#7/#8) |

> **decision (ADR)** — `type: rule` + `decision/adr-YYYY-MM-DD-{slug}.md` 컨벤션. 사람 1차 작성, 에이전트 보조.

9종 외 새 타입 정의 ❌ (AGENTS.md §10). `decision` type 사용 시 → `type: rule` + 폴더 경로/파일명 컨벤션으로 결정 기록임을 표시.

### v0.7.69+ Status 4종 (ADR-2026-07-06 §1.1)

> 사용자 north star (2026-07-06 확인) 실행 기반. 페이지 lifecycle 상태 머신.

| status | 의미 | 진입 트리거 | 검색·링크 |
|---|---|---|---|
| `current` | 사실 검증됨, 권위 있음 (기본값) | 사람 최초 작성, 또는 에이전트 갱신 완료 | ✅ 정상 |
| `stale` | 90일+ 미검증 또는 사실 변경 의심 | `wiki_stale_detect` (MCP) / lint #7 | ⚠️ 헤더 경고 |
| `contested` | 다른 페이지와 모순 발견 | lint #5 (모순 룰) 자동 감지 | ⚠️ 헤더 경고, 양쪽 cross-link |
| `archived` | 격리됨, 더 이상 활성 아님 | `wiki_archive` (MCP) / 사람 CLI | ❌ 검색·그래프 제외 |

**전이 규칙**: `current ↔ stale` (양방향) / `stale → archived` (사람 승인) /
`current ↔ contested` (자동 ❌, 사람 명시) / `archived → current` (사람 승인 필수).

**본문 50%+ 재작성 가드**: `wiki_update` 본문 1.5배 초과 시 `large_rewrite_blocked` (north star 실행 가드).

- 결정: `_meta/decisions/adr-2026-07-06-stale-update-isolate-loop.md`
- 구현: `raven/mcp/tools/stale.py` + `raven/mcp/tools/write.py`
- Lite bootstrap 동기: `raven/core/templates/agent/SCHEMA.md` (Tier 2 자동 복사)

### v0.7.153+ Issue Status 4종
`type: issue` 타입 문서에 한하여, 에이전트 수정 지시 및 피드백 상태를 추적하기 위해 frontmatter `issue_status` 필드를 사용합니다.

| issue_status | 의미 | 트리거 |
|---|---|---|
| `open` | 단순 오픈 (기본값) | 이슈 최초 발행 시 |
| `edit_requested` | 수정요청 | 피드백 전송 또는 사람이 직접 상태 변경 시 |
| `feedback_done` | 피드백완료 | 피드백에 대해 에이전트가 반영 완료했거나 사람이 직접 변경 시 |
| `closed` | 클로즈 | 이슈 해결 완료 또는 사람이 직접 닫음 |

### v0.8.0+ Semantic Relations (M5 관계망)

> **Relation 1급화**: 관계(Relation)는 표현(View, 예: [[wikilink]])과 분리된 1급 데이터입니다. `_meta/vocabularies/`에 정의된 5대 핵심 Vocabulary 관계를 따릅니다.

- **Vocabulary 5종**: `uses`, `depends_on`, `implements`, `implemented_by`, `related`
- **근거(Provenance) 의무**: 모든 relation에는 `evidence`와 `reason`을 포함하여, 지식 망의 생성 근거를 명확히 추적할 수 있도록 합니다.
- **다차원 신뢰도(Confidence)**: 단일 점수 대신 `semantic`, `structural`, `provenance` 차원으로 나누어 다차원 평가 점수를 기록할 수 있으며, 단일 값(high, medium, low)의 주입도 지원합니다.

### System Areas (type 면제, v0.7.66+)

다음 경로는 시스템 자동 생성 영역으로, type 9종 면제 (lint #10 통과):
- `<vault>/_meta/**` — vault 운영 문서 (Tier 2 bootstrap)
- `<vault>/raw/**` — 사람 1차 운영 영역
- `<vault>/content/_index/**` — 자동 카탈로그 (graph hub fan-out 방지, ADR-2026-07-04)
- `<vault>/content/index.md` — root 자동 카탈로그

→ 위 경로 페이지는 type 필드 없이도 lint #10 통과. 9종 정책은 사람이 작성하는 일반 페이지에 한정.

## Tag Taxonomy (v0.7.x: core + custom, 9종 정합)

### Core Tags (lint 대상 — SCHEMA에 명시)
**새 태그 추가 시 SCHEMA에 먼저 등록**:
- 시스템: `system`, `tool`, `ui`, `search`, `viewer`, `schema`, `mcp`, `dashboard`, `meta`, `workflow`, `index`, `home`
- 컨텐츠: `concept`, `person`, `comparison`, `project`, `rule`, `query`, `journal`, `issue`
- 도메인: `ai`, `wiki`, `karpathy`, `llm-wiki`, `tailscale`, `react`, `python`, `docker`
- 상태: `draft`, `review`, `final`, `deprecated`, `orphan`

**lint 동작**: core에 없으면 🔵 info ("not in core taxonomy")

### Custom Tags (자유, lint 면제)
`kotlin`, `android`, `jetpack-compose`, `kubernetes`, `react-19`, ...

**lint 동작**: 자유 허용. tag cloud에 자동 등장.

**승격 절차 (v0.7.x)**:
- lint가 같은 tag가 3+ 페이지에서 사용 시 → "core 승격 추천" 알림
- 사용자가 SCHEMA.md에 한 줄 추가 → 승격 완료
- 10+ 페이지 사용 시 자동 승격 (Q3 변경점)

## Conventions

- **파일명 = title 슬러그 (ADR-2026-07-08 lint #15, 1:1 매칭 필수)**: frontmatter `title`을 그대로 슬러그화 — 공백/특수문자는 `-`, 영문은 소문자화. title과 slug가 다르면 lint #15가 감지. 한글이든 영문이든 title의 언어를 파일명에서 임의로 번역/음차 ❌.
  - ✅ `title: 로컬 개발 포트 매트릭스` → `로컬-개발-포트-매트릭스.md`
  - ❌ `title: 로컬 개발 포트 매트릭스` → `port-matrix-local-dev.md` (영문 임의 변환)
  - **main name + 부속어 예외**: `title`이 "Main Name — 부속 설명" 형식일 때, slug는 main name만 사용 가능 (부속어 = 본문만). lint #15 통과.
    - ✅ `title: MCP Physical Lock — 동시성 충돌 물리적 강제` → `mcp-physical-lock.md` (main name)
    - ❌ `title: MCP Physical Lock — 동시성 충돌 물리적 강제` → `mcp-physical-lock-동시성-충돌-물리적-강제.md` (full 1:1)
  - **예외 (journal/ADR 컨벤션)**:
    - `journal/{title-slug}.md` — 사건일은 frontmatter `event_date: YYYY-MM-DD`로 (선택)
    - `decision/adr-YYYY-MM-DD-{title-slug}.md` — 결정일은 slug에 박되 `created`와 정합
  - **aliases 보존 시 north star 충족 (ADR-2026-07-08 §2)**: `slug` 변경 시 `aliases: [옛slug]` 설정 = wikilink 추적성 유지 = "증분 누적" 충족. **단, 일괄 rename은 vault 운영자 명시 결정 필수** (에이전트 자율 ❌, north star "원문 보존" 위배 회피).
- **인코딩**: UTF-8
- **줄바꿈**: LF
- **위키링크**: `[[wikilinks]]` (slug = vault-relative path, 예: `[[content/llm-wiki]]`, `[[_meta/system-design]]`, `[[SCHEMA]]`)
- **wikilink intent (v0.7.x)**:
  - `[[link]]` — auto (target 존재하면 ok, 없으면 info)
  - `[[link]]!` — broken (CRITICAL)
  - `[[link]]?` — missing placeholder (INFO)
- **교차참조**: outbound ≥ 2 = concept/person/tool 만
- **업데이트**: `updated` 갱신
- **log.md 자동 append**: `raven.core.log.append` (vault-relative lock + atomic write) — 모든 진입점(CLI/API/Dashboard/MCP)이 자동 호출. 트리거 액션 10종: `ingest / update / create / archive / delete / lint / build / migrate / rename / chore`. **CLI만 자동 ❌** (구 문구) — 5개 진입점 전부 자동. 사람 수동 도구는 `raven log list|show|append|rotate|status` (README §191). 자세한 운영 규칙: `adr-2026-07-09-log-md-operations.md`.
- **근거 마커**: 3+ 소스 종합 시 `^[raw/articles/source.md]`

## raw/ 폴더 정책 (v0.7.50+, ADR-2026-07-02)

| 주체 | 권한 | 인터페이스 |
|---|---|---|
| 사람 (1차) | **full CRUD** | Dashboard `/raw` panel, `raven raw ...` CLI, OS 파일관리자 |
| 단일 에이전트 | **read-only** | MCP `wiki_read` (raw slug 조회), `wiki_ingest` (사람 명시 명령 시에만) |
| 멀티 에이전트 | read-only (동시성 보호 없음) | 동일 |

- `wiki_ingest`는 사람 운영자의 명시적 호출 (user_command=True 필수)
- `wiki_update` 등 다른 도구는 raw/ 경로 거부 (HTTP 400 / read-only)
- raw/ 폴더는 source of truth — 에이전트 자율 변조 ❌

## Governance (Cognitive Governance)

> LLM의 자연스러운 중력은 합의/평균. governance는 저항.

### 작성 규칙 (wiki-writer)

- outbound `[[wikilinks]]` ≥ 2 (concept/person/tool 한정)
- 모순 발견 시 `contested: true` + `contradictions: [slug]`
- 단일 출처 = `confidence: medium` 또는 `low`
- 개념 페이지는 "왜 중요한가" 섹션 강제
- 책 뒷면 요약 ❌ (반박/한계/적대자 ≥ 1)

### 분리/아카이브

- 200줄 초과 → 분리 대상 (lint warning)
  - **면제**: `type: rule` (운영 문서, reference 페이지) — `_meta/` 안 페이지
  - **면제**: 1,000줄 미만의 reference/FAQ/guide 류
- 90일 미갱신 + 새 출처 → stale
  - **면제**: `type: rule` (변경 빈도 낮음)
- 365일 미갱신 → `_archive/` 후보

### Lint 자동 탐지 (v0.7.66+ 14개 → v0.7.107 17개 → v0.7.109 18개)

1. 🔴 frontmatter 누락/오류
2. 🔴 broken_link (`[[target!]]` 명시 OR target 존재하면 안 됨)
3. 🔵 missing_link (`[[target?]]` 명시 OR target 미존재)
4. 🟡 orphan (>7일 + inbound 0) — **즉시 ❌, 7일 후 ✅**
   - **면제**: `_meta/` 안 페이지 (rule/reference)
5. 🟡 200줄 초과 — **type: rule 면제** (v0.5.2+)
6. 🔵 weak connection (concept/person/tool 중 outbound < 2)
7. 🔵 tag not in core taxonomy
8. 🔵 `contested: true` 페이지 목록
9. 🔵 90일+ 미갱신 + 새 출처 — **type: rule 면제** (v0.5.2+)
10. 🔵 cognitive_governance_missing (v0.5.3+) — 4신호 미달 페이지 (info)
11. 🟡 index 완전성 (FS vs DB) — v0.7.66+
12. 🔵 log size > 500 entries — v0.7.66+
13. 🔵 cognitive governance 강화 — v0.7.66+
14. 🔴/🟡 tier integrity (v0.7.66+) — Tier 1 leak / _meta/agents/ 보존 검증
15. 🟡 slug-title 1:1 매칭 (ADR-2026-07-08) — frontmatter `title` 슬러그화 결과 ≠ 파일명. `wiki_rename`으로 수리 가능 (PWW §6.5 #15)
16. 🔵 **vault growth rate anomaly** (v0.7.107) — 7일 rolling page count 증가율 > 3σ (과거 30일 기준). north star "증분 누적" 위반 패턴. 사람 운영자 큐레이션 트리거
17. 🟡 **duplicate title candidate** (v0.7.107) — title 유사도 > 0.8 페이지 2개+ — 같은 개념 중복 작성 감지. 큐레이션: `[[wikilink]]` 상호 link 또는 합병 발의 (`type: issue`)
18. 🟡 **audit violation pattern** (v0.7.109) — 30일 log.md에서 단일 actor 5회+ / 단일 path 10회+ permission_denied. north star "원문 보존" 위반 반복 — actor 차단 / 권한 정책 검토

## 빌드 원칙

- **markdown = git 추적 (SoT)**
- **wiki.db = 빌드 산출물 (gitignore)**
- **wiki.db.backup = 일 1회 cron (gitignore)**
- **dashboard/MCP = wiki.db 직접 쿼리** (JSON export ❌)

## Slug Rename 정책 (v0.7.x)

slug 변경 시 (예: `docker-deploy` → `deployment/docker`) 기존 `[[docker-deploy]]` 링크가 모두 깨짐.

**자동 리라이트 정책**:

```yaml
---
slug: deployment/docker          # 새 slug
aliases: [docker-deploy, docker] # 옛 slug alias
---
```

```sql
-- DB lookup: slug 또는 alias로 페이지 찾기
SELECT * FROM pages WHERE slug = ? OR ? IN (
  SELECT value FROM json_each(aliases)
);
```

## MCP 권한 모델 (v0.7.8+: MCP only)

**에이전트 ↔ Raven = MCP only (단일 표준)**. 사람/스크립트는 CLI / API / Dashboard 자유.

| 모드 | 권한 | 도구 |
|---|---|---|
| read (default) | read-only | search, get_page, lint, graph, log |
| write | + write | wiki_update, wiki_ingest (user_command=True) |
| admin | + destructive | wiki_delete, wiki_rename |

## AI 활용 로드맵 (v0.7.x 상태)

| 단계 | 기능 | 시점 |
|---|---|---|
| M1 | 인덱싱 자동화 (curator) | ✅ M1 |
| M2 | MCP server (외부 AI 접근, read-only 기본) | ✅ M2 |
| M3 | Vector Search (`sqlite-vec` 1차) | ⏸ M3 |
| M3 | 관련 문서 추천 (co-citation) | ⏸ M3 |
| M4 | 문서 Q&A (RAG over vault) | ⏸ M4 |
| M5 | 자동 태깅 / 모순 강화 탐지 | ⏸ M5 |
| M6 | 작성 도우미 (초안) | ⏸ M6 |
| ❌ | AI 채팅 (실시간 대화) | OUT |

→ M3-M6 상세: `_meta/ai-roadmap.md`

## 4 진입점 (AGENTS.md §2)

| 진입점 | 용도 | 위치 |
|---|---|---|
| **CLI** | 사람 운영자 / 자동화 (canonical control plane) | `raven/cli/` |
| **HTTP API** | Dashboard backend / 외부 자동화 | `raven/api/` |
| **Dashboard** | 사람 탐색/편집 UX (read-write, API-backed) | `dashboard/` |
| **MCP** | LLM 클라이언트 표준 진입점 (read/write/admin 모드) | `raven/mcp/` |

→ 진입점 추가/제거는 ADR(Architecture Decision Record)로만.

## 관련

- `RULES` — 운영 정책 (M1)
- `agent/TOOLS` (Lite bootstrap Tier 2) — MCP 도구 surface
- `docs/vault-patterns.md` — Karpathy LLM Wiki +α 패턴 opt-in 가이드
- `adr-2026-07-04-schemasys-index-correction` — SCHEMA 9종 + system area 격리 결정

---

## 부록 A. v2.4 → v0.7.x 마이그레이션 노트

**v0.7.0+ 변경 (Lite bootstrap 2-file 도입, 7/3 ebcde83)**:
- `_meta/agents/SCHEMA.md` (Tier 2, 9 type) = 진짜 SOT
- `_meta/SCHEMA.md` (Tier 1, 이 문서) = 사용자 운영 표면 가이드

**사용자 vault 작업**:
- `type: decision` 16개 → `type: rule` 변환 (raven-dev 사이클 7, 7/6, commit 22e2f9e)
- `content/_index/*.md` 자동 카탈로그는 system area (type 면제, 7a6dfd2)
- 한글 title → 한글 파일명 (df99565 → 7b55fd4, 한→한 슬러그)
- raw/ 폴더 정책 (v0.7.50+, 9cd586e → 4fa0014 X-Actor 가드)

→ **이 Tier 1 문서는 v0.7.66+ 코드 SOT와 정합** (다음 갱신: v0.7.69+ 평가 P0/P1 완료 시점).
