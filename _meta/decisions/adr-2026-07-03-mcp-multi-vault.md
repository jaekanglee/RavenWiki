---
adr_id: adr-2026-07-03-mcp-multi-vault
title: MCP 서버 단일-볼트 고정 제거 — 볼트별 인자로 멀티볼트 서빙
status: accepted
created: 2026-07-03
deciders: assistant (제안) · user (승인)
related:
  - adr-2026-06-27-mcp-namespace.md (MCP 패키지 네임스페이스 정리 — 본 ADR의 전신 리팩터)
  - raven/api/server.py L52-59 (_vault_or_404 — 본 ADR이 그대로 미러링한 패턴)
  - raven/mcp/cli.py (register_tools, main)
  - raven/mcp/resources.py (register_resources)
  - raven/mcp/tools/__init__.py (resolve_vault_path)
---

# ADR: MCP 서버 단일-볼트 고정 제거 — 볼트별 인자로 멀티볼트 서빙

## Context (배경)

### 문제

`raven/api/server.py`는 모든 라우트가 `/api/vaults/{name}/...` 형태로 볼트를 매 요청마다 파라미터로 받는 완전한 멀티볼트 구조다 (`_vault_or_404(name)` → registry 조회). 반면 `raven/mcp/cli.py`의 `register_tools()`는 서버 프로세스 시작 시 `_resolve_vault()`로 볼트 하나를 딱 고정해서 `VaultContext`를 클로저로 만들고, 모든 툴 호출이 그 하나의 볼트만 바라봤다.

두 레이어가 같은 하부 배관(`raven.core.registry`, `VaultContext`, per-vault lock)을 쓰면서도 노출 방식만 달랐던 것 — API는 멀티볼트로 진화했지만 MCP는 예전 "임베디드 단일 볼트" 가정에 머물러 있었다.

### 실무 영향

볼트를 여러 개 운영하려면:
- 볼트마다 별도 포트로 별도 MCP 서버 프로세스를 띄워야 함
- 새 볼트를 만들 때마다 에이전트 쪽 `.mcp.json`에 새 엔트리를 수동 등록해야 함

`docker-compose.yml`의 `mcp-http` 서비스는 이미 `WIKI_VAULTS_DIR=/vaults`(볼트 루트 전체)를 마운트하고 있었고, `docker-entrypoint.sh`도 `--vault` 플래그를 넘기지 않고 있었다 — 즉 **인프라는 이미 멀티볼트를 전제로 구성돼 있었고, Python 코드만 못 따라간 상태**였다.

## Decision (결정)

`raven/mcp/cli.py`의 9개 MCP 툴과 `raven/mcp/resources.py`의 5개 리소스 모두 첫 번째 인자로 `vault: str`(registry에 등록된 볼트 이름)을 받도록 바꾸고, 매 호출마다 `raven.core.registry`에서 해당 볼트를 조회해 새 `VaultContext`를 만든다. `--vault` CLI 플래그와 `_resolve_vault()`는 제거한다.

`mode`(read/write/admin)는 볼트별이 아니라 **서버 프로세스 전체의 접근 레벨**로 유지한다 — API처럼 볼트마다 다른 mode를 주는 기능은 이번 스코프에 없다.

```python
# Before — 서버 시작 시 한 번, 모든 툴이 공유
ctx = VaultContext(vault=vault, mode=mode)
def wiki_search(query: str, top_k: int = 10) -> list[dict]:
    return db_module.search_fts(query=query, top_k=top_k, vault=vault)

# After — 매 호출마다, vault 인자로 라우팅
def wiki_search(vault: str, query: str, top_k: int = 10) -> list[dict]:
    return db_module.search_fts(query=query, top_k=top_k, vault=resolve_vault_path(vault))
```

`raven/mcp/tools/read.py`, `write.py`는 변경하지 않았다 — 이 모듈들의 9개 함수는 이미 `ctx: Optional[VaultContext] = None`을 받는 구조라, 문제는 오직 `cli.py`가 `ctx`를 서버 시작 시 한 번만 클로저로 고정했던 부분뿐이었다.

