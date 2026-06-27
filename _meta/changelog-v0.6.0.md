# raven v0.6.0 — MCP 네임스페이스 핵 제거 (P0-4 해소)

> **핵심**: ADR-2026-06-27-mcp-namespace (사용자 A안 합의) 구현. `mcp/` → `raven/mcp/` 이동으로 SDK `mcp[cli]>=1.x`와 충돌 해소. **56줄 우회 코드 (`_load_sdk_fastmcp`) 완전 제거**.

릴리스 일자: 2026-06-27
이전: v0.5.8 (tsbuildinfo 추적 해제)

---

## 한 줄 요약

자체 MCP 패키지를 `raven/mcp/`로 이동, 외부 SDK `mcp[cli]>=1.x`와의 네임스페이스 충돌을 **구조적으로 제거**. SDK의 `FastMCP`를 정상 import.

---

## 1. 변경 사항 (구현 A안)

### 1.1 구조 이동 (`git mv` atomic)

| Before | After |
|---|---|
| `mcp/__init__.py` | `raven/mcp/__init__.py` |
| `mcp/cli.py` | `raven/mcp/cli.py` |
| `mcp/db.py` | `raven/mcp/db.py` |
| `mcp/resources.py` | `raven/mcp/resources.py` |
| `mcp/README.md` | `raven/mcp/README.md` |
| `mcp/tools/{__init__,read,write}.py` | `raven/mcp/tools/{__init__,read,write}.py` |
| `mcp/tests/{conftest,test_db,test_tools}.py` | `raven/mcp/tests/{conftest,test_db,test_tools}.py` |

→ `git mv` 사용으로 **파일 이력 보존** (R = rename).

### 1.2 import 갱신 (10파일 / 22 import)

| 파일 | 변경 |
|---|---|
| `raven/mcp/cli.py` | `from mcp import db` → `from raven.mcp import db` 등 4 lines |
| `raven/mcp/tools/{read,write}.py` | `from mcp import db` → `from raven.mcp import db` 등 4 lines |
| `raven/mcp/resources.py` | 1 line (lazy import) |
| `raven/mcp/tests/test_db.py` | 1 line |
| `raven/mcp/tests/test_tools.py` | 6 lines (top + nested) |
| `tests/test_mcp_write_provenance.py` | 2 import blocks |
| `tests/test_mcp_concurrency.py` | 2 import blocks |
| `tests/test_locks.py` | 1 import block (ANONYMOUS_ACTOR 정렬 보존) |
| `raven/api/server.py` | **1 line (ADR audit에서 누락 발견, 구현 시 보강)** |

### 1.3 `_load_sdk_fastmcp` 56줄 제거

`raven/mcp/cli.py:32-90`의 sys.modules/sys.path 우회 코드 완전 삭제. 이유: `raven.mcp`로 이동하면서 `import mcp`가 SDK 패키지로 직접 resolve됨.

```diff
-from mcp import db as db_module
+from mcp.server.fastmcp import FastMCP   # ← 정상 SDK import
+from raven.mcp import db as db_module

-def _load_sdk_fastmcp():
-    """56줄 우회 코드..."""
-    import os
-    stashed_modules = {...}
-    # ... path/module scrub logic ...
-    fastmcp_mod = importlib.import_module("mcp.server.fastmcp")
-    return fastmcp_mod.FastMCP

-mcp_cls = _load_sdk_fastmcp()
-mcp = mcp_cls("wiki")
+mcp = FastMCP("wiki")
```

→ 56줄 → 1줄. 외부 SDK 충돌 **구조적으로 제거**.

### 1.4 의존성 명시

`scripts/pyproject.toml`:
```diff
 dependencies = [
     "python-frontmatter>=1.1.0",
+    "mcp[cli]>=1.x",
 ]
```

### 1.5 README / AGENTS.md 동기화

| 파일 | 변경 |
|---|---|
| `README.md` §"무엇인가" 표 | `mcp/` → `raven/mcp/` |
| `README.md` §"파일 트리" | `raven/mcp/` 추가 + `mcp/` deprecated 표시 |
| `AGENTS.md` §2 표 | `mcp/` → `raven/mcp/` |
| `AGENTS.md` §7 권한 | `mcp/` → `raven/mcp/` |
| `AGENTS.md` §10 정책 | v0.6.0+ namespace 갱신 |

---

## 2. ADR audit 정정

