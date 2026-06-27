# prompts/query.md

> vault 검색/질의용 프롬프트. 기존 노트를 찾을 때 사용합니다.

---

## 용도

- 키워드로 페이지 검색
- 특정 슬러그의 페이지 조회
- 링크 그래프/로그 확인
- 답변에 사용된 출처를 사용자에게 명시

---

## 프롬프트 (에이전트에 그대로 전달)

```
너는 내 vault의 운영자다. 다음 질의에 답하라.

## 입력
- query: <natural-language question or keyword>
- top_k: <정수, 기본 5>

## 절차
1. 먼저 <vault>/index.md 와 <vault>/log.md 를 읽어 vault 맥락을 파악하라.

2. 다음 중 가장 적절한 경로를 골라라:
   a) 정확한 슬러그를 알고 있으면:
      raven page get <slug>
   b) 자유 텍스트 검색이면:
      raven page new ... (X, 잘못됨) — 정확히는 검색 전용 명령 또는 MCP 사용:
      - MCP read 모드: wiki_search(query, top_k)
      - 또는 vault의 grep/fts 도구 (Raven 빌드 결과 wiki.db가 있으면 FTS5 BM25)
   c) 링크 그래프가 필요하면:
      MCP read 모드: wiki_graph(project, fmt)
   d) 최근 작업 로그가 필요하면:
      raven log list  또는  MCP read 모드: wiki_log(tail_n)

3. 검색 결과에서 답변에 인용한 모든 페이지의 슬러그를 사용자에게 명시하라.

4. 답변에 출처가 포함된 사실이 있으면, 해당 페이지의 `sources` frontmatter도 함께 보여라.

5. 결과를 찾지 못했으면 다음을 구분해 보고하라:
   - "검색 결과 없음" — 실제로 없는 경우
   - "broken intent" — `[[slug]]!` 로 표시된 의도적 깨짐
   - "missing intent" — `[[slug]]?` 로 표시된 미작성 대상

6. 사용자에게 한 줄로 보고하라:
   - 사용한 명령 (CLI 또는 MCP)
   - 인용한 페이지 슬러그 목록
   - vault에 새 노트가 필요하다고 판단되면 그 이유 (5가지 저장 필터 중 무엇에 해당)
```

---

## Raven CLI / MCP 매핑

| 목적 | CLI | MCP |
|---|---|---|
| 단일 페이지 조회 | `raven page get <slug>` | `wiki_get_page(slug)` |
| 자유 검색 | (vault의 grep/fts) | `wiki_search(query, top_k)` |
| 링크 그래프 | (별도 도구) | `wiki_graph(project, fmt)` |
| 최근 로그 | `raven log list` | `wiki_log(tail_n)` |

---

## 답변 형식

```
## 답변
<자연어 답변>

## 출처 (vault 슬러그)
- [[slug-1]]
- [[slug-2]]

## 출처 (sources frontmatter)
- <url-1>
- <doc-id-2>

## vault 갱신 후보 (선택)
- <5가지 저장 필터 중 어떤 문항에 해당했는가>
```

---

## 체크리스트

- [ ] `index.md` / `log.md` 먼저 읽음
- [ ] 적절한 CLI 또는 MCP 도구 선택
- [ ] 인용 슬러그 명시
- [ ] sources frontmatter 함께 표시
- [ ] 결과 없을 시 broken/missing intent 구분
- [ ] 저장 후보가 있으면 5가지 필터 사유 명시