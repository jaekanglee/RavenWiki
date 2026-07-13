# 에이전트 포인터 스텁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** vault 루트에 `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/`.cursorrules`/`.windsurfrules` 5개 포인터 스텁을 자동 생성해, 어떤 코딩 에이전트 도구로 vault를 열든 `_meta/agents/PROJECT-WORKFLOW.md`(Tier 2 운영 지침)를 자동 발견하도록 한다.

**Architecture:** `raven/core/vault.py`에 단일 콘텐츠 상수(`AGENT_POINTER_STUB_CONTENT`)와 대상 파일 리스트(`AGENT_POINTER_STUB_FILES`)를 두고, `_meta/agents/PROJECT-WORKFLOW.md`가 실제로 존재하는 순간(정적 profile 플래그가 아니라 동적 파일 존재 여부로 판단)마다 5개 스텁을 무조건 덮어쓴다. 동시에 `_bootstrap_lite()`와 `sync_meta()`에 중복돼 있던 3-entry 템플릿 dict를 `LITE_BOOTSTRAP_FILE_MAP` 단일 상수로 통합한다. `raven/core/lint.py`의 기존 `#19 check_guide_freshness`를 확장해 스텁 존재/내용 일치를 감시한다.

**Tech Stack:** Python 3, pytest.

## Global Constraints

- 스텁 5개는 **완전히 동일한 콘텐츠** (`AGENT_POINTER_STUB_CONTENT`) — 벤더별 차이 없음.
- 스텁 생성 트리거는 **`_meta/agents/PROJECT-WORKFLOW.md`의 실제 존재 여부**로 판단한다 — `profile` 파라미터나 다른 정적 플래그로 게이팅하지 않는다 (profile은 `.vault.json`에 저장되지 않는 일회성 생성 파라미터일 뿐이므로).
- 스텁은 **항상 무조건 덮어쓴다** (SCHEMA.md/PROJECT-WORKFLOW.md/log.md의 "존재하면 skip" 정책과 다름) — `sync_meta()`의 `force` 파라미터는 스텁 쓰기에 영향을 주지 않는다.
- 트리거 지점은 정확히 3곳: `Vault.create(profile="llm-wiki")` → `_bootstrap_lite()`, `raven meta sync` / `raven vault bootstrap`(CLI) / `POST /api/vaults/{name}/bootstrap`(API) → 전부 `sync_meta()`를 호출하므로 자동 커버됨. **`raven build`는 트리거 대상이 아니다** (`db_module.build_db()`만 호출하며 지금까지도 SCHEMA/PROJECT-WORKFLOW/log.md를 건드린 적이 없음 — 이번 기능을 위해 build의 기존 동작 범위를 넓히지 않는다).
- `_bootstrap_basic()`은 스텁 로직을 호출하지 않는다 (PROJECT-WORKFLOW.md 자체가 없는 프로필).
- 신규 CLI/API/대시보드 표면 추가 없음. 신규 진입점 아님, ADR 불필요.
- `raven/core/verify.py`의 `TEMPLATE_MAP`/`LITE_BOOTSTRAP_FILES`(별도의 4번째 중복 — bootstrap 파일 byte-비교 검증용)는 **이번 스코프에서 건드리지 않는다** — `verify_bootstrap()`은 자신이 아는 3개 파일만 확인하고 vault 루트를 통째로 훑지 않으므로, 새 스텁 파일이 추가돼도 영향받지 않는다.

---

### Task 1: `raven/core/vault.py` — 중복 dict 통합 + 에이전트 포인터 스텁 생성

**Files:**
- Modify: `raven/core/vault.py:36-50` (기존 상수 블록 뒤에 신규 상수 추가), `raven/core/vault.py:349-369` (`_bootstrap_lite()`), `raven/core/vault.py:399-432` (`sync_meta()`)
- Test: `tests/test_agent_pointer_stubs.py` (신규)

**Interfaces:**
- Produces:
  - `raven.core.vault.AGENT_POINTER_STUB_FILES: tuple[str, ...]` — 5개 상대 경로.
  - `raven.core.vault.AGENT_POINTER_STUB_CONTENT: str` — 모든 스텁이 공유하는 고정 콘텐츠.
  - `raven.core.vault.LITE_BOOTSTRAP_FILE_MAP: dict[str, str]` — target 상대경로 → template 리소스 경로 (3-entry, SCHEMA/PROJECT-WORKFLOW/log.md).
  - `raven.core.vault._write_agent_pointer_stubs(path: Path) -> None` — 모듈 레벨 함수.

