# raven v0.7.42 — 동시성 락(Concurrency Lock) 물리적 강제 기능 구현

> **핵심**: 여러 에이전트가 동시에 같은 보관소의 페이지에 쓸 때 발생하는 충돌과 SQLite 잠금 문제를 방지하기 위해, 기존의 권고(Advisory) 동시성 락 시스템을 실제로 쓰기를 거절(Reject)하도록 물리적인 강제 잠금(Hard Lock Enforcement)으로 강화했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.41

---

## 1. 배경 및 기획

* **상황**: 다중 에이전트 환경에서 하나의 볼트에 여러 에이전트들이 동시에 쓰기 작업을 수행하면서 마크다운 파일 덮어쓰기 충돌 및 SQLite `wiki.db` 잠금(Database locked)이 빈번하게 발생했습니다.
* **사용자 요구**: 동시성 락(Advisory Lock) 시스템을 실제로 쓰기 도구 수준에서 검증하여, 다른 에이전트가 락을 잡고 있다면 물리적으로 쓰기를 차단(Reject)하도록 제약 조건을 강화해 달라고 요청하셨습니다.
* **해결 방안**: MCP 쓰기 도구인 `wiki_update`, `wiki_ingest`, `wiki_delete`, `wiki_rename` 진입부에서 대상 슬러그가 다른 액터(Actor)에 의해 잠겨 있는지 사전에 확인하여, 잠겨 있을 경우 즉시 `lock_conflict` 에러를 반환하며 쓰기를 거절하도록 구현합니다.

---

## 2. 변경 사항

### 2-1. MCP 쓰기 도구 내 락 사전 검증 추가 (`raven/mcp/tools/write.py`)
* `wiki_update`, `wiki_delete`, `wiki_rename` 도구 내에서 해당 슬러그의 락 보유자를 검사하여 다른 에이전트가 락을 쥐고 있다면 `ok: False`, `error: "lock_conflict"` 및 락 보유자 정보(`_lock_holder`)를 즉시 반환하도록 개선했습니다.
* `wiki_ingest` 도구의 경우 복사하려는 대상 원본 경로인 `raw/<project>/<src>` 경로에 대해 동일한 락 검증 절차를 수행하도록 보완했습니다.
* `wiki_rename` 도구는 변경 전 슬러그(`old_slug`)와 변경 후 슬러그(`new_slug`) 두 곳 모두에 대해 락 충돌을 사전 확인하여 차단합니다.

### 2-2. 동시성 통합 테스트 수정 (`tests/test_mcp_concurrency.py`)
* 기존에 락 충돌 시에도 쓰기가 허용되던 'Advisory' 방식의 통합 테스트 케이스들을 물리적으로 거절(Reject) 및 락 충돌 에러가 발생하고 파일은 수정되지 않음을 검증하도록 전면 수정 및 활성화했습니다.

### 2-3. 개발 볼트 검증용 테스트 강건화 (`tests/test_v0_7_1_lite_bootstrap_surface.py`)
* 실제 볼트의 작업 수행에 따라 `log.md`가 수정(Append)되어 빌드 테스트가 실패하던 이슈를 수정하기 위해, `test_existing_vaults_synced`가 `log.md`에 대해서는 템플릿 헤더로 시작하는지만 검증하도록 `startswith` 비교식으로 보완했습니다.

---

## 3. 검증 결과

| 항목 | zone | 비고 |
|---|---|---|
| `pytest tests/` 전체 | **490 passed, 1 skipped** | 동시성 락 강제 검증 및 전체 회귀 테스트 통과 |
| `git status` 변경 목록 | **Success** | `write.py`, `test_mcp_concurrency.py`, `test_v0_7_1_lite_bootstrap_surface.py` 및 changelog 반영 |

---

## 4. 다음 단계

* 에이전트 락 획득 실패 시, 사용자에게 현재 락을 쥐고 있는 에이전트 정보와 락 해제 가이드라인을 알기 쉽게 프롬프트로 유도하는 방안 적용.
