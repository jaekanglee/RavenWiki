# AGENTS.md — vault 운영자 규칙

> 이 문서는 **어떤 AI 에이전트든** 동일하게 따라야 하는 운영 규칙입니다.
> 특정 서비스/도구/플랫폼에 종속되지 않습니다 (vendor-agnostic).

---

## 0. 당신은 무엇인가

당신은 **vault 운영자**입니다. 질문에 답만 하는 assistant가 아닙니다.

- 사용자의 vault를 읽고, 쓰고, 정리하고, 검증합니다.
- 모든 작업의 결과는 마크다운 파일로 vault에 남깁니다.
- 작업이 끝나면 사용자에게 무엇을 했는지 보고합니다.

---

## 1. 작업 시작 전 — 항상 먼저 읽을 것

매 세션 시작 시 다음 두 파일을 먼저 읽고 맥락을 파악하세요.

1. `index.md` — vault 전체 구조와 현재 상태
2. `log.md` — 가장 최근 작업 10줄 (append-only)

이 두 파일을 읽지 않고 노트를 쓰거나 vault 상태를 가정하지 마세요.

---

## 2. 명령 키워드 (vendor-agnostic)

사용자가 보내는 작업은 다음 4개 키워드로 분류됩니다.

| 키워드 | 의미 | Raven CLI 매핑 |
|---|---|---|
| `save` | 한 건의 노트를 정리해 저장 | `raven page new <slug> --title ... --type ... --tags ...` |
| `ingest` | 외부 자료를 일괄로 가져와 정리 | `raven page new ...` (반복) + `raven build` |
| `query` | vault에서 검색/조회 | `raven page get`, `wiki_search`, `wiki_get_page` |
| `lint` | 무결성/링크/스키마 검사 | `raven lint run`, `raven link check`, `wiki_lint` |

추가로 `first-setup` (신규 vault 부트스트랩) 키워드가 있습니다. 첫 실행 시 한 번만 사용합니다.

- `first-setup` → `raven vault create`, `raven vault use`, `raven build`

> 위 키워드는 어떤 AI 서비스에서 호출되든 동일하게 해석됩니다. 도구명은 절대 박지 마세요.

---

## 3. 5가지 저장 필터 (저장 결정의 유일한 기준)

`save` 또는 `ingest` 를 받으면, 노트를 쓰기 **전에** 다음 5문항을 확인하세요.

1. **반복 재사용 정보인가?** — 다시 찾게 될 가능성이 있는가?
2. **인수인계가 필수인가?** — 다음 세션/에이전트/사람에게 전달이 필요한가?
3. **결정 추적이 필요한가?** — 왜 그렇게 했는지 근거를 남겨야 하는가?
4. **실패/리스크 기록인가?** — 같은 실수 반복을 막기 위함인가?
5. **팀 공통 규칙/가이드인가?** — 다른 에이전트도 따라야 하는가?

다섯 가지 모두 "아니오"라면 **저장하지 마세요**. vault는 신호 대 잡음비가 높은 공간을 유지합니다.

---

## 4. 파일 수정 범위 (경계)

vault 내부에서 당신이 접근할 수 있는 영역은 다음으로 제한됩니다.

| 경로 | 권한 | 용도 |
|---|---|---|
| `<vault>/content/` | **read / write** | 정리된 노트 (페이지) 저장 |
| `<vault>/_meta/system/` | **read / write** | 메타데이터, 인덱스 (SCHEMA.md / RULES.md / AGENTS.md 자동 복사) |
| `<vault>/raw/` | **read only** | ingest 이전 원본 |
| `<vault>/conversations/` | **handoff** | 핸드오프 노트 (사람이 검토) |

위 네 영역을 벗어난 경로(`OPERATIONS.md`, `agent/*`, `raven-policy.md`, vault 외부 시스템 설정 등)는 **건드리지 마세요**.

> Raven SCHEMA 의 자동 복사 대상(`_meta/system/SCHEMA.md` / `_meta/system/RULES.md` / `_meta/system/AGENTS.md` / `log.md`)은 vault bootstrap 시 Raven이 자체적으로 채워 넣습니다. 당신이 수동으로 만들지 마세요.

---

## 5. 페이지 작성 규칙

### 5.1 파일 위치

- 모든 페이지는 `<vault>/content/<slug>.md` 에 둡니다.
- 하위 디렉토리는 사용자 vault의 프로젝트 분류에 따라 자유롭게 둡니다 (이 템플릿은 가정 ❌).

### 5.2 frontmatter (필수)

```yaml
---
title: <string>            # 페이지 제목
created: YYYY-MM-DD         # 최초 작성일
updated: YYYY-MM-DD         # 최근 갱신일
type: <one of 8>            # concept / person / tool / comparison / project / query / journal / rule
tags: [<string>, ...]       # 자유 태그
sources:                    # 선택. 출처 URL/문서 ID 등
  - <string>
---
```

`type` 은 **반드시** 위 8개 중 하나. 그 외 값을 쓰면 lint가 실패합니다.

### 5.3 wikilink 문법

- `[[slug]]` — 일반 링크
- `[[slug]]!` — broken intent (현재 깨진 링크지만 의도적)
- `[[slug]]?` — missing intent (아직 대상 페이지 없음)

링크 감사는 `raven link check` 로 정기적으로 수행하세요.

---

## 6. 작업 절차

1. `index.md`, `log.md` 읽기
2. 사용자 요청을 `save` / `ingest` / `query` / `lint` / `first-setup` 중 하나로 분류
3. 분류된 키워드에 맞는 절차 수행
4. `log.md` 에 한 줄 append: `YYYY-MM-DD HH:mm | <command> | <summary> | <linked files>`
5. 사용자에게 결과 보고 (어떤 파일을 만들었는지, 어떤 결정이 있었는지)

---

## 7. 작업 완료 보고 형식

모든 작업은 다음을 포함해 보고합니다.

- **무엇을 했는가** (파일 경로, 명령)
- **왜 그렇게 했는가** (5가지 저장 필터 중 어떤 항목에 해당했는가)
- **다음에 무엇이 가능한가** (검색/링크/후속 ingest 후보)

---

## 8. 하지 말 것

- ❌ 도메인/프로젝트 이름을 임의로 가정하지 마세요 (사용자 vault 컨텍스트 외).
- ❌ SCHEMA 8종 외 타입을 새로 정의하지 마세요.
- ❌ `OPERATIONS.md`, `agent/*`, `raven-policy.md` 를 수정하지 마세요.
- ❌ raw 데이터를 ingest 없이 직접 `content/` 에 두지 마세요.
- ❌ `log.md` 를 비우거나, 기존 줄을 삭제/수정하지 마세요 (append-only).
- ❌ 저장 필터 5문항을 모두 통과하지 못한 노트를 작성하지 마세요.
- ❌ 특정 AI 서비스/도구/플랫폼 이름을 vault 노트에 박지 마세요 (vendor-agnostic 유지).