- [x] **Step 1: 실패하는 테스트부터 작성**

`tests/test_agent_pointer_stubs.py` 신규 작성:

```python
"""v0.8.1+ 에이전트 포인터 스텁 (AGENTS.md/CLAUDE.md/GEMINI.md/.cursorrules/.windsurfrules).

_meta/agents/PROJECT-WORKFLOW.md가 존재하는 vault는 profile과 무관하게
5개 포인터 스텁을 얻는다. basic 프로필(PROJECT-WORKFLOW.md 없음)은 스텁도 없다.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.vault import Vault, AGENT_POINTER_STUB_FILES, AGENT_POINTER_STUB_CONTENT


@pytest.fixture
def isolated_vaults_root(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="raven-stub-reg-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def isolated_target():
    tmp = Path(tempfile.mkdtemp(prefix="raven-stub-target-"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def test_llm_wiki_profile_creates_all_stub_files(isolated_vaults_root, isolated_target):
    v = Vault.create("stub-llm", isolated_target / "stub-llm", profile="llm-wiki")
    for fname in AGENT_POINTER_STUB_FILES:
        fp = v.root / fname
        assert fp.is_file(), f"{fname} should exist for llm-wiki profile"
        assert fp.read_text(encoding="utf-8") == AGENT_POINTER_STUB_CONTENT


def test_basic_profile_creates_no_stub_files(isolated_vaults_root, isolated_target):
    v = Vault.create("stub-basic", isolated_target / "stub-basic", profile="basic")
    for fname in AGENT_POINTER_STUB_FILES:
        assert not (v.root / fname).exists(), f"{fname} should NOT exist for basic profile"


def test_sync_meta_backfills_stubs_after_basic_to_llm_wiki_transition(isolated_vaults_root, isolated_target):
    v = Vault.create("stub-transition", isolated_target / "stub-transition", profile="basic")
    for fname in AGENT_POINTER_STUB_FILES:
        assert not (v.root / fname).exists()
    v.sync_meta()
    assert (v.root / "_meta" / "agents" / "PROJECT-WORKFLOW.md").is_file()
    for fname in AGENT_POINTER_STUB_FILES:
        fp = v.root / fname
        assert fp.is_file(), f"{fname} should appear after sync_meta() backfills PROJECT-WORKFLOW.md"
        assert fp.read_text(encoding="utf-8") == AGENT_POINTER_STUB_CONTENT


def test_sync_meta_always_overwrites_stub_files_even_when_manually_edited(isolated_vaults_root, isolated_target):
    v = Vault.create("stub-overwrite", isolated_target / "stub-overwrite", profile="llm-wiki")
    tampered = v.root / "CLAUDE.md"
    tampered.write_text("사용자가 직접 고친 내용\n", encoding="utf-8")
    v.sync_meta()
    assert tampered.read_text(encoding="utf-8") == AGENT_POINTER_STUB_CONTENT


def test_lite_bootstrap_file_map_is_shared_single_source(isolated_vaults_root, isolated_target):
    """LITE_BOOTSTRAP_FILE_MAP 통합 회귀 가드: 두 경로가 같은 상수를 참조한다."""
    from raven.core.vault import LITE_BOOTSTRAP_FILE_MAP
    assert set(LITE_BOOTSTRAP_FILE_MAP.keys()) == {
        "_meta/agents/SCHEMA.md",
        "_meta/agents/PROJECT-WORKFLOW.md",
        "log.md",
    }
    v = Vault.create("stub-consistency", isolated_target / "stub-consistency", profile="llm-wiki")
    for rel_target in LITE_BOOTSTRAP_FILE_MAP:
        assert (v.root / rel_target).is_file()
```

- [x] **Step 2: 테스트 실행해서 실패 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_agent_pointer_stubs.py -v`
Expected: FAIL — `ImportError: cannot import name 'AGENT_POINTER_STUB_FILES' from 'raven.core.vault'`

- [x] **Step 3: 신규 상수 + 헬퍼 함수 추가**

`raven/core/vault.py`에서 기존 `_BASIC_BOOTSTRAP_FILES` 블록(37-50줄) 바로 뒤에 추가:

```python
# v0.8.1+: 다른 코딩 에이전트 도구는 프로젝트 루트에서 각자 다른 파일명을
# 관례적으로 자동 로드한다 (Claude Code → CLAUDE.md, Codex류 → AGENTS.md,
# Gemini CLI → GEMINI.md, Cursor/Windsurf → .cursorrules/.windsurfrules).
# 이 5개 스텁은 어떤 도구로 vault를 열든 Tier 2 운영 지침
# (_meta/agents/PROJECT-WORKFLOW.md)을 자동 발견하게 해준다.
AGENT_POINTER_STUB_FILES: tuple[str, ...] = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".cursorrules",
    ".windsurfrules",
)

