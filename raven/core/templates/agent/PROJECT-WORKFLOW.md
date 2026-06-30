---
title: Project Workflow — 사용자 정의 작업 흐름
created: 2026-06-30
updated: 2026-06-30
type: rule
tags: [system, workflow, meta]
audience: agent
confidence: high
---

# Project Workflow — 사용자 정의 작업 흐름

> **이 문서는 vault 사용자(사람/팀)가 자기 프로젝트/팀의 작업 흐름을 자유롭게 정의하는 곳입니다.**
>
> Raven은 이 문서의 내용을 강제하지 않습니다 — 사용자가 직접 작성/유지합니다.
> 다만 **에이전트에게 "이 vault에서 작업할 때 따라야 할 규칙"**을 알려주는 표준 위치입니다.

## 작성 가이드

1. **결론부터** (BLUF) — 첫 줄에 이 팀/프로젝트의 핵심 작업 원칙 1-2줄
2. **분업** — 사람/에이전트 각각이 무엇을 하는지 (예: "사람 = 결정, 에이전트 = compile/journal")
3. **트리거** — 어떤 신호가 오면 어떤 동작을 하는지 (예: "하루 시작 → 저널 작성 → 결정 정리")
4. **금지/주의** — 이 팀에서 절대 안 되는 것 (예: "도메인 가정 ❌", "외부 시스템 write ❌")

## 참고

- vault 운영 일반 규칙: `_meta/system/AGENTS.md` ("Vault User Guide", v0.7.1+)
- 데이터 구조: `_meta/system/SCHEMA.md`
- 편집 규칙: `_meta/system/RULES.md`
- LLM Wiki +α 가이드: `docs/vault-patterns.md`

## 예시 (참고용, 사용자 팀에 맞게 수정)

```
# harumoa팀 워크플로우

## 결론
- 사람은 결정/원칙만
- 에이전트는 compile/journal/raw 정리
- 도메인 추측 ❌ (사용자에게 묻기)

## 분업
- 사람: 결정(rule), 컨셉(concept) 페이지
- 에이전트: 저널(journal) 자동, raw/ → content/ 컴파일

## 트리거
- 사용자: "X 정리해줘" → journal/concept 자동 작성
- 새 raw/ 파일 → 자동 compile (사람 confirm 후)

## 금지
- 도메인 추측 ❌
- raw/ 자동 수정 ❌
- vault 외부 write ❌
```