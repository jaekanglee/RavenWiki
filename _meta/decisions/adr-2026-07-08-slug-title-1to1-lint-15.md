# ADR-2026-07-08 — slug-title 1:1 매칭 lint #15 신설

> **상태**: accepted (2026-07-08)
> **결정자**: Raven 운영자 (사용자)
> **변경 성격**: data-contract (lint 정의 = 데이터 계약). 정책 + 권한 변경 동반.

## 1. 맥락

Raven vault의 마크다운 파일은 frontmatter `title`과 slug(파일명)가 1:1로 매핑되어야 사람/에이전트가 직관적으로 탐색 가능. AGENTS.md §10은 *"타이틀과 1:1 매핑되지 않는 임의의 마크다운 파일명(Slug) 지정 ❌"* 정책 보유. SCHEMA.md L81-85는 *"title을 그대로 슬러그화"* 원칙 + *"한글 title → 한글 파일명, 음차/번역 금지"* 명시.

그러나 현재 raven-dev vault 자체가 SCHEMA 위반 사례 보유 (예: `port-matrix-local-dev.md`의 title은 *"로컬 개발 포트 매트릭스"* — 한글이지만 slug는 영문). 2026-07-08 사용자 관찰:

> *"에이전트들이 볼트에 문서 쓸때 yyyy-mm-dd-제목 이런 형식으로 타이틀을 다는 것 같은데 어짜피 문서 만들때 날짜가 자체적으로 들어가는데. 왜 타이틀에 자꾸 날짜를 달지..?"*
> *"frontmatter랑 파일명을 한글로 일치시키는건 어때?"*
> *"p1-2 뭐 이런건 알기가 어렵잌아"*

→ **slug가 사람 단어가 아니고**, **journal/ADR에서 slug에 날짜 박는 컨벤션이 SCHEMA에 없음**, **자동 lint가 없어 위반 누적**. 

## 2. 결정

### 2.1 신규 lint #15 신설

| 항목 | 값 |
|---|---|
| 번호 | #15 (다음 번호) |
| 이름 | `slug-title 1:1 매칭` |
| 심각도 | 🟡 warning (자동 일괄 수정 아님 — 운영자 명시 결정) |
| 규칙 | frontmatter `title` 슬러그화 결과(공백/특수문자 → `-`, 영문 소문자화) ≠ 파일명(확장자 제외) |
| 제외 (System Areas, lint #10과 동일) | `_meta/`, `raw/`, `content/_index/`, `content/index.md`, **+ `decision/adr-*` (ADR 컨벤션 유지)** |
| action | §6.5 큐레이션 절차에 #15 항목 추가: `wiki_rename(new_slug)` 자동 수리. 기존 wikilink 추적성 보존이 필요하면 `aliases`에 옛 slug 보존 (SCHEMA.md L74-75) |
| 자동 일괄 | ❌ — vault 운영자가 명시 결정 (north star "원문 보존 + 증분 누적" 위배 회피) |

### 2.2 SCHEMA.md L81-85 강화 (3 원칙 명시)

1. **title 1:1 매칭 (필수)** — frontmatter title 슬러그화 = 파일명
2. **언어 보존 (필수)** — title의 언어 = 파일명의 언어 (한글/영문 매칭)
3. **의미 있는 슬러그 (필수)** — 약어/시스템 코드만으로 구성된 slug 지양

**journal/ADR 컨벤션 예외**:
- `journal/{title-slug}.md` — 사건일은 frontmatter `event_date: YYYY-MM-DD` (선택)
- `decision/adr-YYYY-MM-DD-{title-slug}.md` — 결정일은 slug에 박되 `created`와 정합

### 2.3 PWW §6.5 큐레이션 절차에 #15 항목 추가

`PROJECT-WORKFLOW.md` §6.5 L290-308 큐레이션 8단계 → 9단계로 확장:
- 8번: **#15 slug-title 불일치 → `wiki_rename` 자동 수리 (단 vault 운영자 명시 결정)**

### 2.4 frontmatter 신규 필드 (선택)

- `event_date: YYYY-MM-DD` — journal type이 다루는 **사건일** (메타시점 `created/updated`와 구분)

## 3. 결과

### 긍정
- 사람/에이전트가 파일 목록 보고 의미 즉시 인지 가능
- SCHEMA L81-85 vs 실제 파일 정합 (raven-dev 자체 audit 시 위반 발견됨)
- 큐레이션 워크플로우 자연 통합 — lint 발견 → §6.5 #15 → 운영자 결정
- title-language-slang 일치 → wikilink 안정성 ↑

### 부정 / 비용
- raven-dev 기존 4+ 파일 title과 slug 불일치 (별도 사이클 audit 필요)
- ADR-2026-07-02의 `user_command=True` raw/ 정책과 별개 (영향 0)

### 후속 작업
- **다음 사이클 2번 (별도)**: raven-dev vault 전체 audit + `wiki_rename` 일괄 호출 (운영자 명시 결정 시)
- 다른 vault(babymoa, harumoa, hermes-infra, homelab) 동일 audit
- harumoa `journal/2026-07-02-p1-2-cycle-complete.md` 같은 slug → `journal/{title-slug}.md` + `event_date` 추가

## 4. 변경 파일

- `raven/core/templates/agent/SCHEMA.md` — L81-85 강화 + Lint #15 추가
- `raven/core/templates/agent/PROJECT-WORKFLOW.md` — §6.5 #15 큐레이션 + §1 표 lint #15 자동 수리 표시
- `_meta/SCHEMA.md` — Conventions 강화 + Lint #15 추가
- `_meta/changelog-v0.7.100.md` — 본 ADR 적용 회고
- 본 ADR (신규)

## 5. references

- PWW L81-85 (Slug 규칙) — 본 ADR로 강화
- PWW L100-115 (MCP 도구 표) — `wiki_rename` 표시 추가
- PWW L290-308 (§6.5 큐레이션) — 9단계로 확장
- PWW L328-339 (§8 하지 말 것) — *타이틀과 1:1 매핑되지 않는 임의의 마크다운 파일명 ❌*
- AGENTS.md §10 — 정책 SOT
- SCHEMA.md L74-75 (aliases 정책)
- ADR-2026-07-06 §1.1 — Status 4종 (관련 없으나, `archived` 시 `archive/<YYYY-MM-DD>/<slug>.md` 경로 패턴 참고)
