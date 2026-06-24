---
title: Hermes Agent
created: 2026-06-25
updated: 2026-06-25
type: tool
tags: [tool, ai, system, dashboard]
sources: [_meta/system-design.md]
confidence: high
---

# Hermes Agent

## 정의

> [Hermes Agent](https://hermes-agent.nousresearch.com/docs) — Nous Research의 AI 에이전트 플랫폼.
> CLI + 프로필 기반 멀티 모델 오케스트레이션 + cron/skills/MCP 통합.

핵심: 단순 채팅이 아니라 **능동적 에이전트** — 도구 호출, 스케줄링, 위임, 메모리.

## 4 wiki 프로필

Hermes의 프로필 시스템으로 **역할 분리**:

| 프로필 | 역할 | 핵심 책임 |
|---|---|---|
| **wiki-architect** | 설계자 | SCHEMA/RULES/PRD 작성, lint 규칙 정의, taxonomy 진화 |
| **wiki-curator** | 운영자 | build_db 실행, index 갱신, log.md 관리, lint 자동화, git commit |
| **wiki-writer** | 작성자 | 콘텐츠 페이지 작성 (ingest, 비교, 개념 정리) |
| **wiki-dashboard** | 뷰어 | (구현 예정) read-only 검증, 그래프 미리보기 |

→ 각 프로필은 **자기 prompt + skills + memories** 분리 → 작업 영역 충돌 없음.
→ 위임 시 `cross_profile=True` 명시 필요 (기본은 거부).

## 우리 시스템에서의 역할

**위임 그래프**:
```
[사용자: Jake]
    ↓ Telegram / CLI / 수동
[wiki-orchestrator] ←── Master (오케스트레이션)
    ├── wiki-architect  (M0, W2)
    ├── wiki-curator    (W2, M1 운영)
    ├── wiki-writer     (W3, W4 콘텐츠)
    └── wiki-dashboard  (M3 이후)
```

**wiki-writer 프로필에서 본 작업**:
- 콘텐츠 15페이지 작성 (현재 W4 작업)
- [[scripts/build_db.py]] + [[scripts/lint.py]] 실행
- git commit + log.md 갱신

## MCP 통합 (M2)

Hermes는 MCP 클라이언트이기도 함 → [[content/mcp-server]] 호출 가능:

```
[Hermes profile: wiki-writer]
    ↓ wiki_search / wiki_get_page
[MCP server: wiki-mcp:8765]
    ↓ SQLite
[wiki.db]
```

**핵심**: 위임받은 subagent가 MCP로 wiki.db에 직접 접근 (별도 빌드 불필요).

## Skills 시스템

Hermes의 `skill_view`/`skill_manage`로 **절차 메모리** 저장:
- 자주 쓰는 워크플로 (예: `wiki-build-and-lint`)
- 발견한 함정 / 우회 방법
- 도메인별 best practice

→ 동일 작업 2회 이상 시 skill로 등록 → 3회째부터 시간 단축.

## Cron / 자동화

`cronjob` 도구로 주기 작업:
- 일 1회: `wiki-curator` 자동 lint
- 분기 1회: DR 복구 훈련 (Cron + runbook)
- 시간당: git push (M5 백업)

## 우리 시스템과 통합

| Hermes 기능 | 우리 활용 |
|---|---|
| **Profiles** | 4 wiki 프로필 분리 |
| **Skills** | wiki-build-and-lint 등 절차 저장 |
| **Cron** | 자동 lint, 자동 백업 (M5) |
| **MCP client** | 위임 subagent가 wiki.db 접근 |
| **Telegram delivery** | 결과 자동 보고 |
| **computer_use** | (선택) 외부 UI 자동화 |

## 왜 Hermes인가 (vs 다른 에이전트)

| 후보 | 장점 | 단점 | 결정 |
|---|---|---|---|
| **Hermes** | 프로필, MCP, cron, skills | 비교적 신생 | ✅ 채택 |
| Claude Code | 강력, 성숙 | 프로필/오케스트레이션 약함 | ❌ |
| Codex CLI | 강력, GitHub 통합 | 1프로필만 | ❌ |
| 자체 LangChain | 완전 통제 | 운영 부담 | ❌ |

## 한계 / 주의

- Hermes 자체 spec/도구 변화에 의존
- 모델 라우팅 (provider/model) 변경 가능 → 결과 재현성 주의
- cross-profile write 가드 — 명시적 opt-in 필요

## 관련

- [[content/llm-wiki]] — Hermes가 운영할 LLM Wiki
- [[content/mcp-server]] — Hermes가 호출할 MCP
- [[content/minimax-m3]] — 우리 위임에 쓰이는 모델
- [[_meta/system-design]] — 우리 시스템 전체 설계
- [[_meta/wiki-persona]] — 페르소나별 활용
