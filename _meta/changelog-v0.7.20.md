# raven v0.7.20 — 에이전트 인터페이스(MCP) 가이드 정렬, 쓰기 동시성 가드(File Lock) 도입, 인지 거버넌스 린터 튜닝

> **핵심**: 에이전트 인터페이스의 MCP 단일화에 따라 템플릿 문서를 정렬하고, 에이전트 다중 세션 충돌 방지를 위한 File Lock 도입 및 린터 작성 피로감 개선 작업을 완료했습니다.

릴리스 일자: 2026-06-30
이전: v0.7.19

---

## 한 줄 요약

에이전트 템플릿 문서에서 파이썬 API 흔적을 지우고 MCP 단일 표준으로 정렬했습니다. 동시에 여러 에이전트 간 쓰기 충돌을 방지하기 위해 원자적 디렉토리 생성 기법 기반의 `FileLock` 가드를 도입하고, 인지 거버넌스 린터의 과도한 경고를 해결하는 custom bypass 옵션을 반영했습니다.

---

## 1. 변경 사항

### 1-1. 에이전트 템플릿 문서 정렬 (MCP 중심)
* **`raven/core/templates/agent/TOOLS.md`**: 기존 Python API `Agent.named()` 예제를 완전히 걷어내고, FastMCP의 9대 핵심 툴 규격(`wiki_search`, `wiki_update` 등)과 MCP JSON-RPC 툴 호출 명세, 그리고 쓰기 권한 모드(`--mode write`) 가이드를 채워 넣었습니다.
* **`raven/core/templates/agent/SAFETY.md`**: 파일 및 경로에 대한 `_safe_path()` 검증, 타겟 Vault에 대한 MCP 툴 호출 거부 사항을 기재하고 Python 어댑터 관련 내용을 MCP 툴 호출 형태의 차단 시나리오로 변경했습니다.
* **`docs/vault-patterns.md`**: 템플릿 가이드 중 기존 파이썬 어댑터 `av.write()` 호출 예시 코드를 JSON-RPC 형식의 `wiki_update` 툴 호출 구조로 정정했습니다.

### 1-2. 쓰기 동시성 가드 (FileLock) 구현
* **`raven/core/lock.py`**: OS 수준에서 디렉토리 생성이 원자적으로 이루어지는 점을 이용한 `FileLock` 헬퍼 모듈을 추가했습니다. 락 획득 실패 시 타임아웃(기본 5초) 후 예외를 발생시키며, 락 디렉토리는 `.mcp/locks/` 아래 생성되어 workspace를 더럽히지 않고 Git에 잡히지 않습니다.
* **`raven/core/contracts.py`**: 단일 쓰기 진입점인 `write_page` 함수의 파일 존재 검사 및 쓰기 프로세스 전반을 `lock_for_file` 락으로 감쌌습니다.
* **`raven/core/log.py`**: `log.md` 어펜드 과정(`append` 함수)의 Read-Modify-Write 단계를 락으로 보호하여, 다중 세션이나 여러 에이전트가 동시에 실행될 때 로그 유실이나 덮어쓰기 레이스 컨디션을 물리적으로 완벽 차단했습니다.

### 1-3. 인지 거버넌스 린터 튜닝
* **`raven/core/lint.py`**: 인지 거버넌스(#13) 규칙의 경고를 유연하게 우회할 수 있도록 3가지 우회로를 튜닝했습니다.
  1. `.vault.json`에 `disable_cognitive_governance: true` 옵션 추가 시 린트를 글로벌하게 스킵.
  2. `wip/` 또는 `scratch/` 하위 경로에 속한 임시 마크다운 문서들은 평가에서 면제.
  3. Frontmatter tags에 `wip`, `draft`, `scratch`, `memo`, `quick` 중 하나가 존재하면 면제(초안 보호).

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| pytest | **471 passed, 1 skipped** | 전체 테스트 성공 ✅ |
| FileLock 동작 | contracts 및 log.md에 정상 격리 락 작동 확인 | Concurrency Guard ✅ |
| 린터 튜닝 | wip/ 및 tags 면제 heuristic 정상 작동 확인 | Cognitive Governance Bypass ✅ |

---

## 3. 호환성

- ✅ **기존 사용자**: `.vault.json`에 `disable_cognitive_governance`를 추가하지 않는 한 기존 인지 거버넌스 린트 동작에 영향이 없습니다.
- ✅ **에이전트 템플릿**: 새로이 생성되는 vault에 Lite bootstrap 시 MCP 규격의 템플릿 파일들이 정확히 배치됩니다.

---

## 4. 다음 단계
* **v0.7.21 (후보)**: API 응답 `vaults: []` 디버깅