AGENT_POINTER_STUB_CONTENT = (
    "이 vault의 에이전트 운영 지침은 `_meta/agents/PROJECT-WORKFLOW.md` 참조.\n"
    "(자동 생성 파일 — 직접 편집 금지. `raven meta sync`가 매번 덮어씁니다.)\n"
)

# v0.8.1+: _bootstrap_lite()의 template_map과 sync_meta()의 file_map은
# 완전히 동일한 3-entry dict를 각자 중복 정의하고 있었다 (drift 위험 —
# 위 _LITE_BOOTSTRAP_FILES 주석이 이미 "must match" 라고 경고했던 지점).
# 하나의 상수로 통합.
LITE_BOOTSTRAP_FILE_MAP: dict[str, str] = {
    "_meta/agents/SCHEMA.md":            "templates/agent/SCHEMA.md",
    "_meta/agents/PROJECT-WORKFLOW.md":  "templates/agent/PROJECT-WORKFLOW.md",
    "log.md":                            "templates/log.md",
}


def _write_agent_pointer_stubs(path: Path) -> None:
    """PROJECT-WORKFLOW.md가 있으면 5개 포인터 스텁을 무조건 덮어써서 생성.

    profile이 아니라 PROJECT-WORKFLOW.md의 실제 존재 여부로 트리거한다 —
    basic 프로필로 만들어진 vault가 나중에 sync_meta()로 PROJECT-WORKFLOW.md를
    얻게 되는 경우에도, 같은 호출 안에서 스텁이 함께 생기도록 하기 위함.
    """
    if not (path / "_meta" / "agents" / "PROJECT-WORKFLOW.md").exists():
        return
    for rel_target in AGENT_POINTER_STUB_FILES:
        (path / rel_target).write_text(AGENT_POINTER_STUB_CONTENT, encoding="utf-8")
```

- [x] **Step 4: `_bootstrap_lite()`가 통합 상수를 참조하도록 교체 + 스텁 호출 추가**

`raven/core/vault.py`의 `_bootstrap_lite()` 안에서, 지역 변수 정의:

```python
        # Map: target relative path → template resource path
        template_map = {
            "_meta/agents/SCHEMA.md":            "templates/agent/SCHEMA.md",
            "_meta/agents/PROJECT-WORKFLOW.md":  "templates/agent/PROJECT-WORKFLOW.md",
            "log.md":                            "templates/log.md",
        }

        for rel_target, tmpl_path in template_map.items():
```

를 다음으로 교체:

```python
        for rel_target, tmpl_path in LITE_BOOTSTRAP_FILE_MAP.items():
```

그리고 이 for 루프가 끝난 직후(`_bootstrap_lite()` 함수의 마지막 줄, `except Exception as e: raise RuntimeError(...) from e` 블록 다음), 스텁 생성 호출을 추가:

```python
                raise RuntimeError(
                    f"Lite bootstrap failed: could not copy {rel_target} "
                    f"from {tmpl_path}: {e}"
                ) from e

        _write_agent_pointer_stubs(path)
```

- [x] **Step 5: `sync_meta()`가 통합 상수를 참조하도록 교체 + 스텁 호출 추가**

`raven/core/vault.py`의 `sync_meta()` 안에서, 지역 변수 정의:

```python
        file_map = {
            "_meta/agents/SCHEMA.md":            "templates/agent/SCHEMA.md",
            "_meta/agents/PROJECT-WORKFLOW.md":  "templates/agent/PROJECT-WORKFLOW.md",
            "log.md":                            "templates/log.md",
        }
        if not lite and not force:
            # Safety: full set without force could overwrite user-edited files.
            for rel_target in file_map:
```

를 다음으로 교체 (2군데 `file_map` 참조 모두):

```python
        if not lite and not force:
            # Safety: full set without force could overwrite user-edited files.
            for rel_target in LITE_BOOTSTRAP_FILE_MAP:
