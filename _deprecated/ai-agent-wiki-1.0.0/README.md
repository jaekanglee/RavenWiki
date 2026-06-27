# AI Agent Wiki Template (Raven Edition) v1.0.0

> AI 에이전트와 사람이 함께 쓰는 마크다운 기반 지식 베이스 템플릿.
> 마크다운 기반 PKM 도구 **Raven** 위에서 동작하도록 설계되었습니다.

---

## 1. 이 템플릿은 무엇인가요?

`AI-Agent-Wiki-Template`은 AI 에이전트(단일 또는 멀티)와 사람이 **함께** 마크다운 노트를 축적·검색·유지보수할 수 있도록 만들어진 **vault 템플릿**입니다.

- **저장소**: 마크다운 파일 (`.md`) + frontmatter (YAML)
- **검색/링크**: wikilink `[[slug]]` + FTS5 BM25 인덱스
- **진입점**: REST API, Dashboard, MCP (Model Context Protocol) 어느 경로로든 접근 가능

이 템플릿은 특정 AI 서비스에 종속되지 않습니다 (vendor-agnostic). 명령 키워드는 영어로 고정하고, 도구명은 절대 박지 않습니다.

---

## 2. Raven 이란?

Raven은 옵시디언(Obsidian)을 대체하기 위한 **마크다운 기반 PKM 노트 프로덕트**입니다.

| 항목 | 값 |
|---|---|
| 종류 | 마크다운 노트 프로덕트 (PKM) |
| 사용자 | (a) 사람, (b) 단일 에이전트, (c) 멀티 에이전트 |
| API 진입점 | `http://<host>:8765` |
| Dashboard | `http://<host>:5173` |
| MCP | `fastmcp` 서버 (`wiki_*` 도구 9종) |
| 페이지 타입 | 8종 (concept / person / tool / comparison / project / query / journal / rule) |

> "wiki" 라는 단어는 일반 명사(knowledge base)로만 사용합니다. Raven은 **노트 프로덕트**입니다.

---

## 3. 운영 원칙 (필수)

### 3.1 5가지 저장 필터

어떤 에이전트든, 사람이든 vault에 노트를 **저장하기 전에** 다음 5문항을 확인하세요. 하나라도 "예"라면 저장합니다.

1. **반복 재사용 정보인가?** — 다시 찾게 될 가능성이 있는가?
2. **인수인계가 필수인가?** — 다음 세션/에이전트/사람에게 전달이 필요한가?
3. **결정 추적이 필요한가?** — 왜 그렇게 했는지 근거를 남겨야 하는가?
4. **실패/리스크 기록인가?** — 같은 실수 반복을 막기 위함인가?
5. **팀 공통 규칙/가이드인가?** — 다른 에이전트도 따라야 하는가?

### 3.2 도메인 가정 금지 (개발단 원칙)

이 템플릿은 도구를 정의할 뿐, **vault 안의 프로젝트/도메인 구조는 사용자(사람/에이전트)가 동적으로 결정**합니다.

- 어떤 도메인/프로젝트가 있는지 이 템플릿은 가정하지 않습니다.
- 템플릿은 빈 골격만 제공합니다. 프로젝트 분류, 태그 규칙, 노트 컨벤션은 사용자 vault에서 정하세요.

### 3.3 페이지 타입 = Raven SCHEMA 8종

```
concept | person | tool | comparison | project | query | journal | rule
```

이 8종 외 타입을 새로 만들지 마세요. frontmatter `type` 필드는 위 8개 중 하나여야 합니다.

---

## 4. 폴더 구조

```
ai-agent-wiki-1.0.0/
├── README.md                ← 사람이 읽는 안내서 (이 파일)
├── AGENTS.md                ← 어떤 AI 에이전트든 따라야 하는 운영 규칙
├── START_HERE.md            ← 신규 사용자/에이전트 진입 가이드
├── index.md                 ← vault 지도 (사람 + 에이전트 공용)
├── log.md                   ← 작업 로그 (append-only)
├── VERSION                  ← 1.0.0
├── LICENSE.md               ← 라이선스
├── TEMPLATE_MANIFEST.md     ← 템플릿 필수 파일/디렉토리 manifest
├── .gitignore               ← OS metadata / secrets 제외
├── prompts/
│   ├── first-setup.md       ← 첫 vault 세팅 프롬프트
│   ├── save.md              ← 단일 노트 저장 프롬프트
│   ├── ingest.md            ← 외부 자료 일괄 ingest 프롬프트
│   ├── query.md             ← 검색/질의 프롬프트
│   └── lint.md              ← 무결성 검사 프롬프트
└── scripts/
    └── verify-raven-vault.sh ← 배포 전 검증 스크립트
```

