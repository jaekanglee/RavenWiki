---
title: Raven Contract and User Agent Policy Boundary
created: 2026-07-14
type: rule
tags: [rule, agent, workflow, mcp]
confidence: high
---

# Raven Contract and User Agent Policy Boundary

> **결정:** Raven은 기술 계약과 안전장치만 소유하며, vault 운영·에이전트 역할·작업 위임 정책은 운영자가 독립적으로 소유한다.

## 맥락

기존 Lite bootstrap의 `PROJECT-WORKFLOW.md`는 MCP·경로 보호처럼 Raven이 보장해야 할 사실과 저장 기준·큐레이션·역할 분업처럼 운영자가 정해야 할 판단을 함께 전달했다. 또한 Raven이 일반적인 루트 agent instruction 파일을 만들고 덮어쓸 수 있었다.

## 결정

- Lite bootstrap은 `SCHEMA.md`, `RAVEN-CONTRACT.md`, `log.md`만 제공한다.
- `RAVEN-CONTRACT.md`는 Markdown SoT, MCP, 권한 모드, 보호 경로, log/guide/freshness의 제품 동작만 설명한다.
- 기존 `PROJECT-WORKFLOW.md`는 읽기 전용 호환 안내이며 bootstrap·sync·freshness·diff 대상이 아니다.
- Raven은 `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`를 생성·수정·검증하지 않는다. builder는 이 파일을 페이지로 해석하지 않을 뿐이다.
- 사용자 소유 정책은 Raven이 읽거나 동기화하지 않는 별도 문서로 관리한다.

## 결과

운영자는 vault별 정책과 에이전트별 역할을 제품 업그레이드와 독립적으로 바꿀 수 있다. Raven은 다중 에이전트 운영을 지시하지 않고, 권한 모드·보호 경로·audit·idempotency 같은 협업 안전 primitives만 제공한다.

## 관련

- [[raven-contract-and-user-agent-policy-boundary]] — 이 경계의 결정 기록
- [[changelog-v0-7-173]] — 구현 변경 이력
