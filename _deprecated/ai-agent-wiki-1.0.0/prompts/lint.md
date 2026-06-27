# prompts/lint.md

> vault 무결성 검사용 프롬프트. SCHEMA, wikilink, frontmatter 등을 점검할 때 사용합니다.

---

## 용도

- SCHEMA 위반 (8종 외 type, frontmatter 누락 등) 검사
- wikilink 깨짐 감사
- log.md append-only 규칙 확인
- 5가지 저장 필터 미준수 의심 노트 검토

---

## 프롬프트 (에이전트에 그대로 전달)

```
너는 내 vault의 운영자다. 다음 lint 절차로 vault 무결성을 점검하라.

## 절차
1. SCHEMA 검사
   - 모든 <vault>/content/**/*.md 의 frontmatter `type` 이
     8종 (concept / person / tool / comparison / project / query / journal / rule)
     중 하나인지 확인하라.
   - frontmatter 필수 필드(title, created, updated, type, tags)가 모두 있는지 확인하라.
   - `sources` 는 있을 때만 검사 (선택 필드).

2. wikilink 감사
   - raven link check 로 broken link / orphan link 를 모두 추출하라.
   - `[[slug]]!` (broken intent) 와 `[[slug]]?` (missing intent) 는
     의도적 표시이므로 별도 카테고리로 보고하라.

3. log.md 검사
   - <vault>/log.md 가 append-only로 유지되고 있는지 확인하라.
     기존 줄의 삭제/수정이 발견되면 위반으로 보고하라.

4. 5가지 저장 필터 의심 노트 검토
   - 최근 30일 이내 저장된 노트 중 front `type=journal` 또는 `query` 가 아닌데
     본문이 200자 미만이고 wikilink가 0개이면 "재사용 신호 약함"으로 표시하라.
   - 사용자 판단으로 남길지/삭제할지 결정하게 하라. 자동으로 삭제하지 마라.

5. CLI 실행
   - raven lint run  (12 check 항목)
   - raven link check

6. MCP 사용 가능 시
   - wiki_lint() 도 함께 호출해 cross-check 하라.

7. 결과를 다음 형식으로 사용자에게 보고하라:
   - 검사한 페이지 수
   - SCHEMA 위반 (있으면 목록)
   - broken link / orphan link / broken intent / missing intent (각각 개수와 목록)
   - log.md 위반 (있으면)
   - 재사용 신호 약함 의심 노트 (있으면)

8. vault의 `log.md` 에 한 줄 append하라:
   YYYY-MM-DD HH:mm | lint | <N> pages checked, <M> issues | <report path or "(no issues)">
```

---

## Raven CLI / MCP 매핑

| 검사 | CLI | MCP |
|---|---|---|
| SCHEMA + frontmatter + wikilink + log + 기타 12 check | `raven lint run` | `wiki_lint()` |
| wikilink 감사만 | `raven link check` | — |

---

## 결과 보고 형식

```
## Lint Report — YYYY-MM-DD HH:mm
- pages checked: <N>
- schema violations: <M>
  - <path>: type=<bad-type>
- broken links: <K>
  - <source-page> → <target-slug>
- orphan links: <L>
  - <slug> (no inbound)
- broken intent (!): <I>
- missing intent (?): <J>
- log.md violations: <V>
- low-signal notes: <W>
```

---

## 체크리스트

- [ ] `raven lint run` 실행
- [ ] `raven link check` 실행
- [ ] log.md append-only 확인
- [ ] 재사용 신호 약함 노트 의심 표시
- [ ] MCP `wiki_lint()` (가능 시)
- [ ] `log.md` 에 한 줄 append
- [ ] 사용자에게 위반 목록 + 권고 조치 보고