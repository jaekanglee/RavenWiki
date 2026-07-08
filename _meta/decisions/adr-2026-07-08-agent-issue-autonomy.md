---
title: Agent `type: issue` 자율 발행 + status 머신 fallback 승격
created: 2026-07-08
type: rule
tags: [adr, agent-autonomy, status-machine, layer-2, policy]
audience: agent
confidence: high
status: current
related:
  - _meta/decisions/adr-2026-07-06-stale-update-isolate-loop.md
  - _meta/decisions/adr-2026-07-02-raw-folder-human-first.md
aliases: [adr-agent-issue-autonomy]
---

# ADR: Agent `type: issue` 자율 발행 + status 머신 fallback 승격

> **BLUF**: `type: issue` 권한을 v0.7.106 "agent 발의만"에서 v0.7.113+ "agent 자율 draft 발행 + status 머신 fallback 승격"으로 확장한다. 사용자 north star (Layer 2 — "사람 curation은 옵션, 전제조건 ❌")와 기존 합의 (자동 4신호 기반 자율 write, 사람 명시 = override)를 type: issue에도 일관 적용. 사람 review는 명시 트리거 / draft 누적으로만 개입.

## 1. 맥락 (Context)

### 1.1 사용자 north star (v0.7.107+ 합의)

> "에이전트 자신의 cwd 작업 과정·산출물·인사이트를 vault에 위키화해서, 다음 세션·다음 에이전트가 즉시 활용 가능한 형태로 영구 위임. 사람 curation은 옵션일 뿐, 전제조건이 아니다."

### 1.2 사용자 운영 시나리오 (2026-07-08 명시)

> "Telegram turn → agent RAG 검색 + 계획 + 자율 실행 → 작업 중 vault 정리 필요 → 다음 turn에 활용. 사람 turn은 **의도/결정**이지 매번 gate가 아님."

### 1.3 기존 ADR / 정책과의 정합

- **ADR-2026-07-06**: stale/contested/archived status 머신 4종 (`status: current|stale|contested|archived`).
- **v0.7.106 §7.1**: type: issue = "발의만". 이건 agent가 inbox를 채우면 사람 curation 부담이 폭증한다는 보수적 해석.
- **v0.7.111 PWW §0.5**: "사람 curation은 옵션" + v0.7.104 ADR threshold = "policy/permission/data-contract 변경 = ADR" → 본 ADR로 처리.

### 1.4 충돌 분석

| 권 | 내용 | 충돌? |
|---|---|---|
| §7.1 (v0.7.106) | type: issue = agent 발의만 | ✅ 해소 |
| §0.5 (Layer 2 north star) | 사람 curation 옵션 | ✅ 정합 |
| 사용자 운영 시나리오 | 매 turn 사람 gate ❌ | ✅ 정합 |
| 사용자 메모리 "Decision fatigue" | 묶음 종착 = hotfix, 사이클 = 명시 요청 시 ACT+report | ✅ 정합 |
| 사용자 메모리 "Agent write trigger" | §3 4신호 ≥1 OR lint 자동 = 자율 write | ⚠️ 일관 (issue 제외였음) |

## 2. 결정 (Decision)

### 2.1 새 정책 — `type: issue` 자율 발행 + fallback 승격

```yaml
# 발행 (agent / 사람 공통)
type: issue
status: draft               # 발행 시 default = draft (사람/agent 무관)
tags: [issue, severity, kind, draft]   # draft 자동 포함
created: YYYY-MM-DD
last_verified: YYYY-MM-DD   # 발행/검증 시 stamp
```

```yaml
# 승격 (status 머신 §1.1)
draft → current:   사람 명시 turn ("이거 final로") OR
                    7일+ draft 유지 + lint #18 audit 통과 → 자동 current
draft → archived:  사람 명시 turn (현재 backlog 정리)
current → stale:   wiki_stale_detect 90일+ (기존 v0.7.106 머신)
current → contested: lint #5 모순 발견 시 양쪽 cross-link
archived → current: 사람 승인 필수 (v0.7.106 정책 유지)
```

### 2.2 사람 개입 트리거 (3종)

