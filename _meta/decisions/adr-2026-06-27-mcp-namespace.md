---
adr_id: adr-2026-06-27-mcp-namespace
title: MCP 패키지 네임스페이스 핵 제거 (`mcp/` → `raven/mcp/`)
status: proposed
created: 2026-06-27
deciders: wiki-orchestrator (제안) · user (검토 게이트)
supersedes: P0-4 in changelog-v0.5.6 §5
related:
  - AGENTS.md §8 (진입점 추가/제거 의사결정 절차)
  - AGENTS.md §10 ("mcp/ 패키지 이름 변경 없이 import 추가 ❌")
  - mcp/cli.py L10-90 (_load_sdk_fastmcp 우회 코드)
  - mcp/README.md L121-135 (근본 원인 설명)
---

# ADR: MCP 패키지 네임스페이스 핵 제거

## Context (배경)

### 문제

Raven의 MCP 진입점은 `mcp/` 디렉토리에 자체 패키지를 둠. 같은 이름 `mcp`를 쓰는 외부 SDK (`mcp[cli]>=1.x`, FastMCP)가 있어 **네임스페이스 충돌** 발생.

### 증거 — `_load_sdk_fastmcp` 우회 (mcp/cli.py:32-90, 56줄)

```python
# mcp/cli.py L11-15 (코드 자체가 인정)
The real MCP SDK (`mcp[cli]>=1.x`) ships its own `mcp` package whose
submodules include `mcp.server.fastmcp.FastMCP`. Because our local
`mcp/__init__.py` is first on `sys.path` whenever the vault root is the
cwd, Python's import machinery resolves `import mcp` to our package, not
the SDK. To access the SDK's `FastMCP`, we temporarily remove our local
`mcp.*` entries from `sys.modules` and re-import — see `_load_sdk_fastmcp`.
```

→ **56줄 우회 코드**가 **모든 MCP 서버 시작 시** 실행됨. 깨지기 쉬운 구조 + 외부 사용자 첫 `pip install` 시 import error 위험.

### mcp 사용처 audit (2026-06-27)

| 위치 | import | 비고 |
|---|---|---|
| `mcp/cli.py:92-95` | `from mcp import db`, `from mcp.tools import ...` | 자기 자신 |
| `mcp/tools/{read,write}.py` | `from mcp import db` | 자기 자신 |
| `tests/test_mcp_write_provenance.py:42,51` | `from mcp.tools import ...` | root test |
| `tests/test_mcp_concurrency.py:33,40` | `from mcp.tools import ...` | root test |
| `tests/test_locks.py:15` | `from mcp.tools import ...` | root test |
| `mcp/tests/conftest.py:1` | "make `mcp` and `scripts/` importable" | 의도적 격리 |

→ **외부 사용처 3개 파일** (tests), 모두 `from mcp.tools import ...` 패턴.

### scripts/pyproject.toml / Makefile

| 파일 | 상태 |
|---|---|
| `scripts/pyproject.toml` | `python-frontmatter`만 선언, **`mcp` 자체 ❌** |
| `Makefile` | `mcp` 타겟 **0** |

→ 의존성 격리 부재 + 별도 진입점 미정의. v0.5.7 P0-1에서 `python-frontmatter` 추가했지만 mcp 패키지 자체는 root venv에서 import 가능한 이유 = `mcp/` 디렉토리가 cwd + `sys.path`에 자동 포함됨 (fragile).

### 정책 정합

- **AGENTS.md §10**: `❌ mcp/ 패키지 이름 변경 없이 import 추가 ❌` — 이미 경고 명시
- **AGENTS.md §8**: 진입점 구조 변경은 **ADR + write contract 단일화 검증 + 테스트 + changelog + README 동기화 + 사용자 승인** 절차
- **README §"진입점 추가/제거"**: 위 절차 동일

→ 본 ADR이 AGENTS.md §8이 **오래도록 미뤄둔 정당한 후속**.

