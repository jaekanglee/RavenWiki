<!--
이 템플릿은 vault 루트의 `raven-policy.md`로 복사됩니다.
raven-internal 운영 정책이라 Lite bootstrap에서는 자동 복사 ❌.
`raven sync_meta(full=True, force=True)` 또는 `raven docs policy`로 접근.
-->

---
title: Vault Operating Policy
created: 2026-06-26
updated: 2026-07-16
type: rule
tags: [system, policy, meta]
confidence: high
---

# Vault Operating Policy

> 이 vault가 **어떻게 운영되는가** 한 페이지 요약.
> 출처: [[SCHEMA]] (규약) · [[RULES]] (편집) · [[log]] (이력) · 카파시 LLM Wiki gist (2026-04).

## North Star (v0.6.37 재정렬, 사용자 원칙 확립)

> **"Raven은 사람을 1차 사용자로 하는 local-first Zettelkasten-inspired markdown PKM이며, 원하는 vault 영역에만 LLM Wiki 패턴을 +α로 켜 AI 에이전트가 이해하고 재사용하기 좋은 compounding knowledge를 누적한다."**
>
> — **Zettelkasten 원칙 (작은 생각 단위 + 링크 + 누적) + Obsidian 모티브 (자유 vault) + Karpathy LLM Wiki (2026) 영감 + 자체 구현체.** 분업: 사람은 source curate + 방향 결정, **원하면** vault의 특정 영역에서 LLM Wiki 패턴(raw/, log.md, _meta/agents/)을 켜서 에이전트가 compile / cross-reference / lint / consistency를 도울 수 있음. **컴파일 후 reuse, 매번 재구성 ❌.** 모든 운영 결정은 이 한 줄로 수렴.

## 3-Layer 구조 (카파시)

```
┌─────────────────────────────────────────────┐
│ Layer 3: Schema (SCHEMA.md + RULES.md)      │  ← 규약 (이 문서 포함)
├─────────────────────────────────────────────┤
│ Layer 2: Wiki (content/, _meta/, log.md)    │  ← LLM/사용자가 쓰기
├─────────────────────────────────────────────┤
│ Layer 1: Source of Truth (markdown in git)  │  ← 불변의 진실
└─────────────────────────────────────────────┘
              ↓ rebuild
        wiki.db (Query Index, gitignore)
```

- **markdown = SoT** (git 추적)
- **wiki.db = Query Index** (regenerable, gitignore)
- **log.md = 작업 이력** (vault 루트, append-only)

## 핵심 운영 규칙 (5가지)

| # | 규칙 | 검증 |
|---|---|---|
| 1 | 모든 페이지는 frontmatter 필수 | `raven build` |
| 2 | slug = vault-relative path | `raven page new <slug>` |
| 3 | type 9종 + tags core/custom | lint |
| 4 | wikilink 의도 명시 (`[[x]]!` / `[[x]]?`) | `raven link check` |
| 5 | 작업마다 log.md 자동 append | `raven log list` |

## 문서 발행 책임

> 문서 발행은 본문 저장으로 끝나지 않습니다. **근거·분류·연결을 갖춘 지식 노드로 vault에 편입**하는 일입니다.

1. **검색 후 작성**: 기존 문서·규칙·결정을 먼저 찾아 중복을 피하고, 실제로 참고한 문서와 원문만 근거로 사용합니다.
2. **기본 메타데이터**: 발행자는 내용에 맞는 `title`, `type`, 제목에서 파생한 slug, 최소 `tags`, `created`/`updated`를 기록합니다. 원문 근거가 있으면 `sources`, 검증 수준에 맞춰 `confidence`도 기록합니다.
3. **본문 연결**: 독자가 다음에 확인해야 할 기존 문서는 문맥 설명을 붙인 `[[wikilink]]`로 연결합니다. 링크 수를 채우기 위한 연결은 금지합니다.
4. **의미 관계**: `uses`, `depends_on`, `implements`, `implemented_by`, `related`는 실제 관계가 확인되고 `evidence`와 `reason`을 적을 수 있을 때만 기록합니다. 대시보드의 "함께 읽어볼 만한 문서" 추천은 관계 후보일 뿐, 관계를 자동 확정하는 근거가 아닙니다.
5. **예외 메타데이터**: `aliases`는 rename/병합 때만, `contested`·`contradictions`는 실제 충돌을 조사한 뒤에만, `status` 전이는 운영 근거와 권한이 있을 때만 기록합니다.

## 카파시 운영정책 (v0.5.0 도입)

### log.md

- 위치: **vault 루트** (카파시 가이드 그대로)
- 형식: `## [YYYY-MM-DD] action | subject` (grep-parseable)
- append-only, 500 entries 초과 시 rotate
- 자동 append 시점: 페이지 CRUD, build, lint, archive

### frontmatter 신호 (강제 ❌, 권장 ⭕)

```yaml
confidence: high | medium | low   # 단일 출처면 medium/low
contested: true                     # 모순 발견 시
contradictions: [slug-a, slug-b]    # 모순인 다른 페이지
```

→ lint는 "필드 없음 = info" (기존 페이지 안 건드림, SCHEMA에 명시만).

### 운영 규칙 (lint 14개, v0.6.33+)

자세한 14개 항목은 [[SCHEMA]] §"Lint 운영 규칙" 참조. v0.5.0에서는 #1-3 (broken/missing) + #12 (log size) 자동화.

### Lint severity

- 🔴 **critical**: 즉시 수정 (broken link, malformed frontmatter)
- 🟡 **warning**: backlog (orphan after grace, contradiction, tag 미등록)
- 🔵 **info**: 기록만 (stale, large page, low confidence, missing placeholder)

## 작업 흐름

### 페이지 생성

```bash
# 1. 페이지 만들기
raven page new foo --title "Foo" --type concept --tags "ai, concept"
# → content/foo.md (frontmatter 자동)
# → log.md 자동 append (create | foo)

# 2. 본문 작성 (vim 또는 GUI)
# → outbound [[wikilinks]] ≥ 2 (concept/person/tool 한정)

# 3. 빌드 + lint
raven build
# → wiki.db 재빌드
# → log.md 자동 append (build | N pages)
# → lint 결과 출력

# 4. 커밋
git add content/foo.md log.md && git commit -m "feat(content): add foo"
```

### 작업 이력 조회

```bash
# 최근 10개
raven log list --tail 10

# 특정 액션만
raven log list --action lint

# grep-style
raven log search "raven"
```

### Lint 강제 실행

```bash
# link check (v0.5.0)
raven link check

# build + lint (v0.5.1+)
raven build

# dry-run (실제 변경 ❌)
raven build --dry-run
```

## 금지 사항 (Hard Rules)

- ❌ raw 파일 수정 (불변, 1차 소스)
- ❌ vault 외부에서 vault 수정
- ❌ `[[wikilinks]]` 없는 concept/person/tool 페이지
- ❌ `confidence: high` 단일 출처 페이지
- ❌ 200줄 초과 push (분할 권장)
- ❌ wiki.db git commit (gitignore)
- ❌ log.md 수정 (append-only)

## 관련

- [[SCHEMA]] — 데이터 형식 + lint 14개
- [[RULES]] — 편집 5규칙
- [[log]] — 작업 이력
- [[_meta/ai-roadmap]] — M3-M6 로드맵
- 카파시: <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>
