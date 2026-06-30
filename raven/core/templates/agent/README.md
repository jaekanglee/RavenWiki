---
title: Raven Agent Guide — 진입점
created: 2026-06-25
updated: 2026-06-25
type: rule
tags: [system, meta, raven, agent, guide]
audience: agent
confidence: high
---

# Raven Agent Guide — 진입점

> **당신은 raven vault에서 일하는 LLM 에이전트입니다.**
> 이 문서는 다른 `agent/*` 문서의 **진입점**입니다. 작업 시작 전 순서대로 읽으세요.

## 분리 원칙 (왜 이 디렉토리가 따로 있나)

raven vault는 **두 종류의 독자**를 위한 규칙이 분리되어 있습니다:

| 디렉토리 | 대상 | 내용 톤 |
|---|---|---|
| `_meta/system/` | 사람 + raven 코드 (lint/build) | "시스템은 이렇게 동작한다" |
| `_meta/agent/` (← 여기) | LLM 에이전트 | "당신은 이렇게 행동해야 한다" |

**혼용 ❌**. agent 지침이 lint 룰로 잘못 적용되거나, 시스템 규약이 agent 행동으로 새는 일 절대 금지.

→ 분리 결정 문서: `content/journal/2026-06-25-raven-guidelines-split-decision.md`

---

## 먼저 읽을 것 (1회)

| 순서 | 파일 | 내용 |
|---|---|---|
| 1 | **이 README.md** | 지금 보고 있는 것 — 전체 그림 |
| 2 | [TOOLS.md](TOOLS.md) | Agent / CLI / HTTP 인터페이스 사용법, scope 규칙 |
| 3 | [WORKFLOW.md](WORKFLOW.md) | 트리거별 행동, Phase 게이트, 부트스트랩 패턴 |
| 4 | [SAFETY.md](SAFETY.md) | 절대 안 되는 것, scope 우회 금지, vault 외부 read/write 금지 |

---

## 작업 시작 시 (매 세션) — 4-step orientation

에이전트는 작업을 개시할 때, 직접 CLI 서브프로세스를 띄우거나 파일에 접근하기보다 **MCP 툴을 호출**하여 Vault의 맥락을 동기화해야 합니다.

1. **최근 활동 파악**: `wiki_log(tail_n=5)` 툴을 호출해 최근 변경 내역을 읽습니다.
2. **최근 결정/Lesson 확인**: `wiki_search`를 사용해 해당 프로젝트/팀의 최신 `rule` (결정/교훈) 페이지들을 검색하고 핵심 내용을 파악합니다.
3. **Journal 인수인계 확인**: `wiki_get_page` 툴로 최근 작성된 `journal` 페이지를 조회하여 이전 작업 현황을 파악합니다.
4. **모순 검사**: `wiki_lint` 툴을 실행하여 contradictions(모순) 등으로 플래그된 린트 경고가 없는지 사전 검사합니다.

→ 위 동기화 결과를 작업 컨텍스트에 반드시 포함시켜 영구 지식(Vault)과 메모리를 일치시킵니다.

---

## 한 줄 요약

> **당신의 기억은 휘발성, vault는 영구적.**
> **새로운 지식을 정의(Write)하기 전에 이미 컴파일된 지식이 없는지 먼저 적극적으로 검색(Read)하여 재사용하십시오. (Read-heavy, Write-rare)**
> **결정 / lesson / journal이 생기는 순간 = 당신이 vault에 write해야 하는 순간.**
> **scope 밖 read/write 절대 ❌. 사용자에게 항상 "어디 저장됐는지" 보고.**

---

## 외부 LLM cross-check (선택, v0.6.36+)

`agent/README.md` 만으로 부족하면 다른 LLM의 cross-check을 위해 외부 CLI에 위임 가능. **어떤 vendor든 동일하게 다룬다 — vendor 이름 자체를 표기하지 않는다 (LLM Wiki 개념 추상화)**.

| Backend (추상) | 특징 | 호출 예 |
|---|---|---|
| **외부 LLM CLI** | vendor 무관. JSON envelope / plain text / markdown 모두 vendor 구현에 따름 | `terminal(command="<llm-cli> -p '...'", workdir=...)` |

> 기본값은 직접 작업. **사용자 명시 / cross-check 요청 시점에만** 외부 LLM 호출. **wrap-up 단계 fix 침습 금지** — 분석만, 패치는 orchestrator에게 보고.
>
> **north star 준수 (v0.6.36+)**: 어떤 vendor가 와도 동일하게 동작. vendor 이름 자체를 정책 문서에 박지 않는다 (LLM Wiki 개념 추상화).
