---
title: MiniMax-M3 (우리가 쓰는 모델)
created: 2026-06-25
updated: 2026-06-25
type: tool
tags: [tool, ai, system]
sources: [_meta/system-design.md]
confidence: high
---

# MiniMax-M3 (우리가 쓰는 모델)

## 정의

> **MiniMax-M3** — 현재 활성 모델. MiniMax에서 2026년 초 출시한 foundation 모델.
> Hermes Agent의 모델 라우팅을 통해 호출. 우리 시스템의 모든 위임 작업에 사용.

> 회사/모델 양쪽 의미로 쓰임. 도구(tool)로 분류 (다른 모델로 swap 가능하므로 person보다 tool이 정확).

## 4 wiki 프로필에 배분된 모델

[[_meta/system-design]] §0에서 결정된 모델 배분:

| 프로필 | 모델 | 용도 | 비고 |
|---|---|---|---|
| **wiki-architect** | `anthropic/claude-sonnet-4` | SCHEMA/PRD 작성, lint 규칙 | 깊은 설계에 강한 모델 |
| **wiki-curator** | `MiniMax-M3` (또는 mini) | 자동 lint, 빌드, git 운영 | 빠르고 반복 작업에 강함 |
| **wiki-writer** | `MiniMax-M3` | 콘텐츠 작성 (현재) | 한국어 + 마크다운 능숙 |
| **wiki-dashboard** | `MiniMax-M3` (예정) | UI 생성 (코드 작성) | React/TS 코드 생성 |

**현재 세션 = MiniMax-M3 + wiki-writer 프로필**.

## 우리 시스템에서의 역할

### 콘텐츠 작성 (현재 W4)
- 15페이지 작성: concept/tool/person/comparison/project/query
- [[SCHEMA]] 준수: frontmatter, wikilinks, taxonomy
- [[scripts/lint.py]] 자동 검증

### 인덱싱 (M1 운영)
- wiki.db 빌드 (build_db.py)
- lint 자동 실행 (M1 일 1회)
- log.md append

### 위임 (M2+)
- MCP 호출: wiki_search / wiki_get_page
- 다른 모델 호출 (Sonnet 필요 시 위임)

## 모델 스왑 가능성

Hermes 프로필 설정에서 모델 변경 가능:
```yaml
# ~/.hermes/profiles/wiki-writer/config.yaml
model:
  provider: minimax-oauth
  model: MiniMax-M3
```

→ 모델이 더 좋아지면 한 줄만 바꾸면 프로필 전체 업그레이드.

## 장점 / 한계

### 장점
- **한국어 자연스러움**: 위키 콘텐츠 한국어 작성에 강함
- **마크다운 문법 정확성**: frontmatter, wikilinks, 표 정확
- **속도**: 반복 작업(lint/git/빌드) 빠르게
- **도구 호출 능력**: MCP, terminal, write_file 모두 안정적

### 한계
- **장문 reasoning**: Sonnet 4 대비 약함 (필요 시 위임)
- **최신 정보**: knowledge cutoff (2026-01)
- **영어/한국어 혼용 시 한국어 우선** (의도적, 우리 vault가 한국어)

## 우리 시스템이 모델을 추상화하는 방식

→ 모델에 의존하지 않게 **스키마/툴 인터페이스로 격리**:
- [[SCHEMA]] = 모델 무관 (frontmatter, wikilinks, taxonomy)
- [[scripts/build_db.py]] = 모델 무관 (markdown → SQLite)
- [[scripts/lint.py]] = 모델 무관 (9개 규칙)

**원칙**: 모델은 **인터페이스 구현체**, 스키마는 **인터페이스 자체**.
→ 모델 바꿔도 데이터/규약 그대로 유지.

## 결정 사항

| # | 결정 | 선택 |
|---|---|---|
| D-MODEL-1 | 위임에 사용할 메인 모델 | MiniMax-M3 (빠르고 한국어 강함) |
| D-MODEL-2 | architect 모델 | Sonnet 4 (깊은 설계, 비용 OK) |
| D-MODEL-3 | 모델 swap 방식 | Hermes 프로필 config 한 줄 변경 |

## 관련

- [[content/hermes-agent]] — 이 모델을 호출하는 플랫폼
- [[content/llm-wiki]] — LLM Wiki 패턴의 LLM
- [[_meta/system-design]] — 모델 배분 결정 (D-MODEL-*)
- [[_meta/wiki-persona]] — 페르소나별 활용 맥락
