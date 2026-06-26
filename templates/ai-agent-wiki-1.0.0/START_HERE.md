# START_HERE.md — 첫 실행 가이드

> 신규 사용자가 자신의 AI 에이전트에게 **첫 실행 프롬프트**로 붙여넣는 문서입니다.
> 아래 "첫 프롬프트" 블록 전체를 복사해 에이전트에 전달하세요.

---

## 첫 프롬프트 (그대로 복사해 사용)

```
너는 지금부터 내 vault의 운영자다. 다음 순서로 첫 vault를 세팅하라.

1. 이 템플릿 폴더의 구조와 다음 파일들을 모두 읽어라:
   - README.md
   - AGENTS.md
   - index.md
   - log.md
   - prompts/first-setup.md

2. AGENTS.md의 "5가지 저장 필터"와 "파일 수정 범위"를 반드시 숙지하라.

3. Raven CLI가 설치되어 있는지 확인하라 (`raven --version`).
   설치되어 있으면 다음을 수행하라:
     a) `raven vault create` 로 새 vault를 만들어라 (이름은 사용자에게 확인).
     b) `raven vault use <name>` 으로 active vault를 전환하라.
     c) `raven build` 로 wiki.db를 빌드하라.
     d) Raven SCHEMA bootstrap 결과(SCHEMA.md, RULES.md, log.md, _meta/)가
        vault에 자동 복사되었는지 확인하라.
        절대 복사되면 안 되는 파일(OPERATIONS.md, agent/*, raven-policy.md)이
        함께 들어오지 않았는지도 확인하라.

4. 사용자에게 다음을 한 줄로 보고하라:
   - 만든 vault 경로
   - active vault 이름
   - bootstrap으로 들어온 파일 4종
   - 다음 단계로 가능한 작업 (예: 첫 노트 저장, 외부 자료 ingest)

5. 모든 작업이 끝나면 vault의 `log.md` 에 다음 형식으로 한 줄 append하라:
   `YYYY-MM-DD HH:mm | first-setup | <vault-name> created, bootstrap verified | <vault-path>`

지금 시작하라.
```

---

## 5가지 저장 필터 (프롬프트 어디든 붙여넣어 재확인 가능)

`save` 또는 `ingest` 명령을 받으면, 노트 작성 전 다음 5문항을 확인하라.

1. 반복 재사용 정보인가?
2. 인수인계가 필수인가?
3. 결정 추적이 필요한가?
4. 실패/리스크 기록인가?
5. 팀 공통 규칙/가이드인가?

모두 "아니오"면 저장하지 마라.

---

## Raven CLI 매핑 (필수 암기)

| 사용자 키워드 | Raven CLI |
|---|---|
| `save` (단일 노트) | `raven page new <slug> --title ... --type ... --tags ...` |
| `ingest` (일괄) | `raven page new ...` (반복) + `raven build` |
| `query` | `raven page get <slug>`, 또는 MCP `wiki_search` / `wiki_get_page` |
| `lint` | `raven lint run`, `raven link check`, 또는 MCP `wiki_lint` |
| `first-setup` | `raven vault create` → `raven vault use` → `raven build` |

페이지 `type` 은 8종만 사용 가능: `concept / person / tool / comparison / project / query / journal / rule`

---

## 다음 단계

첫 실행이 끝났다면, 상황에 따라 다음 프롬프트를 사용하세요.

- 한 건의 노트를 정리하고 싶을 때 → `prompts/save.md`
- 외부 자료(논문, 문서, 글)를 일괄로 가져올 때 → `prompts/ingest.md`
- 기존 노트를 검색/조회할 때 → `prompts/query.md`
- vault 무결성을 점검할 때 → `prompts/lint.md`