## Decision (결정안)

### A안 (권장): `mcp/` → `raven/mcp/` 이동

```
mcp/                      →  raven/mcp/
├── __init__.py           →  ├── __init__.py
├── cli.py                →  ├── cli.py
├── db.py                 →  ├── db.py
├── resources.py          →  ├── resources.py
├── README.md             →  ├── README.md
└── tools/                →  └── tools/
    ├── __init__.py       →      ├── __init__.py
    ├── read.py           →      ├── read.py
    └── write.py          →      └── write.py

mcp/tests/                →  raven/mcp/tests/  (또는 tests/ 유지 + import만 변경)
```

**import 갱신**:
- `from mcp import db` → `from raven.mcp import db`
- `from mcp.tools import ...` → `from raven.mcp.tools import ...`
- 영향: `mcp/cli.py`, `mcp/tools/*.py`, `tests/test_mcp_*.py`, `tests/test_locks.py` (~6 파일)

**삭제**: `mcp/cli.py:32-90` (`_load_sdk_fastmcp` 56줄) — SDK의 `mcp.server.fastmcp.FastMCP`를 정상 import 가능

**진입점 변경**:
- `python -m mcp.cli` → `python -m raven.mcp.cli`
- README §"MCP (LLM 표준)" 안내 갱신
- `Makefile`에 `mcp` 타겟 추가 (선택)

**scripts/pyproject.toml 갱신**:
- `dependencies = ["python-frontmatter>=1.1.0", "mcp[cli]>=1.x"]` (외부 SDK 명시)

### B안 (보류): SDK 패키지 이름 변경 추적

- 외부 SDK가 `mcp` 대신 다른 이름 쓰기 시작하면 충돌 자연 해소
- ❌ **불가능**: SDK 이름은 우리가 통제 불가, v0.5.6 changelog P0-4가 1년 넘게 미뤄진 결과

### C안 (기각): 우회 코드 보강

- `_load_sdk_fastmcp`를 더 robust하게 (path 감지 로직 강화)
- ❌ **근본 해결 아님**: 56줄 우회 자체가 fragile + 외부 사용자 첫 실행 시 깨질 수 있는 구조 동일

## Consequences (결과)

### Positive (A안)

- ✅ **56줄 우회 코드 완전 제거** → SDK `mcp.server.fastmcp.FastMCP`를 정상 import
- ✅ 외부 사용자 `pip install mcp[cli]>=1.x` 후 즉시 동작 (가정: `make install`이 의존성 추가)
- ✅ `from raven.mcp.tools import ...` 패턴 → 의도 명확
- ✅ AGENTS.md §10 정책 준수
- ✅ 진입점 4종 약속 ("MCP" = `raven/mcp/cli`) 일관성 회복

### Negative (A안)

- ⚠️ ~6 파일 import 경로 갱신 (회귀 가드 테스트로 보호)
- ⚠️ `python -m mcp.cli` 사용자 (있다면) breakage → README로 안내
- ⚠️ Makefile에 `mcp` 타겟 추가 시 작업량 +1

### Risks

| 위험 | 완화 |
|---|---|
| import 경로 갱신 누락 | grep으로 `from mcp\|import mcp` 전수 audit + pytest 354 passed 회귀 가드 |
| v0.5.6 changelog P0-4 ADR 누락 상태 | 본 ADR로 해소 |
| 외부 SDK의 `mcp.server.fastmcp` breaking change | 의존성 버전 pin (`mcp[cli]>=1.x,<2.0`) — 본 ADR 범위 외, 별도 이슈 |

## Alternatives Considered (검토한 대안)

| 안 | 채택 여부 | 이유 |
|---|---|---|
| **A안: `raven/mcp/` 이동** | ✅ **권장** | 근본 해결, 정책 준수, 우회 제거 |
| B안: SDK 이름 변경 대기 | ❌ | 통제 불가, 1년+ 미뤄짐 |
| C안: 우회 코드 보강 | ❌ | fragile 구조 유지 |
| **D안: hybrid — A안 + Makefile mcp 타겟** | 🟢 가능 | 작업량 +10줄, 진입점 명시. 본 ADR 본문에 **선택 사항**으로 명시 |

