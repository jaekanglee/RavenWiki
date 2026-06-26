# prompts/save.md

> 단일 노트 저장용 프롬프트. 한 건의 노트를 정리해 vault에 기록할 때 사용합니다.

---

## 용도

- 개념/인물/도구/비교/프로젝트/질문/일지/규칙 중 **하나**의 노트를 새로 만들거나 갱신
- 대화/탐색 결과물을 영구 노트로 변환
- 5가지 저장 필터를 통과한 정보만 저장

---

## 프롬프트 (에이전트에 그대로 전달)

```
너는 내 vault의 운영자다. 다음 정보를 단일 노트로 저장하라.

## 입력
- 슬러그(slug): <kebab-case-slug>
- 제목(title): <string>
- 타입(type): <concept | person | tool | comparison | project | query | journal | rule>
- 태그(tags): [<string>, ...]
- 본문(content): <markdown body>
- 출처(sources, 선택): [<url-or-doc-id>, ...]

## 절차
1. 5가지 저장 필터를 다시 확인하라. 하나라도 "예"가 아니면 저장하지 말고 그 이유를 보고하라.
   (1) 반복 재사용? (2) 인수인계 필수? (3) 결정 추적? (4) 실패/리스크? (5) 팀 공통 규칙?

2. 슬러그가 이미 존재하면 갱신 정책(merge vs replace)을 사용자에게 한 줄로 확인하라.

3. 파일 위치 결정:
   - 사용자 vault의 프로젝트 구조에 맞춰 <vault>/content/<path>/<slug>.md 로 둔다.
   - 어떤 디렉토리 구조를 쓸지는 사용자 vault 컨텍스트에 따라 다르다.
     임의로 도메인/프로젝트명을 가정하지 마라.

4. frontmatter를 다음 형식으로 채워라:
   ---
   title: <title>
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   type: <type>
   tags: [<tags>]
   sources: [<sources>]   # 출처가 있을 때만
   ---

5. 본문에서 다른 페이지를 참조할 때는 wikilink 문법을 사용하라:
   - [[other-slug]]       일반 링크
   - [[other-slug]]!      broken intent (의도적 깨짐)
   - [[other-slug]]?      missing intent (대상 없음)

6. 다음 CLI를 호출해 노트를 저장하라:
   raven page new <slug> --title "<title>" --type <type> --tags <tag1,tag2>
   또는 기존 페이지 갱신 시:
   raven page new <slug> ... (동일 명령; idempotent 정책은 vault별 설정 따름)

7. vault의 `log.md` 에 한 줄 append하라:
   YYYY-MM-DD HH:mm | save | <type>/<slug> created | <vault>/content/<path>/<slug>.md

8. 사용자에게 보고하라:
   - 저장한 파일 경로
   - 적용한 5가지 저장 필터 항목 (어떤 문항이 "예"였는가)
   - 본문에서 사용한 wikilink 목록
```

---

## Raven CLI 매핑

```
raven page new <slug> --title "<title>" --type <type> --tags <tag1,tag2,...>
```

필수 옵션: `--title`, `--type`. 선택: `--tags`.

타입은 반드시 8종 중 하나: `concept | person | tool | comparison | project | query | journal | rule`

---

## 체크리스트

- [ ] 5가지 저장 필터 통과 확인
- [ ] 슬러그 중복/갱신 정책 확인
- [ ] `type` 이 8종 중 하나
- [ ] frontmatter 필수 필드 (title/created/updated/type/tags) 채워짐
- [ ] wikilink 문법 준수
- [ ] `log.md` 에 한 줄 append
- [ ] 사용자에게 보고