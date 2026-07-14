# Raven 기술 계약

이 문서는 Raven vault의 **제품 소유 기술 계약**이다. 에이전트 역할, 기록 기준, 승인 흐름, 글쓰기 방식 같은 운영 정책은 vault 운영자가 별도로 관리한다.

## 소스 오브 트루스

- Markdown 파일이 vault의 원본이다.
- `wiki.db`는 Markdown에서 다시 만들 수 있는 조회 인덱스다. 직접 수정하지 않고 `raven build`로 재생성한다.
- `log.md`는 도구가 남기는 append-only 작업·감사 이력이다.

## Model Context Protocol (MCP) 인터페이스

- Raven은 HTTP localhost 기반 MCP를 제공한다. MCP endpoint는 `http://localhost:8766/mcp`이고, Dashboard API는 `http://localhost:8765`다.
- 클라이언트는 `tools/list`로 현재 서버가 제공하는 입력·출력 schema를 발견한다.
- 호출할 때는 등록된 vault 이름을 명시한다.

## Permission Modes (권한 모드)

서버 시작 시 모드는 고정된다.

| 모드 | 기능 |
|---|---|
| `read` | 검색, 페이지 조회, lint, graph, log, guide, freshness 확인 |
| `write` | read + `wiki_update`, `wiki_ingest`, `wiki_archive` |
| `admin` | write + `wiki_delete`, `wiki_rename` |

정확한 도구 시그니처와 현재 제공 여부는 MCP의 `tools/list`가 기준이다.

## 작업 이력 입력

`wiki_update`로 변경을 기록할 때 `summary`에는 사람이 읽을 수 있는 변경 요약을, `reason`에는 변경 근거를 전달할 수 있다. Raven은 이를 `log.md`의 작업 이력과 기술 감사 정보에 함께 남긴다.

## Hard Path Protections & Audit Records (제품이 강제하는 보호 경계)

- `raw/`, `_meta/system/`, `_meta/agents/`에 대한 에이전트 직접 쓰기는 API/MCP에서 거부된다.
- `log.md`의 기존 줄은 수정·삭제할 수 없다.
- 차단된 보호 경로 쓰기 시도와 기존 log 변조 시도는 audit 기록으로 남는다.
- Markdown 페이지의 데이터 형식·링크·관계 payload·lint 의미는 `SCHEMA.md`가 정의한다.

## Freshness Check 및 Raven 소유 부속의 갱신·조회

- Lite bootstrap과 `raven meta sync` 대상은 `SCHEMA.md`, 이 문서(`RAVEN-CONTRACT.md`), `log.md`뿐이다.
- `wiki_get_guide`, `wiki_get_guide_diff`, `wiki_check_freshness`는 위 Raven 소유 부속의 조회·차이·신선도 확인에만 사용한다.
- 운영자 소유 정책 문서는 Raven이 동기화·해석·검증하지 않는다.