```

그리고 아래쪽 `for rel_target, tmpl_path in file_map.items():` 도 `LITE_BOOTSTRAP_FILE_MAP.items()`로 교체.

마지막으로 `sync_meta()`의 `return out` 바로 앞에 스텁 호출 추가:

```python
            except Exception as e:
                out["errors"].append({"file": rel_target, "error": str(e)})
        _write_agent_pointer_stubs(self.root)
        return out
```

- [x] **Step 6: 테스트 실행해서 통과 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_agent_pointer_stubs.py -v`
Expected: 5 passed

- [x] **Step 7: 기존 bootstrap/vault 관련 테스트 회귀 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_vault_create.py tests/test_basic_profile_bootstrap.py tests/test_bootstrap_verify.py tests/test_v0_7_1_lite_bootstrap_surface.py tests/test_tier_boundary.py -v`
Expected: 모두 PASS (기존 3종 파일의 skip-if-exists 동작, `_LITE_BOOTSTRAP_FILES`/`_BASIC_BOOTSTRAP_FILES` 검증, tier-boundary 검증 모두 그대로 통과해야 함 — 이번 변경은 add-only)

- [x] **Step 8: 커밋**

```bash
git add raven/core/vault.py tests/test_agent_pointer_stubs.py
git commit -m "$(cat <<'EOF'
feat(vault): 에이전트 포인터 스텁 자동 생성 + bootstrap 파일맵 통합

_bootstrap_lite()/sync_meta()에 중복돼 있던 3-entry 템플릿 dict를
LITE_BOOTSTRAP_FILE_MAP 단일 상수로 통합. PROJECT-WORKFLOW.md가 존재하는
순간(profile이 아니라 파일 존재 여부로 판단) AGENTS.md/CLAUDE.md/
GEMINI.md/.cursorrules/.windsurfrules 5개 포인터 스텁을 자동 생성/재생성.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `raven/core/lint.py` — `#19 check_guide_freshness` 확장

**Files:**
- Modify: `raven/core/lint.py` (`check_guide_freshness()` 함수, PROJECT-WORKFLOW.md 섹션과 `return out` 사이)
- Test: `tests/test_lint_guide_freshness.py` (기존 파일에 테스트 추가)

**Interfaces:**
- Consumes: `raven.core.vault.AGENT_POINTER_STUB_FILES`, `raven.core.vault.AGENT_POINTER_STUB_CONTENT` (Task 1).
- Produces: 없음 (lint 최종 소비자). 기존 `#19` 이슈 포맷(`{"id": "#19", "severity": "info", "slug": ..., "message": ...}`)을 그대로 따른다.

- [x] **Step 1: 실패하는 테스트부터 작성**

`tests/test_lint_guide_freshness.py`에 다음 4개 테스트 함수를 파일 끝에 추가 (기존 `_setup_vault`/`_write_agents`/`_write_stamp` 헬퍼 재사용):

