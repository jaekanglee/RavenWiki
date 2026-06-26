# prompts/ingest.md

> 외부 자료 일괄 ingest용 프롬프트. 논문/문서/글 등을 vault로 가져올 때 사용합니다.

---

## 용도

- 외부 자료(URL, PDF, 텍스트 파일, 메모)를 vault에 일괄로 저장
- raw → content 변환 파이프라인 실행
- 5가지 저장 필터를 통과한 항목만 `content/` 로 이동

---

## 프롬프트 (에이전트에 그대로 전달)

```
너는 내 vault의 운영자다. 다음 외부 자료를 ingest 하라.

## 입력
- source: <url | path-to-file | inline-text>
- project: <사용자 vault 컨텍스트의 프로젝트 식별자 (있는 경우)>
- mode: <append | replace | dry-run>

## 절차
1. source가 URL이면 raw 텍스트를 가져와 <vault>/raw/ 아래에
   <timestamp>-<short-hash>.md 로 저장하라.
   source가 파일 경로면 그 파일을 <vault>/raw/ 아래로 복사하라.

2. raw 본문을 분석해 다음 항목으로 분해하라:
   - 개념(concept): 재사용 가능한 정의
   - 인물(person): 주체/저자/팀
   - 도구(tool): 언급된 소프트웨어/서비스
   - 비교(comparison): 두 개 이상 대상의 비교
   - 결정(decision): 자료가 시사하는 결정/근거
   - 에러(error): 자료가 경고하는 실패/리스크
   - 규칙(rule): 자료가 명시하는 팀/도메인 규칙
   위 7가지 분류는 Raven SCHEMA 8 type taxonomy의 부분집합이다.
   (남은 한 타입 "journal/query"는 ingest 결과가 아니라 사용자 활동에서 생긴다.)

3. 각 항목마다 5가지 저장 필터를 다시 확인하라.
   하나라도 "예"가 아니면 <vault>/raw/ 에만 남기고 content/ 로 옮기지 마라.

4. 통과한 항목만 다음 위치에 저장하라:
   <vault>/content/<type>/<slug>.md
   각 파일은 prompts/save.md 의 frontmatter 규칙을 따른다.
   sources 필드에는 원본 URL/파일 경로를 반드시 적어라.

5. 모든 페이지 저장 후 `raven build` 로 wiki.db를 갱신하라.

6. vault의 `log.md` 에 한 줄 append하라:
   YYYY-MM-DD HH:mm | ingest | <source-summary>, <N> pages created | <file1>, <file2>, ...

7. 사용자에게 보고하라:
   - raw로 저장한 파일
   - content로 승격된 페이지 수와 그 목록
   - 5가지 저장 필터로 탈락한 항목이 있다면 그 사유
```

---

## Raven CLI 매핑

| 단계 | 명령 |
|---|---|
| 페이지 생성 (반복) | `raven page new <slug> --title ... --type ... --tags ...` |
| 인덱스 빌드 | `raven build` |
| (MCP 모드) 일괄 ingest | `wiki_ingest(source, project, mode)` |

> MCP `wiki_ingest` 는 write 모드 진입 시 사용 가능. read 전용 환경에서는 CLI만 사용.

---

## 체크리스트

- [ ] source가 `raw/` 에 먼저 저장됨
- [ ] 항목별 5가지 저장 필터 재확인
- [ ] `type` 이 8종 중 하나
- [ ] 각 페이지 `sources` frontmatter 채워짐
- [ ] `raven build` 로 인덱스 갱신
- [ ] `log.md` 에 한 줄 append
- [ ] 사용자에게 보고