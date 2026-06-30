# raven v0.7.22 — 템플릿(Scaffold) 리팩토링: CLI 종속성 제거 및 에이전트 MCP 지침 통일

> **핵심**: 새로 생성되는 Vault와 에이전트 가이드라인 템플릿에서 구식 CLI 명령어 하드코딩 가이드를 제거하고, MCP 툴을 직접 발견하고 사용하는 가이드라인으로 전면 쇄신했습니다.

릴리스 일자: 2026-06-30
이전: v0.7.21

---

## 한 줄 요약

Vault 생성 및 에이전트 구동 시 로드되는 템플릿들에서 CLI 기반 가이드를 MCP 툴 호출 지침으로 개편했습니다. 이를 통해 코어 엔진 버전 업데이트 시 템플릿 가이드라인이 구식이 되어 발생하는 버전 괴리(Drift) 문제를 완화하고 에이전트의 작동 신뢰도를 올렸습니다.

---

## 1. 변경 사항

### 1-1. 템플릿 내 CLI 하드코딩을 MCP 기반으로 정렬
* **`raven/core/templates/agent/README.md`**: 작업 세션 개시 시 수행하는 4-step orientation 가이드에서 기존 CLI 명령어(`raven log list`, `raven page ls`) 예시를 제거하고, `wiki_log`, `wiki_search`, `wiki_get_page`, `wiki_lint` 등의 MCP 툴 호출 지침으로 쇄신했습니다.
* **`raven/core/templates/agent/WORKFLOW.md`**: 부트스트랩 및 작업 개시 과정에 기재되어 있던 `raven` CLI 관련 예시와 SOUL.md 권장 가이드 라인을 MCP 툴 매칭 지침으로 변경했습니다.
* **`raven/core/templates/system/AGENTS.md`**: 4대 명령 키워드 매핑 테이블에 **에이전트 호출 (MCP)** 열을 추가하고, 사람은 CLI/Dashboard를 쓰고 에이전트는 MCP 툴(`wiki_update`, `wiki_ingest` 등)을 매칭하여 조작하도록 지침을 일원화했습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| pytest | **471 passed, 1 skipped** | 전체 테스트 성공 ✅ |

---

## 3. 다음 단계
* **v0.7.23 (후보)**: API 응답 `vaults: []` 디버깅
