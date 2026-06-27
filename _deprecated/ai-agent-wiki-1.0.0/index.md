# index.md — vault 지도

> 사람 + 에이전트가 같이 보는 vault 전체 지도. 이 파일이 비어 있으면 vault도 비어 있는 것입니다.

---

## Start Here

| 항목 | 위치 |
|---|---|
| 신규 사용자 첫 실행 | [`START_HERE.md`](START_HERE.md) |
| 사람이 읽는 가이드 | [`README.md`](README.md) |
| 에이전트 운영 규칙 | [`AGENTS.md`](AGENTS.md) |
| 작업 로그 (append-only) | [`log.md`](log.md) |

---

## Vault Structure

```
<vault>/
├── content/         # 정리된 노트 (페이지). read/write.
│   ├── concept/     # 개념 정의
│   ├── person/      # 인물/주체
│   ├── tool/        # 도구/소프트웨어
│   ├── comparison/  # 비교 분석
│   ├── project/     # 프로젝트별 노트 (사용자 정의 구조)
│   ├── query/       # 자주 묻는 질문/답
│   ├── journal/     # 시계열 일지
│   └── rule/        # 규칙/가이드
├── _meta/           # 메타데이터, 인덱스. read/write.
├── raw/             # ingest 이전 원본. read only.
├── conversations/   # 핸드오프/대화 메모. 사람 검토용.
├── SCHEMA.md        # Raven SCHEMA 정의 (bootstrap 자동 복사)
├── RULES.md         # vault 운영 규칙 (bootstrap 자동 복사)
└── log.md           # 작업 로그 (bootstrap 자동 복사)
```

> 위 8개 `content/` 하위 디렉토리는 **Raven SCHEMA 권장 분류**일 뿐 강제는 아닙니다.
> 사용자 vault에서 자유롭게 재구성하세요 (예: 프로젝트별 디렉토리로 통합).

---

## Projects

> 사용자 vault의 프로젝트 분류에 따라 자유롭게 채우는 섹션.
> 에이전트는 사용자가 명시한 프로젝트만 여기에 기록하세요.

_아직 등록된 프로젝트가 없습니다._

<!-- 예시 (사용자 vault 컨텍스트에 맞춰 변경):
- [[project-alpha]]
- [[project-beta]]
-->

---

## Decisions

> 중요한 결정과 그 근거. ADR(Architecture Decision Record) 성격.

_아직 기록된 결정이 없습니다._

<!-- 예시:
- [[adr-2026-06-27-vault-bootstrap]]
-->

---

## Sources

> 외부 자료(논문, 문서, 글) ingest 기록. `sources` frontmatter 또는 별도 페이지로 관리.

_아직 ingest된 자료가 없습니다._

---

## Errors

> 실패/리스크 기록. 같은 실수 반복 방지용.

_아직 기록된 에러가 없습니다._

---

## Prompt Library

| 프롬프트 | 용도 |
|---|---|
| [`prompts/first-setup.md`](prompts/first-setup.md) | 신규 vault 부트스트랩 |
| [`prompts/save.md`](prompts/save.md) | 단일 노트 저장 |
| [`prompts/ingest.md`](prompts/ingest.md) | 외부 자료 일괄 ingest |
| [`prompts/query.md`](prompts/query.md) | 검색/질의 |
| [`prompts/lint.md`](prompts/lint.md) | 무결성 검사 |

---

## Quick Links — Raven 도구

- **Raven CLI**: `raven vault create | list | use`, `raven page new | get | delete`, `raven link check`, `raven build`, `raven lint run`, `raven log list`
- **MCP (9 tools)**: `wiki_search`, `wiki_get_page`, `wiki_lint`, `wiki_graph`, `wiki_log`, `wiki_update`, `wiki_ingest`, `wiki_delete`, `wiki_rename`
- **진입점**: API `:8765`, Dashboard `:5173`, MCP `fastmcp`

---

_last updated: bootstrap_