```yaml
# 1. 명시 turn
"이 이슈 final로 올려" / "이거 백로그 정리해" → 즉시 status 전이

# 2. severity=high 자동 큐
agent 발행 시 severity=high → Dashboard 큐에 노출 (사람 review 권고)
사람이 보고 final/archive 결정

# 3. audit violation (lint #18)
30일 단일 actor 5회+ / 단일 path 10회+ permission_denied
→ 일시적 agent 차단 + 사람 review 게이트
```

### 2.3 백엔드 contract 변경

```yaml
# raven/core/lint.py — #13 cognitive governance 확장
type: issue + status: draft + created+7d < now + lint #18 clean
  → 자동 status: current 전이 + log.md audit record

# raven/api/server.py
POST /api/vaults/{name}/pages  # type=issue 자유 허용 (기존 PWW §7.1 가드 제거)
  payload.type = "issue"        # 200 OK
  자동 frontmatter:
    status: draft
    tags: [issue, severity, kind, draft]
```

### 2.4 SCHEMA / PWW 갱신

- `_meta/SCHEMA.md` §type 9종 매트릭스 — issue 행 갱신
- `_meta/SCHEMA.md` §issue 본문 템플릿 — `## 상태`에 status 머신 4종 안내 추가
- `raven/core/templates/agent/SCHEMA.md` — 동일 (Lite bootstrap SOT)
- `raven/core/templates/agent/PROJECT-WORKFLOW.md` §7.1 — type: issue 행 갱신
- `_meta/agents/SCHEMA.md` + `_meta/agents/PROJECT-WORKFLOW.md` — Lite bootstrap 동기화
- `dashboard/src/components/NewIssueButton.tsx` — agent 호출 가능 export 추가 + 기본 status=draft

### 2.5 변경 안 하는 것

- `type: decision` (ADR) 권한 = **사람 1차, agent 보조** 그대로 (SCHEMA L99 권고 유지)
- `_meta/system/`, `_meta/agents/` 직접 write = ❌ (Tier 1 가드 유지)
- raw/ 자율 write = ❌ (ADR-2026-07-02 유지)
- `wiki_delete` / `wiki_rename` admin 도구 = 사람 운영자 전용 그대로

## 3. 결과 (Consequences)

### 3.1 긍정

- Layer 2 north star 일관성 회복 (모든 type에서 사람 curation 옵션)
- Telegram turn 체감 latency 감소 (사람 gate 제거)
- agent backlog 자연 누적 + draft 자동 current로 stale 방지
- status 머신 4종을 모든 type에 일관 적용 (v0.7.106 stale 루프 인프라 활용)

### 3.2 부정 / 리스크

- 사람 inbox가 agent 발행으로 채워질 수 있음 → **status: draft가 inbox 역할** (사람이 무시해도 current 자동 승격됨)
- 자동 승격 7일 window는 사람 운영 부재 시 문제 누적 가능 → lint #18 + severity=high 큐로 보완
- status 머신이 4종 (current/stale/contested/archived)에서 5종 (draft 추가)으로 늘어남 → PWW §1.1 status 머신 표 갱신 필요

### 3.3 회귀 가드 (3종)

```yaml
# 1. SCHEMA.md §issue 매트릭스 — agent 자율 ✅ 명시
# 2. PROJECT-WORKFLOW.md §7.1 — type: issue ✅ 자유 (decision ❌ 유지)
# 3. lint #13 — type=issue + status=draft + 7일+ 자동 current 머신 구현
```

## 4. 다음 단계

```yaml
1. _meta/SCHEMA.md 갱신 (즉시)
2. raven/core/templates/agent/{SCHEMA,PROJECT-WORKFLOW}.md 갱신 (즉시)
3. _meta/agents/* 동기화 (meta sync --force)
4. raven-dev vault에 type: issue 자가 사용 페이지 발행 (회귀 가드)
5. Dashboard NewIssueButton — status=draft default + agent 호출 가능 export
6. raven/core/lint.py — #13 draft→current 자동 머신 (lint #18)
7. raven/api/server.py — type=issue 자율 write 가드 제거 (200 OK)
8. _meta/changelog-v0.7.113.md
9. 두-repo commit
