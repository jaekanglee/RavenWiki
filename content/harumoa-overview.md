---
title: Harumoa 프로젝트 — 첫 번째 샘플
created: 2026-06-25
updated: 2026-06-25
type: project
tags: [project, ai, wiki]
sources: [_meta/system-design.md, _meta/mvp-prd.md]
confidence: high
---

# Harumoa 프로젝트 — 첫 번째 샘플

## 정의

> **Harumoa** = 본 위키 시스템의 첫 번째 검증용 샘플 프로젝트.
> "하루 모아" — 일일 학습/노트를 모은다는 의미. 다른 위키 프로젝트의 템플릿 역할.

→ 우리 시스템이 **여러 프로젝트**를 수용할 수 있음을 입증.

## vault 안에서의 역할

| 역할 | 설명 |
|---|---|
| **검증용** | schema/SCHEMA/lint 동작 검증 (페이지 ≥ 10개 필요) |
| **템플릿** | 새 프로젝트 시작 시 참고 구조 |
| **컨텐츠** | 일일 학습 노트/링크/요약 (점진적 축적) |
| **그래프 노드** | 다른 프로젝트와 cross-link 가능 ([[content/llm-wiki]] "영구 누적") |

## 시작 가이드

### 1단계: 디렉토리 생성
```
content/projects/harumoa/
├── _overview.md         # 이 페이지
├── 2026-06-25.md        # 일일 노트
├── 2026-06-26.md        # 다음 노트
└── ...
```

### 2단계: frontmatter (모든 페이지 필수)
```yaml
---
title: 2026-06-25 일일 노트
created: 2026-06-25
updated: 2026-06-25
type: journal
tags: [journal, harumoa, daily]
---
```

### 3단계: wikilink 활용
- 같은 프로젝트 내: `[[harumoa/2026-06-26]]`
- 다른 프로젝트/컨텐츠: `[[content/llm-wiki]]`
- 메타: `[[SCHEMA]]`, `[[RULES]]`

### 4단계: curator가 빌드
```bash
cd ~/wiki && python3 scripts/build_db.py
cd ~/wiki && python3 scripts/lint.py
```

### 5단계: git commit
```bash
git add content/projects/harumoa/
git commit -m "feat(harumoa): 2026-06-25 일일 노트"
```

## 우리 시스템에서의 위치

[[content/llm-wiki]] 패턴에서 Harumoa = **위키의 콘텐츠**:
- raw sources (`raw/articles/*.md`)에서 ingest
- writer가 `content/projects/harumoa/`에 페이지 생성
- curator가 index 갱신
- dashboard가 그래프 + 검색으로 노출

## 다른 프로젝트로 확장

새 프로젝트 시작 시 [[content/_template]] 사용.

**확장 가능성**:
- `content/projects/daily-notes/` — 일일 학습
- `content/projects/papers/` — 논문 요약
- `content/projects/book-study/` — 책 챕터별 노트
- `content/projects/coding-kb/` — 코드 패턴 KB

→ 모두 같은 [[SCHEMA]] + [[scripts/build_db]] + [[scripts/lint]] 사용.

## 왜 "Harumoa"인가

- "하루 모아" — 일일 단위로 모아 위키를 키운다는 의미
- 발음 쉬움 (한국어/일본어 모두 자연스러움)
- 약자로 "hm" — git commit prefix로 사용

## 현재 상태 (2026-06-25)

- 디렉토리: 미생성 (이 페이지만 존재)
- 첫 일일 노트: M1 완료 후 작성 예정
- 목표: M1 종료 시 ≥ 10 페이지 (검증)

## 관련

- [[content/llm-wiki]] — 우리 위키 패턴 (Harumoa가 콘텐츠)
- [[content/_template]] — 새 프로젝트 시작 템플릿
- [[_meta/system-design]] — 시스템 전체
- [[_meta/mvp-prd]] — MVP PRD (Harumoa 검증 기준)
- [[SCHEMA]] — vault 규약