### 4.1 Lite bootstrap (vault 생성 시 자동 복사)

Raven이 사용자 vault를 처음 만들 때 다음 파일만 자동 복사됩니다.

| 자동 복사 ✅ | 자동 복사 ❌ |
|---|---|
| `SCHEMA.md`     | `OPERATIONS.md`  |
| `RULES.md`      | `agent/*`        |
| `log.md`        | `raven-policy.md`|
| `_meta/`        | (없음)           |

이 템플릿 파일(`README.md`, `AGENTS.md`, `START_HERE.md`, `index.md`, `prompts/`, `scripts/`, …)은 **vault bootstrap 대상이 아닙니다**. 사용자 vault는 비어 있는 상태에서 시작합니다.

---

## 5. 시작 가이드

### 5.1 사람용 (1회)

1. 이 템플릿을 사용자 vault 경로에 복사합니다.
2. `START_HERE.md` 를 에이전트 프롬프트에 붙여넣어 첫 vault 세팅을 실행시킵니다.
3. 에이전트가 `raven vault create`, `raven vault use` 로 새 vault를 만들고, `SCHEMA.md` / `RULES.md` / `log.md` / `_meta/` 가 자동 복사되었는지 확인합니다.

### 5.2 에이전트용 (매 세션 시작)

1. `index.md` 와 `log.md` 를 읽어 직전 작업 맥락을 파악합니다.
2. 명령 키워드(`save` / `ingest` / `query` / `lint`)에 맞춰 작업을 수행합니다.
3. 작업 끝나면 `log.md` 에 한 줄 추가하고 사용자에게 보고합니다.

자세한 운영 규칙은 `AGENTS.md` 를 따르세요.

### 5.3 Raven CLI 빠른 참조

```bash
raven vault create <name> <path>    # 새 vault 생성
raven vault list                    # vault 목록
raven vault use <name>              # active vault 전환
raven page new <slug> --title ... --type ... --tags ...
raven page get <slug>               # 페이지 읽기
raven page delete <slug>            # 페이지 삭제
raven link check                    # wikilink 감사
raven build                         # wiki.db 빌드
raven lint run                      # lint (12 check)
raven log list                      # log.md 보기
```

### 5.4 MCP 도구 빠른 참조 (9종)

| 모드 | 도구 | 용도 |
|---|---|---|
| read | `wiki_search(query, top_k)` | FTS5 BM25 검색 |
| read | `wiki_get_page(slug)` | 페이지 조회 |
| read | `wiki_lint()` | lint 실행 |
| read | `wiki_graph(project, fmt)` | 링크 그래프 |
| read | `wiki_log(tail_n)` | log 조회 |
| write | `wiki_update(slug, content, frontmatter)` | 페이지 작성 |
| write | `wiki_ingest(source, project, mode)` | raw ingest |
| admin | `wiki_delete(slug)` | 페이지 archive |
| admin | `wiki_rename(old_slug, new_slug)` | slug rename |

---

## 6. 배포 전 검증

저장소 push 전 다음을 실행하세요.

```bash
# 1) 템플릿 무결성
bash scripts/verify-raven-vault.sh

# 2) Raven CLI가 설치된 환경이면 lint 까지
raven lint run --no-log
```

`verify-raven-vault.sh` 가 점검하는 항목:

- 필수 파일/디렉토리 14개 존재
- OS metadata (`.DS_Store`, `Thumbs.db`) 제거
- secrets 패턴 (`api_key`, `token`, `password`, `secret`) 검사
- `Raven CLI` 가 PATH에 있으면 `raven lint run --no-log` 도 호출

---

## 7. 변경 이력

| 버전 | 날짜 | 변경 |
|---|---|---|
| 1.0.0 | 2026-06-27 | Raven 시스템용 vendor-agnostic 템플릿 출시 |

---

## 8. 라이선스

`LICENSE.md` 참조.