### 대안 검토

| 안 | 채택 여부 | 이유 |
|---|---|---|
| **볼트 이름을 툴 인자로 (채택)** | ✅ | API의 `{name}` 패턴과 동일, 하부 배관 이미 존재, 최소 변경 |
| 볼트마다 별도 프로세스/포트를 자동 관리 | ❌ | 여전히 프로세스 N개 필요, `.mcp.json` 엔트리도 볼트 수만큼 필요 — 문제를 자동화할 뿐 구조적으로 해결 안 함 |
| MCP 리소스 URI만 멀티볼트, 툴은 유지 | ❌ | 툴이 실제 read/write를 수행하는 표면인데 여기가 여전히 단일 볼트면 문제 미해결 |

## Consequences (결과)

### Positive

- ✅ MCP 서버 프로세스 1개가 registry에 등록된 모든 볼트를 서빙 — 새 볼트 추가 시 서버 재시작/재설정 불필요
- ✅ `.mcp.json` 등록이 평생 한 번으로 줄어듦 (포트/커맨드가 볼트마다 안 바뀜)
- ✅ `docker-compose.yml`, `docker-entrypoint.sh` 변경 불필요 — 이미 멀티볼트 전제로 구성돼 있었음
- ✅ `read.py`/`write.py`, 기존 테스트 5종 무변경 — 이 모듈들은 이미 `ctx` 주입 구조였음

### Negative / Breaking Change

- ⚠️ **하위 호환 없음**: 기존에 `wiki_search(query="x")`처럼 `vault` 없이 호출하던 에이전트 설정은 필수 인자 누락으로 실패한다. 마이그레이션 경로: 모든 호출에 `vault="<등록된 이름>"` 추가.
- ⚠️ 여러 볼트가 한 프로세스에 물려 있으므로, 에이전트가 `vault` 이름을 잘못 넘기면 의도치 않은 볼트를 건드릴 수 있다 (기존엔 프로세스 자체가 물리적으로 분리돼 있어 원천 차단됐던 리스크). API 레이어도 이미 안고 있는 동일한 리스크라 새로운 종류의 문제는 아니다.
- ⚠️ 존재하지 않는 볼트 이름 호출 시 `ValueError`(FastMCP가 `ToolError`로 감쌈)로 실패 — 등록된 볼트 목록을 메시지에 포함해 에이전트가 스스로 정정 가능하게 함.

### Risks

| 위험 | 완화 |
|---|---|
| 외부에 이미 배포된 `.mcp.json` 설정이 구 시그니처를 호출 | README.md CLI/툴 시그니처 표 갱신, 본 ADR로 breaking change 명시 |
| `mode` 파라미터명이 `wiki_ingest`의 자체 `mode`(auto/force) 인자와 충돌 | `register_tools` 내부에서 `permission_mode = mode`로 별칭 지정 후 클로저에서 `permission_mode`만 참조 |
| 신규 라우팅 로직 무테스트 | `tests/test_mcp_multi_vault.py` 신규 추가 — 2개 임시 볼트로 툴/리소스 라우팅 + 미등록 볼트 에러 메시지 검증 |

## Verification

- 기존 `raven/mcp/tests/`, `tests/test_mcp_concurrency.py`, `tests/test_mcp_write_provenance.py`, `tests/test_v0_7_7_mcp_accurate.py`, `tests/test_v0_7_8_mcp_only_for_agents.py` — 전부 무회귀 (실제 로직은 `read.py`/`write.py`에 있고 그쪽은 미변경).
- 신규 `tests/test_mcp_multi_vault.py` 4종 — 같은 툴을 서로 다른 `vault` 이름으로 호출했을 때 올바른 볼트로만 라우팅되는지, 미등록 볼트 이름에 등록된 볼트 목록을 포함한 에러가 나는지 검증.