```python
def test_lint_19_no_stub_check_when_pww_missing(tmp_path):
    """PROJECT-WORKFLOW.md 자체가 없으면 (basic profile 상황) 스텁 검사 skip."""
    from raven.core.lint import check_guide_freshness
    from raven.core.vault import AGENT_POINTER_STUB_FILES

    vault = _setup_vault(tmp_path)
    # _write_agents() 호출 안 함 — SCHEMA/PWW 둘 다 없는 상태
    issues = check_guide_freshness(vault)
    stub_issues = [i for i in issues if i["slug"] in AGENT_POINTER_STUB_FILES]
    assert stub_issues == []


def test_lint_19_stub_files_missing_when_pww_exists(tmp_path):
    """PWW 있고 stamp 신선하지만 스텁 파일 5개가 없음 — info 5건 추가."""
    from raven.core.lint import check_guide_freshness
    from raven.core.vault import AGENT_POINTER_STUB_FILES
    from raven.mcp.tools.guide import _sha256

    vault = _setup_vault(tmp_path)
    _write_agents(vault.root)
    schema_hash = _sha256(vault.root / "_meta" / "agents" / "SCHEMA.md")
    pww_hash = _sha256(vault.root / "_meta" / "agents" / "PROJECT-WORKFLOW.md")
    _write_stamp(vault.root, {"SCHEMA": schema_hash, "PROJECT-WORKFLOW": pww_hash})
    issues = check_guide_freshness(vault)
    stub_issues = [i for i in issues if i["slug"] in AGENT_POINTER_STUB_FILES]
    assert len(stub_issues) == len(AGENT_POINTER_STUB_FILES)
    assert all("부재" in i["message"] for i in stub_issues)


def test_lint_19_stub_files_fresh_when_content_matches(tmp_path):
    """스텁 5개가 정확한 내용으로 존재 — 스텁 관련 issue 0건."""
    from raven.core.lint import check_guide_freshness
    from raven.core.vault import AGENT_POINTER_STUB_FILES, AGENT_POINTER_STUB_CONTENT
    from raven.mcp.tools.guide import _sha256

    vault = _setup_vault(tmp_path)
    _write_agents(vault.root)
    schema_hash = _sha256(vault.root / "_meta" / "agents" / "SCHEMA.md")
    pww_hash = _sha256(vault.root / "_meta" / "agents" / "PROJECT-WORKFLOW.md")
    _write_stamp(vault.root, {"SCHEMA": schema_hash, "PROJECT-WORKFLOW": pww_hash})
    for fname in AGENT_POINTER_STUB_FILES:
        (vault.root / fname).write_text(AGENT_POINTER_STUB_CONTENT, encoding="utf-8")
    issues = check_guide_freshness(vault)
    stub_issues = [i for i in issues if i["slug"] in AGENT_POINTER_STUB_FILES]
    assert stub_issues == []


def test_lint_19_stub_file_tampered_content(tmp_path):
    """스텁 파일 내용이 변조됨 — 해당 스텁만 info 1건."""
    from raven.core.lint import check_guide_freshness
    from raven.core.vault import AGENT_POINTER_STUB_FILES, AGENT_POINTER_STUB_CONTENT
    from raven.mcp.tools.guide import _sha256

    vault = _setup_vault(tmp_path)
    _write_agents(vault.root)
    schema_hash = _sha256(vault.root / "_meta" / "agents" / "SCHEMA.md")
    pww_hash = _sha256(vault.root / "_meta" / "agents" / "PROJECT-WORKFLOW.md")
    _write_stamp(vault.root, {"SCHEMA": schema_hash, "PROJECT-WORKFLOW": pww_hash})
    for fname in AGENT_POINTER_STUB_FILES:
        (vault.root / fname).write_text(AGENT_POINTER_STUB_CONTENT, encoding="utf-8")
    (vault.root / "CLAUDE.md").write_text("변조됨\n", encoding="utf-8")
    issues = check_guide_freshness(vault)
    stub_issues = [i for i in issues if i["slug"] == "CLAUDE.md"]
    assert len(stub_issues) == 1
    assert "불일치" in stub_issues[0]["message"]
```

- [x] **Step 2: 테스트 실행해서 실패 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_lint_guide_freshness.py -v`
Expected: 첫 번째 테스트(`no_stub_check_when_pww_missing`)는 이미 통과(스텁 검사가 아직 없으므로 `stub_issues`가 항상 빈 리스트) — 나머지 3개는 FAIL (스텁 관련 issue가 전혀 생성되지 않으므로 `len(stub_issues) == 0`으로 assert 실패)

- [x] **Step 3: `check_guide_freshness()`에 스텁 검사 추가**

`raven/core/lint.py`의 `check_guide_freshness()` 함수 안, 기존 `from raven.mcp.tools.guide import _sha256, _load_version_stamp` import 줄을 찾아서 그 아래에 추가:

```python
    from raven.mcp.tools.guide import _sha256, _load_version_stamp
    from .vault import AGENT_POINTER_STUB_FILES, AGENT_POINTER_STUB_CONTENT
```

그리고 함수 안 PROJECT-WORKFLOW.md 섹션(`pww_path` 관련 if/else 블록) 다음, 기존 `return out` 바로 앞에 추가:

```python
    # 포인터 스텁 (v0.8.1+): PROJECT-WORKFLOW.md가 있을 때만 검사 —
    # profile=basic처럼 PROJECT-WORKFLOW.md 자체가 없는 vault는 스텁도
    # 없는 게 정상이므로 skip.
    if pww_path.exists():
        for stub_name in AGENT_POINTER_STUB_FILES:
            stub_path = vault.root / stub_name
            if not stub_path.exists():
                out.append(_mk_issue(
                    "#19", "info", stub_name,
                    f"에이전트 포인터 스텁 부재 — {stub_name}이 vault 루트에 없음 "
                    f"(raven meta sync 실행 시 자동 생성)",
                ))
                continue
            try:
                content = stub_path.read_text(encoding="utf-8")
            except Exception:
                content = None
            if content != AGENT_POINTER_STUB_CONTENT:
                out.append(_mk_issue(
                    "#19", "info", stub_name,
                    f"에이전트 포인터 스텁 내용 불일치 — {stub_name}이 변조됨 "
                    f"(raven meta sync 실행 시 자동 복구)",
                ))

    return out