## Implementation Plan (구현 계획)

### Phase 1: 구조 이동 (atomic)

```bash
# worktree feat/v0.6.0-adr-mcp-namespace 에서
mkdir -p raven/mcp
git mv mcp/__init__.py mcp/cli.py mcp/db.py mcp/resources.py mcp/README.md raven/mcp/
git mv mcp/tools/ raven/mcp/tools
git mv mcp/tests/ raven/mcp/tests   # 또는 tests/ 유지 (선택)

# 단, git mv는 worktree 단위 작업이므로 worktree에서 실행
```

### Phase 2: import 갱신

```bash
# 다음 파일들에서:
# - from mcp import db → from raven.mcp import db
# - from mcp.tools import ... → from raven.mcp.tools import ...
# - import mcp (in tests) → import raven.mcp

mcp/cli.py → raven/mcp/cli.py
mcp/tools/{read,write}.py → raven/mcp/tools/{read,write}.py
tests/test_mcp_write_provenance.py
tests/test_mcp_concurrency.py
tests/test_locks.py
mcp/tests/conftest.py → raven/mcp/tests/conftest.py
```

### Phase 3: scripts/pyproject.toml

```diff
 dependencies = [
     "python-frontmatter>=1.1.0",
+    "mcp[cli]>=1.x",
 ]
```

### Phase 4: README/AGENTS.md 동기화

- README §"MCP (LLM 표준) | FastMCP 9 tools + 5 resources | `mcp/`" → "`raven/mcp/`"
- README §"빠른 시작" — `python -m mcp.cli` → `python -m raven.mcp.cli`
- AGENTS.md §"4가지 진입점" 표 — 같은 갱신

### Phase 5: Makefile `mcp` 타겟 (선택)

```makefile
.PHONY: mcp
mcp: venv-check ## Run MCP server (default: stdio, --write for mutating tools)
	PYTHONPATH=. $(PY) -m raven.mcp.cli
```

### Phase 6: 검증

```bash
PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/ -q
# → 354 passed, 1 warning (기존과 동일 회귀 가드)

# 외부 import 회수 확인
PYTHONPATH=. scripts/.venv/bin/python -c "from raven.mcp import cli; print('OK')"
PYTHONPATH=. scripts/.venv/bin/python -c "from raven.mcp.tools import write; print('OK')"
```

### Phase 7: 문서화

- `_meta/changelog-v0.6.0.md` 신규 (작업 보고)
- AGENTS.md §10 "mcp/ 패키지 이름 변경 없이 import 추가 ❌" 삭제 또는 갱신
- MEMORY.md 갱신 (P0-4 해소)

## Decision Status

- [x] **제안 작성**: 2026-06-27 (wiki-orchestrator)
- [ ] **사용자 검토 게이트**: pending
- [ ] **구현 시작**: 사용자 합의 후

## 사용자 결정 요청

다음 중 선택:

| 안 | 의미 | 작업량 |
|---|---|---|
| **A안 (권장)** | `mcp/` → `raven/mcp/` 이동 + import 갱신 + pyproject.toml + README | ~120줄, 1-2h |
| **A안 + Makefile 타겟 (D안)** | 위 + `make mcp` 타겟 추가 | ~130줄, 1.5-2h |
| **B안 (보류)** | 외부 SDK 변경 대기, ADR만 기록 | 10줄 (ADR만) |
| **C안 (기각)** | 우회 코드 보강 (비권장) | 30줄, fragile 구조 유지 |
| **거부** | P0-4를 v0.6.0 이후로 재연기 | 0줄 |

→ **A안 또는 A안+D안 추천** (근본 해결, 정책 준수).
