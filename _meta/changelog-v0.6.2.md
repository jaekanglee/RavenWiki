# raven v0.6.2 — write-path 단일화 (P1-1 해소)

> **핵심**: v0.5.6 changelog §8 P1-1 약속 이행. 4곳에 분산된 write recipe를 `raven.core.contracts.write_page()` 단일 진입점으로 통합. **net -1줄, 회귀 0**.

릴리스 일자: 2026-06-27
이전: v0.6.1 (scripts/.venv 추적 해제 핫픽스)

---

## 한 줄 요약

CLI/API/Agent의 write 코드 4-step recipe (slug validate → FM merge → write → log)를 `raven/core/contracts.py` 한 함수로 통합. 진입점 3종이 단일 함수를 호출.

---

## 1. 변경 사항

### 1.1 신규 모듈: `raven/core/contracts.py`

```python
def write_page(
    vault: Vault,
    slug: str,
    content: str,
    *,
    title=None, type=None, tags=None,
    actor=None,           # dict | object (Agent provenance)
    overwrite=True,       # False → 409-style "exists" error (CLI/API create)
    normalize=True,       # False → no auto-prefix (Agent semantics)
    body=None,            # legacy alias
) -> WriteResult: ...
```

`WriteResult` (frozen dataclass): `ok`, `slug`, `path`, `bytes_written`, `created`, `created_date`, `error`, `message`.

### 1.2 진입점 위임 (3종)

| 진입점 | 함수 | 변경 |
|---|---|---|
| **CLI** `raven.cli.__main__.page_new` | 73 lines → 25 lines | contracts.write_page 위임, typer.Exit 코드 보존 |
| **API** `raven.api.server.create_page` | 36 lines → 22 lines | contracts.write_page + HTTPException 매핑 (409/400) |
| **API** `raven.api.server.update_page` | 30 lines → 25 lines | contracts.write_page + pre-check 404 보존 |
| **Agent** `raven.agents.AgentVault.write` | 50 lines → 32 lines | contracts.write_page + provenance dict + normalize=False |

### 1.3 핵심 옵션 (`normalize`)

CLI/API는 `normalize=True` (default) — `hello` → `content/hello.md` (사용자 친화).
**Agent는 `normalize=False`** — LLM agent는 `content/hello` 같은 explicit path 사용 (provenance + audit 명확).

### 1.4 핵심 옵션 (`actor`)

`actor=None` (CLI/API): provenance 안 박음.
`actor={"name":..., "timestamp":..., "run_id":..., "intent":...}` (Agent): `frontmatter.render(agents=[...])` 호출로 YAML list 직렬화.

---

## 2. 회귀 분석 (구현 중 발견)

| 회귀 | 원인 | 해결 |
|---|---|---|
| `test_api_page_update_preserves_created` | update_page가 `meta.get("created")` 반환 → WriteResult에 `created_date` 필드 없음 | WriteResult에 `created_date: Optional[str]` 추가 |
| `test_api_page_update_rejects_bad_slug` | update_page의 pre-check이 404 잘못 반환 (slug 검증이 400) | `_safe_slug_or_400` 명시 호출 + 404만 pre-check |
| `test_agent_write_creates_with_provenance` | actor dict가 meta에 들어가서 Python repr로 직렬화됨 | frontmatter.render의 `agents` 별도 kwarg 활용 |
| `test_agent_write_creates_with_provenance` | actor dict에 `timestamp` 누락 | Agent write가 `provenance.timestamp` 포함 |
| `test_agent_write_short_slug_creates_at_root` | contracts의 default `normalize=True`가 Agent 시맨틱 위반 | contracts에 `normalize: bool` 옵션 추가 |

→ **5건 모두 해결**, **0건 잔존**.

---

## 3. 검증

```bash
$ PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/ -q
361 passed, 1 warning in 5.20s   ✅ 회귀 0 (기존 354 + 신규 7)

$ PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/test_contracts.py -v
tests/test_contracts.py::test_write_page_creates_new_file            PASSED
tests/test_contracts.py::test_write_page_overwrite_preserves_created  PASSED
tests/test_contracts.py::test_write_page_rejects_exists_when_no_overwrite PASSED
tests/test_contracts.py::test_write_page_normalize_prefixes_short_slugs PASSED
tests/test_contracts.py::test_write_page_normalize_false_keeps_bare_slug PASSED
tests/test_contracts.py::test_write_page_rejects_bad_slug             PASSED
tests/test_contracts.py::test_write_page_with_actor_attaches_agents_list PASSED
7 passed in 0.09s
```

---

## 4. 변경 사항 요약

| 카테고리 | 변경 |
|---|---|
| **신규** | `raven/core/contracts.py` (~250 lines, 단일 함수 + dataclass) |
| **신규** | `tests/test_contracts.py` (7 tests, 회귀 가드) |
| **CLI** `page_new` | -48 / +11 lines |
| **API** `create_page` | -36 / +22 lines |
| **API** `update_page` | -30 / +25 lines |
| **Agent** `AgentVault.write` | -36 / +18 lines |
| **`__init__.py`** | +3 lines (export contracts_module) |
| **`changelog-v0.6.2.md`** | 이 문서 |

코드 footprint: **net -1줄** (4-step recipe 중복 → 단일 함수로 통합).

---

## 5. 효과

| 효과 | 정량 |
|---|---|
| Write recipe 변경 시 패치 위치 | **4곳 → 1곳** |
| 회귀 가드 단일 진입점 | ✅ `tests/test_contracts.py` (7 tests) |
| 진입점별 시맨틱 보존 | CLI/API auto-prefix, Agent explicit-path, API 409/404, Agent provenance |

---

## 6. 다음 사이클 후보

1. **delete_page / rename_page 단일화** (P1-1 후속) — archive.py richer surface, 별도 audit 필요
2. **P1-2 SCHEMA.md sync 충돌 정책** (ADR + 3-way merge)
3. **P1-3 SQLite WAL + aiosqlite** (멀티 에이전트 동시성, experimental 한계 유지)
4. **MCP wiki_update 위임** — `overwrite=True`만 다른 entrypoint와 다름 (lock + idempotency) → 별도 옵션 필요
5. **Dashboard NewVaultWizard 실사용 검증**

---

## 7. 작업 보고

- **무엇**: `raven/core/contracts.py` 신규 + 진입점 3종 위임 (CLI/API/Agent) + 신규 테스트 7건
- **왜 (저장 신호)**: ① 재사용 가능성 (recipe 변경 1곳), ② 인수인계 (단일 진입점), ③ 결정 추적 (changelog + ADR §8), ④ 실패 기록 (회귀 5건 분석)
- **검증**: pytest 361 passed (회귀 0), contracts 단독 smoke test 통과
- **다음 가능**: delete/rename_page 단일화 (P1-1 후속), SCHEMA sync ADR, SQLite WAL
