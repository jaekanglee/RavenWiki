---
title: 새 프로젝트 시작 템플릿
created: 2026-06-25
updated: 2026-06-25
type: project
tags: [project, wiki, template]
sources: [content/harumoa-overview.md]
confidence: high
---

# 새 프로젝트 시작 템플릿

> 새 프로젝트/디렉토리를 시작할 때 이 템플릿을 복사하세요.

## 5단계 가이드

### 1단계: 위치 결정

우리 vault = 단일 `content/` 디렉토리 + `type:` frontmatter로 분류.

**디렉토리 컨벤션**:
```
content/projects/<project-name>/
├── _overview.md           # 프로젝트 소개 (이 템플릿의 역할)
├── _template.md           # 페이지 템플릿 (선택)
├── YYYY-MM-DD.md          # 시계열 노트 (journal)
└── <topic>.md             # 주제별 페이지 (concept/comparison)
```

**예시**:
- `content/projects/harumoa/`
- `content/projects/papers/quantum-2026/`
- `content/projects/book-study/sapiens/`

### 2단계: _overview.md 작성

**필수 frontmatter**:
```yaml
---
title: <프로젝트 이름>
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: project
tags: [project, <도메인 태그>]
sources: [<참조한 메타 문서>]
confidence: high | medium | low
---
```

**본문 권장 구조**:
1. **정의** (1-2 문장)
2. **왜 시작하나** (motivation)
3. **디렉토리 구조** (서브 페이지 위치)
4. **수집 규칙** (어떤 자료를 어떤 형식으로)
5. **출처/링크** (시작점 자료)
6. **관련** wikilinks

### 3단계: SCHEMA 상속 확인

**자동 상속**:
- 모든 vault 페이지가 따르는 기본 [[SCHEMA]] (taxonomy, frontmatter, wikilink 규칙)
- 빌드/lint 도구 ([[scripts/build_db]], [[scripts/lint]])
- 4 wiki 프로필 + MCP (구현 후)

**프로젝트별 override (선택)**:
- 추가 tag: `tags: [project, papers, quantum]` 등
- project-specific frontmatter 필드: `paper_doi:`, `book_chapter:` 등
  → lint가 알 수 없는 필드는 무시 (info 없음)

### 4단계: 첫 페이지 작성

`_overview.md` 다음 페이지 작성:

**journal (일일 노트)** 예시:
```markdown
---
title: 2026-06-26 일일 노트
created: 2026-06-26
updated: 2026-06-26
type: journal
tags: [journal, <project>, daily]
sources: [raw/articles/example.md]
---

# 2026-06-26 일일 노트

## 오늘 한 것
- ...

## 배운 것
- ...

## wikilink
- [[<project>/_overview]]
- [[content/llm-wiki]]
```

**concept 페이지** 예시:
```markdown
---
title: <컨셉 이름>
created: 2026-06-26
updated: 2026-06-26
type: concept
tags: [concept, <project>, <도메인>]
sources: [raw/articles/source.md]
confidence: high
---

# <컨셉 이름>

## 정의
...

## 관련
- [[<project>/_overview]]
- [[content/llm-wiki]]
```

### 5단계: 빌드 + lint + commit

```bash
cd ~/wiki && python3 scripts/build_db.py
cd ~/wiki && python3 scripts/lint.py
git add content/projects/<project>/
git commit -m "feat(<project>): _overview + initial pages"
```

**lint 통과 조건**:
- 0 critical (frontmatter, broken link)
- warning 가능 (200줄 초과 — 분리 권장이지 에러 아님)
- info는 OK (custom tag, weak connection 등)

## 체크리스트

시작 전:
- [ ] `_overview.md` frontmatter (title/type/tags/created/updated) ✅
- [ ] 본문에 "왜 시작하나" 섹션
- [ ] wikilink ≥ 2 (project 타입은 면제지만 권장)
- [ ] tag가 [[SCHEMA]] core taxonomy에 있는지 확인

작성 중:
- [ ] 모든 페이지 frontmatter ✅
- [ ] wikilink vault-relative path (`[[content/llm-wiki]]`)
- [ ] `[[link]]!` 사용 안 함 (의도적 broken만 사용)
- [ ] 의도적 placeholder만 `[[link]]?`

빌드 후:
- [ ] `build_db.py` 0 error
- [ ] `lint.py` 0 critical
- [ ] `wiki.db` 사이즈 확인
- [ ] git commit (한국어/영어 상관없음)

## Anti-pattern

❌ 이렇게 하지 마세요:

| 안티패턴 | 왜 안 되는가 | 대안 |
|---|---|---|
| Obsidian 플러그인 의존 | 우리 시스템은 Obsidian-free | 자체 도구 ([[content/react-spa-architecture]]) |
| `[[wikilink]]!` 남용 | broken link (CRITICAL lint) | `[[wikilink]]` 사용 (target 존재 확인) |
| 500줄 단일 페이지 | 200줄 초과 → lint warning | 분리 ([[SCHEMA]] §분리/아카이브) |
| 모호한 title ("메모", "정리") | 검색/그래프 식별 어려움 | 구체적 ("MCP 권한 모델") |
| raw 직접 인용만 | 비판적 사고 ❌ (Jônadas) | "왜 중요한가" 섹션 + 한계 |
| git 없이 작업 | 롤백 불가 ([[_meta/system-design]] R5) | commit 자주 |

## 확장 — 프로젝트 간 연결

**서로 다른 프로젝트가 cross-link 가능** ([[content/llm-wiki]] "영구 누적"):
```markdown
## 관련
- [[content/projects/harumoa/_overview]]
- [[content/projects/papers/quantum-2026/_overview]]
```

→ dashboard graph view에서 노드 간 엣지로 시각화.

## 예시 프로젝트

| 이름 | 용도 | 시작 가이드 |
|---|---|---|
| **harumoa** | 일일 학습 노트 | [[content/harumoa-overview]] |
| **papers** | 논문 digest | (예정) |
| **book-study** | 책 챕터별 | (예정) |
| **coding-kb** | 코드 패턴 KB | (예정) |

## 관련

- [[content/harumoa-overview]] — 첫 번째 샘플 (실제 구조 참고)
- [[content/llm-wiki]] — 우리 위키 패턴
- [[SCHEMA]] — vault 전체 규약
- [[RULES]] — 운영 정책
- [[_meta/system-design]] — 시스템 설계
- [[scripts/build_db]] — 빌드 도구
- [[scripts/lint]] — lint 도구
