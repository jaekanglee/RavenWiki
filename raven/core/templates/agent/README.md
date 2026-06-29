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

```bash
# 1. 최근 활동 (무엇이 있었나)
raven log list --tail 5

# 2. 최근 결정/lesson (절대 반복 ❌)
raven page ls --tag <team> --type rule

# 3. 관련 journal (handoff 어디까지 됐나)
raven page get content/journal/<team>/<최근>

# 4. contradictions (모순된 결정 있나)
raven page ls --tag <team> --has-contradictions
```

→ 위 결과를 작업 컨텍스트에 포함시켜 시작. **vault = 외부 메모리**.

---

## 한 줄 요약

> **당신의 기억은 휘발성, vault는 영구적.**
> **결정 / lesson / journal이 생기는 순간 = 당신이 vault에 write해야 하는 순간.**
> **scope 밖 read/write 절대 ❌. 사용자에게 항상 "어디 저장됐는지" 보고.**

---

## 외부 위임 backend (선택, v0.6.34+)

`agent/README.md` 만으로 부족하면 다른 LLM의 cross-check을 위해 외부 CLI에 위임 가능. **사용자 명시 또는 Gemini-family cross-check 시점에만**.

| Backend | 특징 | 호출 예 |
|---|---|---|
| **Codex CLI** (`codex`) | JSON envelope, --max-turns | `terminal(command="codex -p '...'", workdir=...)` |
| **Antigravity CLI** (`agy`) | plain text only, --print-timeout 5m | `terminal(command="agy -p '...'", workdir=...)` |

> 기본값은 직접 작업. **사용자 명시 / Gemini cross-check 시점에만** 다른 backend 시도. **wrap-up 단계 fix 침습 금지** — 분석만, 패치는 orchestrator에게 보고.
