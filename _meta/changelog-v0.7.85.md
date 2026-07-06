# Changelog v0.7.85 — PROJECT-WORKFLOW.md 에이전트 CRUD 및 자율점검 가이드 강화 (2026-07-07)

> **BLUF**: 외부 에이전트의 안전한 CRUD 보장과 데이터 정합성 유지를 위해, `AGENTS.md`에 선언된 정책(슬러그 1:1 매핑, 저널 요약 강제화 등) 및 에이전트 자율 점검 가이드(RAG 4원칙)를 `PROJECT-WORKFLOW.md` 템플릿에 직접 이식했습니다.

이전 changelog: `_meta/changelog-v0.7.84.md`

---

## §0 — commit 후보

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| (pending) | A. PROJECT-WORKFLOW.md — 에이전트 CRUD 가이드라인 및 자율점검 가이드 보강 | 1 파일 | +30/−6 |

---

## A. PROJECT-WORKFLOW.md — 가이드라인 보강

### 진단

외부 에이전트가 볼트 진입 시 읽는 `PROJECT-WORKFLOW.md` 내에, 레이븐의 핵심 규칙인 슬러그 명명 정책과 자율 점검 가이드(RAG 4원칙)가 누락되어 있어 에이전트 자율 CRUD 시 일관성을 잃을 가능성이 있었습니다.

### 변경 사항

| 파일 | 내용 |
|---|---|
| `raven/core/templates/agent/PROJECT-WORKFLOW.md` | §1. MCP 사용 규약에 에러 처리 및 `idempotency_key` 사용 지침 추가 <br> §5. 형식 요구사항에 슬러그 1:1 매핑 및 저널 요약 3줄 이내 작성 의무화 규칙 반영 <br> §7. 일관성 체크리스트에 슬러그 일치, 요약 포함, `wiki_lint` 셀프 검증 추가 <br> §7.1 에이전트 자율 점검 가이드(RAG 4원칙) 섹션 신설 |

### 검증

- `make test` 검증 수행

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `make test` | 성공 (673 passed) |

---

## §2 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.83 | silent stale hotfix (MCP lifecycle 통합) |
| v0.7.84 | §13.2 잔여 8곳 + Edit/Delete icon SVG |
| v0.7.85 | **PROJECT-WORKFLOW.md 에이전트 CRUD 및 자율점검 가이드 강화** |