ADR 작성 시 다음 파일을 **놓침**:

| 파일 | 누락 import | 해결 |
|---|---|---|
| `raven/api/server.py:722` | `from mcp.tools import check_lock, _load_locks_store, _is_expired` | ✅ v0.6.0 구현 시 갱신 |

→ ADR §3 "Risks"의 "import 경로 갱신 누락" 위험이 실제로 발생 — **grep audit으로 즉시 발견 + 수정**. 다음 ADR 작성 시 더 엄격한 audit 필요.

---

## 3. 검증

```bash
$ PYTHONPATH=. scripts/.venv/bin/python -c "
from raven.mcp import cli, db, resources
from raven.mcp.tools import read, write
from mcp.server.fastmcp import FastMCP
print('all OK')
"
✅ all OK

$ PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/ -q
354 passed, 1 warning in 5.57s
✅ 회귀 0 (변경 전과 동일)

$ grep -rn "from mcp\b\|import mcp\b" --include="*.py" | grep -v "from raven.mcp\|from mcp.server\|mcp.server.fastmcp"
✅ 0 matches (잔존 import 없음)
```

---

## 4. 변경 사항 요약

| 카테고리 | 변경 |
|---|---|
| 구조 이동 | 11 파일 (git mv atomic) |
| import 갱신 | 10 파일, 22 lines |
| `_load_sdk_fastmcp` 제거 | cli.py -56 lines |
| SDK 직접 import | cli.py +1 line |
| `_resolve_vault` 경로 | cli.py (parent.parent → parent.parent.parent) |
| `scripts/pyproject.toml` | +1 dep |
| README | 3곳 갱신 |
| AGENTS.md | 3곳 갱신 |
| **`_meta/changelog-v0.6.0.md`** | **이 문서** |

코드 변경: +20 / -85 (net -65줄) · 문서 변경: +12 / -8

---

## 5. 호환성

| 항목 | 상태 |
|---|---|
| `python -m mcp.cli` (구) | ❌ 깨짐 → `python -m raven.mcp.cli` 사용 |
| `from mcp.tools import ...` (구) | ❌ 깨짐 → `from raven.mcp.tools import ...` 사용 |
| 외부 SDK `mcp[cli]>=1.x` | ✅ 정상 (네임스페이스 충돌 해소) |
| `python -m raven.api` / Dashboard | ✅ 영향 없음 |
| pytest 354 tests | ✅ 모두 통과 |

**사용자 액션**: README가 안내하는 quick start만 따르면 OK. 외부 사용자는 `pip install mcp[cli]>=1.x` 후 즉시 동작.

---

## 6. P0 잔여

| # | 항목 | 상태 |
|---|---|---|
| P0-1, 3, 5, 6, 7, 8 | v0.5.7 외부 배포 P0 | ✅ |
| P0-2 tsbuildinfo | v0.5.8 | ✅ |
| **P0-4 MCP 네임스페이스** | **v0.6.0** | ✅ **본 사이클로 해소** |

→ **모든 P0 완료**. 외부 배포 차단 이슈 0건.

---

## 7. 다음 사이클 후보 (v0.6.1 / v0.7)

1. **P1-1 write-path 단일화** (`raven.core.contracts.write_page()`, 50~100줄)
2. **P1-2 SCHEMA sync 충돌 정책** (ADR + 3-way merge vs skip+warn)
3. **P1-3 SQLite WAL + aiosqlite** (멀티 에이전트 동시성, experimental 한계 명시 유지)
4. **Dashboard NewVaultWizard 실사용 검증** (방금 머지된 lost-in-limbo 회수분)

---

## 8. 작업 보고

- **무엇**: `mcp/` → `raven/mcp/` 이동 (11파일 git mv) + import 갱신 (10파일 22 lines) + `_load_sdk_fastmcp` 56줄 제거 + pyproject.toml 의존성 + README/AGENTS 동기화
- **왜 (저장 신호)**: ① 재사용 가능성 (외부 SDK 호환), ② 인수인계 (사용자 quick start 일관), ③ 결정 추적 (ADR + 본 changelog), ④ 실패 기록 (ADR audit 누락 발견)
- **검증**: SDK import 정상, raven.mcp import 정상, pytest 354 passed (회귀 0), 잔존 `from mcp` 0건
- **다음 가능**: P1-1 write-path 단일화 (멀티 진입점 write 일관), Dashboard NewVaultWizard 실사용 검증