```

- [x] **Step 4: 테스트 실행해서 통과 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_lint_guide_freshness.py -v`
Expected: 8 passed (기존 4개 + 신규 4개)

- [x] **Step 5: 전체 lint 테스트 회귀 확인**

Run: `scripts/.venv/bin/python -m pytest tests/ -k lint -v`
Expected: 모두 PASS

- [x] **Step 6: 커밋**

```bash
git add raven/core/lint.py tests/test_lint_guide_freshness.py
git commit -m "$(cat <<'EOF'
feat(lint): #19 guide freshness가 에이전트 포인터 스텁도 감시하도록 확장

PROJECT-WORKFLOW.md가 존재하는 vault에 한해, AGENTS.md/CLAUDE.md/
GEMINI.md/.cursorrules/.windsurfrules 5개 스텁의 존재/내용 일치를
결정론적 문자열 비교로 검사. info 등급, silent warn.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: 전체 회귀 검증 + 수동 확인

**Files:** 없음 (검증 전용 태스크, 코드 변경 없음)

**Interfaces:**
- Consumes: Task 1-2 전체 산출물.
- Produces: 없음.

- [x] **Step 1: 전체 Python 테스트 스위트 실행**

Run: `scripts/.venv/bin/python -m pytest tests/ -q`
Expected: 전체 PASS, 실패 0건

- [x] **Step 2: 실제 vault로 CLI 수동 확인 — llm-wiki 프로필**

```bash
export WIKI_VAULTS_DIR=$(mktemp -d /tmp/raven-stub-manual-reg-XXXX)
scripts/.venv/bin/python -m raven.cli vault create manual-stub-llm "$(mktemp -d /tmp/raven-stub-manual-target-XXXX)/manual-stub-llm"
ls "$WIKI_VAULTS_DIR"/../*manual-stub-llm*/manual-stub-llm 2>/dev/null || find /tmp -maxdepth 3 -iname "manual-stub-llm" -exec ls {} \;
```
Expected: vault 루트에 `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules` 5개 파일이 보임.

- [x] **Step 3: 실제 vault로 CLI 수동 확인 — basic 프로필 + sync_meta 전환**

```bash
export WIKI_VAULTS_DIR=$(mktemp -d /tmp/raven-stub-manual-reg2-XXXX)
TARGET=$(mktemp -d /tmp/raven-stub-manual-target2-XXXX)/manual-stub-basic
scripts/.venv/bin/python -m raven.cli vault create manual-stub-basic "$TARGET" --profile basic
ls -la "$TARGET" | grep -E "AGENTS|CLAUDE|GEMINI|cursorrules|windsurfrules" && echo "FAIL: 스텁이 basic에 생기면 안 됨" || echo "OK: basic은 스텁 없음"
scripts/.venv/bin/python -m raven.cli meta sync --vault manual-stub-basic
ls -la "$TARGET" | grep -E "AGENTS|CLAUDE|GEMINI|cursorrules|windsurfrules" && echo "OK: sync 후 스텁 생김" || echo "FAIL: sync 후에도 스텁 없음"
```
Expected: 첫 번째 `ls` 후 "OK: basic은 스텁 없음", `meta sync` 후 두 번째 `ls`에서 "OK: sync 후 스텁 생김".

- [x] **Step 4: 임시 디렉토리 정리 + 사용자에게 결과 보고**

```bash
rm -rf /tmp/raven-stub-manual-*
```

다음을 포함해 보고 (AGENTS.md §12 형식):
- 무엇을 했는가: Task 1-2에서 수정한 2개 파일(`raven/core/vault.py`, `raven/core/lint.py`) + 신규/확장 테스트 2개 파일 경로
- 왜 그렇게 했는가: 저장 신호 — 재사용성(어떤 코딩 에이전트 도구든 vault 진입 시 자동 발견) + 실패 기록(중복 dict 3벌 중 2벌을 통합해 drift 재발 방지)
- 검증: Step 1-3의 pytest/수동 CLI 결과
- 다음에 무엇이 가능한가: `raven/core/verify.py`의 4번째 중복(`TEMPLATE_MAP`) 정리, `.cursorrules`/`.windsurfrules` 외 추가 벤더 지원, 큐레이션 판단 기준 문서(다음 우선순위 항목) 등 후속 후보

(커밋 없음 — 검증 전용 태스크)

---
