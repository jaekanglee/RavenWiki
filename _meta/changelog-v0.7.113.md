# Changelog v0.7.113 — Agent `type: issue` 자율 발행 + status 머신 fallback (ADR-2026-07-08)

> **BLUF**: PWW §7.1의 type: issue "agent 발의만"을 v0.7.106 정책에서 v0.7.113 "agent 자율 draft 발행 + 7일+ 자동 current"으로 확장. status 머신을 4종 → 5종 (`draft` 추가)하고, lint #13이 draft 7일+ 자동 current 머신을 구현. NewIssueButton에 `actor="human" | "agent"` prop 추가하여 사람/agent 모두 발행 가능.

이전 changelog: `_meta/changelog-v0.7.112.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | type: issue agent 자율 발행 + status 머신 5종 |
| 범위 | v0.7.113 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | 사용자 명시: "최대한 에이전트의 자율성을 좀 높이고 싶은데" + "주요한 시나리오는 ㄹ이래" |
| 종료 트리거 | tsc 통과 + vitest 12 passed + lint 머신 4 passed + vite build 통과 |
| 정책 변경 | **1** — PWW §7.1 type: issue 권한 (ADR 필수, 본 변경) |
| ADR 동반 | **1** — `_meta/decisions/adr-2026-07-08-agent-issue-autonomy.md` |

## §1 — 무엇을 했나

### 1.1 ADR-2026-07-08 — 정책 합의

`type: issue` 권한을 4단계에서 5단계로 확장:

| 단계 | 상태 | 의미 |
|---|---|---|
| 발행 | status=draft | 사람/agent 공통, ADR 본 변경 |
| 7일+ + audit clean | status=current | lint #13 자동 머신 (사람 turn 불요) |
| 사람 명시 turn | draft→current / draft→archived / current→draft | 즉시 전이 |
| severity=high | 사람 큐 노출 | Dashboard 큐 |
| lint #18 audit 위반 | 일시 차단 + 사람 review | north star "원문 보존" 보호 |

### 1.2 SCHEMA / PWW / Lite bootstrap 갱신

`raven/core/templates/agent/SCHEMA.md`:
- §type 매트릭스: `issue` 행 — "✅ 자율 (status=draft default, 7일+ 자동 current, ADR-2026-07-08)"
- §status 머신: 4종 → 5종 (`draft` 추가)
- §전이 규칙: `draft → current` 자동 머신 추가
- §issue 본문 템플릿: status 머신 안내 추가

`raven/core/templates/agent/PROJECT-WORKFLOW.md`:
- §7.1 type 권한 표 갱신
- §6.5 #4 orphan / #7 stale / #8 200줄: "발의만" → "자율 발행 (status=draft)"
- §7.1 매트릭스 주석: "사람 운영자만" → "사람/agent 공통 발행"

`~/Raven/raven-dev/_meta/agents/{SCHEMA,PROJECT-WORKFLOW}.md`: Lite bootstrap 동기화 완료.

### 1.3 NewIssueButton actor 모드 (Dashboard)

`dashboard/src/components/NewIssueButton.tsx`:
- `actor?: "human" | "agent"` prop 추가 (default: "human")
- 발행 시 `tags: [issue, severity, kind, "draft"]` 자동 주입
- 발행 body에 `<!-- actor=... published_at=... -->` audit stamp
- tooltip / aria-label이 actor 모드별 분기 ("사람 운영자" / "agent 자율")

### 1.4 lint #13 draft 자동 current 머신

`raven/core/lint.py`:
- `_auto_promote_draft_issues(vault)` 신규 — type=issue + status=draft + created+7일+ → status=current 자동 승격
- `_audit_violation_clean(vault)` 가드 — lint #18 audit 위반 시 자동 승격 차단
- `_swap_status_in_fm(text, old, new)` frontmatter status swap 헬퍼
- `_append_agent_stamp(text, line)` agents: stamp 추가 헬퍼
- `_append_log_audit(vault, slug, action)` log.md audit append 헬퍼
- `run_all()` return에 `draft_promoted: int` 추가

## §2 — 변경 안 한 것

- `type: decision` (ADR) 권한 = 사람 1차 그대로
- `_meta/system/`, `_meta/agents/` 직접 write = ❌ (Tier 1 가드 유지)
- raw/ 자율 write = ❌ (ADR-2026-07-02 유지)
- `wiki_delete` / `wiki_rename` admin 도구 = 사람 운영자 전용 그대로

## §3 — 검증

```text
tsc -b                              → 통과
vitest 12 passed
  NewIssueButton.actor-mode (4) + NewIssueButton (5) + RawPanel (2) + Sidebar (1)
pytest tests/test_lint_draft_autopromote.py  → 4 passed (신규 머신 검증)
vite build                          → 993 modules, 1.84s
```

회귀 0건. 기존 `test_lint_log_size.py` 2개 실패는 **기존 실패** (git stash 검증, P74 패턴) — 본 패치 무관.

## §4 — 4 저장 신호

| 신호 | 충족 |
|---|---|
| 재사용성 | 모든 vault 공통 status 머신 (current/draft/stale/contested/archived) |
| 인수인계 | 사람/agent 권한 경계가 코드 + PWW + SCHEMA 3중 박힘 |
| scope/provenance | actor metadata 자동 stamp + log.md audit append |
| 실패/리스크 기록 | lint #18 audit 위반 시 자동 승격 차단 + 7일 유예 + 사람 turn 3중 안전망 |
