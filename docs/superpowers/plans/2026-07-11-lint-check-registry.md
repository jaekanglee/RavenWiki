# Lint 체크 레지스트리 단일화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** `raven/core/lint.py`에 `CHECK_REGISTRY` 단일 소스를 추가하고, CLI/API/대시보드가 하드코딩된 체크 이름/개수 대신 이를 참조하도록 고쳐 현재 존재하는 drift 버그(대시보드 14개, CLI summary 13개, CLI `_CHECK_ID_TO_NAME`의 `#1`/`#3` 오매핑, `#2`/`#14`-`#23` 누락)를 제거한다.

**Architecture:** 백엔드 `CHECK_REGISTRY: dict[str, dict]`(id → {name, fn})가 유일한 소스. `run_all()`이 `checks` 필드로 이를 embed하고, API 두 엔드포인트가 그대로 forward하며, CLI는 같은 프로세스이므로 직접 import해서 참조하고, 대시보드는 API 응답의 `checks` 필드에서 이름/순회 목록을 파생한다.

**Tech Stack:** Python 3 (FastAPI, Typer), TypeScript/React 19 (Vite), pytest, vitest.

## Global Constraints

- 응답 필드는 **added-only** — 기존 `counts`/`by_check`/`issues` 키 이름·타입 변경 금지 (하위 호환).
- 신규 진입점 추가 없음, ADR 불필요 (AGENTS.md §8 대상 아님).
- auto-fix/quick-fix UI 추가 금지 — `dashboard/tests/LintPage.no-quickfix.contract.test.ts`가 계속 통과해야 함 (`handleRebuild`는 유지, `퀵픽스`/`handleFixBrokenLink`/`handleFixFrontmatter`/`stub 문서` 문자열은 추가 금지).
- `#1`-`#3`은 `_legacy_link_issues()`(link_module 기반)로 생성되며 개별 `check_*` 함수가 없다 — `CHECK_REGISTRY`에서 `fn: None`으로 표시.
- 커밋은 매 태스크 종료 시 1개씩, 태스크 밖에서 마음대로 묶지 않는다.

---

### Task 1: 백엔드 `CHECK_REGISTRY` 추가 + `run_all()` embed + 회귀 테스트

**Files:**
- Modify: `raven/core/lint.py` (모듈 상수 추가 — `CORE_TAGS_FALLBACK` 정의 블록 뒤, `# ────── 데이터 구조 ──────` 섹션 앞이 적당한 위치, 그리고 `run_all()` 함수 내부 return dict)
- Test: `tests/test_lint_check_registry.py` (신규)

**Interfaces:**
- Produces: `lint_module.CHECK_REGISTRY: dict[str, dict]` — 각 값은 `{"name": str, "fn": Optional[str]}`. `run_all(vault)`의 반환 dict에 새 키 `"checks": dict[str, str]` (id → name) 추가.

- [x] **Step 1: 회귀 테스트부터 작성 (실패 확인용)**

`tests/test_lint_check_registry.py` 새로 작성:

```python
"""CHECK_REGISTRY가 실제 run_all() 산출 check id를 전부 커버하는지 회귀 검증.

새 check_* 함수가 lint.py에 추가됐는데 CHECK_REGISTRY 등록을 빠뜨리면 이 테스트가
실패해 즉시 드러난다 (대시보드/CLI 14개↔23개 drift 재발 방지).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core import lint as lint_module
from raven.core.vault import Vault


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-lintreg-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-lintreg-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("lintreg-test", target_root / "lintreg-test", bootstrap=False)
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_check_registry_covers_all_produced_ids(vault):
    result = lint_module.run_all(vault)
    produced_ids = set(result["by_check"].keys())
    registry_ids = set(lint_module.CHECK_REGISTRY.keys())
    missing = produced_ids - registry_ids
    assert not missing, f"CHECK_REGISTRY에 등록되지 않은 check id: {missing}"


def test_check_registry_fn_names_resolve_to_real_functions():
    for cid, meta in lint_module.CHECK_REGISTRY.items():
        fn_name = meta.get("fn")
        if fn_name is None:
            continue
        assert hasattr(lint_module, fn_name), (
            f"{cid}: CHECK_REGISTRY.fn={fn_name!r} 가 raven.core.lint에 없음"
        )


def test_run_all_embeds_checks_field(vault):
    result = lint_module.run_all(vault)
    assert "checks" in result
    assert result["checks"] == {
        cid: meta["name"] for cid, meta in lint_module.CHECK_REGISTRY.items()
    }
```

- [x] **Step 2: 테스트 실행해서 실패 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_lint_check_registry.py -v`
Expected: FAIL — `AttributeError: module 'raven.core.lint' has no attribute 'CHECK_REGISTRY'`

- [x] **Step 3: `CHECK_REGISTRY` 추가**

`raven/core/lint.py`에서 `CORE_TAGS_FALLBACK = {...}` 블록(약 99-109줄) 바로 뒤에 추가:

```python
# ────────────────────────── 체크 레지스트리 (단일 소스, v0.8.1+) ──────────────────────────
#
# CLI(`raven lint summary`/`check`)와 API/대시보드가 각자 체크 이름·개수를
# 하드코딩해 발생한 drift(대시보드 14개 vs 실제 23개)를 근본 해결하기 위한
# 단일 소스. 새 check_* 함수를 추가할 때는 반드시 이 dict에도 등록할 것 —
# tests/test_lint_check_registry.py가 누락을 감지한다.
CHECK_REGISTRY: dict[str, dict] = {
    "#1":  {"name": "깨진 위키링크", "fn": None},
    "#2":  {"name": "깨진 의도 링크 오탐", "fn": None},
    "#3":  {"name": "누락된 위키링크", "fn": None},
    "#4":  {"name": "고아 문서", "fn": "check_orphans"},
    "#5":  {"name": "모순 감지", "fn": "check_contradictions"},
    "#6":  {"name": "신뢰도 낮음", "fn": "check_confidence_low"},
    "#7":  {"name": "오래된 문서", "fn": "check_stale"},
    "#8":  {"name": "문서 길이 초과", "fn": "check_page_size"},
    "#9":  {"name": "핵심 분류 밖 태그", "fn": "check_tag_audit"},
    "#10": {"name": "frontmatter 완전성", "fn": "check_frontmatter_completeness"},
    "#11": {"name": "index 완전성", "fn": "check_index_completeness"},
    "#12": {"name": "로그 크기 과다", "fn": "check_log_size"},
    "#13": {"name": "인지 거버넌스", "fn": "check_cognitive_governance"},
    "#14": {"name": "계층 무결성", "fn": "check_tier_integrity"},
    "#15": {"name": "slug-title 매칭", "fn": "check_slug_title_1to1"},
    "#16": {"name": "vault 성장률 이상", "fn": "check_vault_growth_rate"},
    "#17": {"name": "중복 제목 후보", "fn": "check_duplicate_title"},
    "#18": {"name": "감사 위반 패턴", "fn": "check_audit_violation_pattern"},
    "#19": {"name": "가이드 최신성", "fn": "check_guide_freshness"},
    "#20": {"name": "플레이스홀더 텍스트", "fn": "check_placeholder_text"},
    "#21": {"name": "맥락 없는 위키링크", "fn": "check_contextless_wikilinks"},
    "#22": {"name": "저널 요약 완전성", "fn": "check_journal_summary_completeness"},
    "#23": {"name": "의미 관계 무결성", "fn": "check_semantic_relations"},
}
```

- [x] **Step 4: `run_all()`에 `checks` 필드 embed**

`raven/core/lint.py`의 `run_all()` 함수에서 `return {` 블록(약 1157줄 부근, `"ok": counts["critical"] == 0,` 로 시작하는 부분) 을 찾아 수정:

```python
    return {
        "ok": counts["critical"] == 0,
        "vault": vault.meta.name,
        "counts": counts,
        "issues": issues,
        "by_check": by_check,
        "checks": {cid: meta["name"] for cid, meta in CHECK_REGISTRY.items()},
        # `wiki_lint`/run_all is intentionally read-only. Historical versions
        # auto-promoted stale draft issues here; keep the response key for
        # compatibility but do not mutate vault files from the linter path.
        "draft_promoted": 0,
    }
```

- [x] **Step 5: 테스트 실행해서 통과 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_lint_check_registry.py -v`
Expected: 3 passed

- [x] **Step 6: 기존 lint 테스트 전체가 여전히 통과하는지 확인**

Run: `scripts/.venv/bin/python -m pytest tests/ -k lint -v`
Expected: 모두 PASS (added-only 변경이므로 회귀 없어야 함)

- [x] **Step 7: 커밋**

```bash
git add raven/core/lint.py tests/test_lint_check_registry.py
git commit -m "$(cat <<'EOF'
feat(lint): CHECK_REGISTRY 단일 소스 추가

CLI/API/대시보드가 체크 이름·개수를 각자 하드코딩해 생긴 drift를 막기 위해
raven/core/lint.py에 단일 레지스트리를 두고 run_all()이 embed하도록 함.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: API 응답에 `checks` 필드 forward

**Files:**
- Modify: `raven/api/server.py:2879-2885` (`get_lint` 반환), `raven/api/server.py:2888-2898` (`get_lint_summary` 반환)
- Test: `tests/test_lint_api_checks_field.py` (신규)

**Interfaces:**
- Consumes: Task 1의 `lint_module.run_all(v)["checks"]`.
- Produces: `GET /api/vaults/{name}/lint` 및 `GET /api/vaults/{name}/lint/summary` 응답에 `"checks": dict[str, str]` 키.

- [x] **Step 1: 실패하는 테스트 작성**

기존 API 테스트가 FastAPI `TestClient`를 어떻게 쓰는지 확인 후(`tests/`에서 `from fastapi.testclient import TestClient` grep), 같은 패턴으로 `tests/test_lint_api_checks_field.py` 작성:

```python
"""GET /api/vaults/{name}/lint 및 .../lint/summary 응답에 checks 필드가 있는지 검증."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.vault import Vault


@pytest.fixture
def client(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-lintapi-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-lintapi-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    Vault.create("lintapi-test", target_root / "lintapi-test", bootstrap=False)
    from raven.api.server import app
    with TestClient(app) as c:
        yield c
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_get_lint_includes_checks_field(client):
    r = client.get("/api/vaults/lintapi-test/lint")
    assert r.status_code == 200
    body = r.json()
    assert "checks" in body
    assert body["checks"]["#4"] == "고아 문서"
    assert len(body["checks"]) == 23


def test_get_lint_summary_includes_checks_field(client):
    r = client.get("/api/vaults/lintapi-test/lint/summary")
    assert r.status_code == 200
    body = r.json()
    assert "checks" in body
    assert len(body["checks"]) == 23
```

- [x] **Step 2: 테스트 실행해서 실패 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_lint_api_checks_field.py -v`
Expected: FAIL — `assert "checks" in body` 에서 KeyError/AssertionError

- [x] **Step 3: `get_lint` 응답에 `checks` 추가**

`raven/api/server.py`의 `get_lint()` 함수 마지막 `return` 블록(2879-2885줄)을 수정:

```python
    return {
        "ok": result["ok"],
        "vault": name,
        "counts": result["counts"],
        "by_check": result["by_check"],
        "checks": result.get("checks", {}),
        "issues": issues,
    }
```

같은 함수 내 예외 처리 fallback dict(2852-2858줄)에도 `"checks": {}`를 추가:

```python
        result = {
            "ok": False,
            "counts": {"critical": 0, "warning": 0, "info": 0, "total": 0},
            "by_check": {},
            "checks": {},
            "issues": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
```

- [x] **Step 4: `get_lint_summary` 응답에 `checks` 추가**

`raven/api/server.py`의 `get_lint_summary()` 함수(2888-2898줄)를 수정:

```python
@app.get("/api/vaults/{name}/lint/summary")
def get_lint_summary(name: str):
    """23개 check별 통계 (빠른 헬스체크)."""
    v = _vault_or_404(name)
    result = lint_module.run_all(v)
    return {
        "ok": result["ok"],
        "vault": name,
        "counts": result["counts"],
        "by_check": result["by_check"],
        "checks": result.get("checks", {}),
    }
```

- [x] **Step 5: 테스트 실행해서 통과 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_lint_api_checks_field.py -v`
Expected: 2 passed

- [x] **Step 6: 기존 API 테스트 회귀 확인**

Run: `scripts/.venv/bin/python -m pytest tests/ -k "api and lint" -v`
Expected: 모두 PASS

- [x] **Step 7: 커밋**

```bash
git add raven/api/server.py tests/test_lint_api_checks_field.py
git commit -m "$(cat <<'EOF'
feat(api): lint 엔드포인트 응답에 checks 레지스트리 필드 forward

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: CLI `lint summary`/`lint check` 하드코딩 제거

**Files:**
- Modify: `raven/cli/__main__.py:1425-1493`
- Test: `tests/test_lint_cli_registry.py` (신규)

**Interfaces:**
- Consumes: `lint_module.CHECK_REGISTRY` (Task 1).
- Produces: 없음 (CLI 최종 소비자).

- [x] **Step 1: 실패하는 테스트 작성**

`tests/test_lint_cli_registry.py`:

```python
"""raven lint summary / raven lint check CLI가 CHECK_REGISTRY 23개를 전부 반영하는지 검증."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.cli.__main__ import app
from raven.core import lint as lint_module

runner = CliRunner()


@pytest.fixture
def fresh_env(monkeypatch):
    vaults_root = Path(tempfile.mkdtemp(prefix="raven-lintcli-vaults-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-lintcli-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(vaults_root))
    result = runner.invoke(app, [
        "vault", "create", "lintcli-test", str(target_root / "lintcli-test"),
        "--no-bootstrap",
    ])
    assert result.exit_code == 0, result.stderr
    yield
    shutil.rmtree(vaults_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_lint_summary_shows_all_registered_checks(fresh_env):
    result = runner.invoke(app, ["lint", "summary", "--vault", "lintcli-test"])
    assert result.exit_code == 0, result.stdout
    for cid in lint_module.CHECK_REGISTRY:
        assert cid in result.stdout, f"{cid} 가 lint summary 출력에 없음"


def test_lint_check_unsupported_link_based_check_gives_clear_message(fresh_env):
    result = runner.invoke(app, ["lint", "check", "#1", "--vault", "lintcli-test"])
    assert result.exit_code == 1
    assert "link_module" in result.stdout or "link_module" in result.stderr


def test_lint_check_runs_registered_function(fresh_env):
    result = runner.invoke(app, ["lint", "check", "#4", "--vault", "lintcli-test"])
    assert result.exit_code == 0, result.stdout
    assert "#4" in result.stdout
```

- [x] **Step 2: 테스트 실행해서 실패 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_lint_cli_registry.py -v`
Expected: FAIL — `test_lint_summary_shows_all_registered_checks`에서 `#15` 등이 출력에 없어 AssertionError

- [x] **Step 3: `lint summary`의 하드코딩된 range 교체**

`raven/cli/__main__.py`의 `lint_summary()` 함수(1425-1451줄)를 수정:

```python
@lint_app.command("summary")
def lint_summary(
    vault: Optional[str] = typer.Option(None, "--vault"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """check별 통계 (빠른 헬스체크)."""
    v = _resolve_vault_or_die(vault)
    result = lint_module.run_all(v)
    if json_out:
        typer.echo(json.dumps({
            "vault": result["vault"],
            "ok": result["ok"],
            "counts": result["counts"],
            "by_check": result["by_check"],
        }, indent=2, ensure_ascii=False))
        return
    c = result["counts"]
    typer.echo(f"📊 {result['vault']} lint summary:")
    typer.echo(f"   total:     {c['total']}")
    typer.echo(f"   critical:  {c['critical']} 🔴")
    typer.echo(f"   warning:   {c['warning']}  🟡")
    typer.echo(f"   info:      {c['info']}     🔵")
    typer.echo(f"\n   by check:")
    for cid in sorted(lint_module.CHECK_REGISTRY, key=lambda c: int(c[1:])):
        n = result["by_check"].get(cid, 0)
        bar = "█" * min(n, 20)
        typer.echo(f"     {cid}  {n:3d}  {bar}")
```

- [x] **Step 4: `lint check`의 `_CHECK_ID_TO_NAME` 버그 있는 매핑 제거**

`raven/cli/__main__.py`의 `lint_check()` 함수와 `_CHECK_ID_TO_NAME` 딕셔너리(1454-1493줄)를 통째로 교체:

```python
@lint_app.command("check")
def lint_check(
    check_id: str = typer.Argument(..., help="실행할 check id (예: #4)"),
    vault: Optional[str] = typer.Option(None, "--vault"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """특정 check 1개만 실행 (디버깅/타겟 검증)."""
    v = _resolve_vault_or_die(vault)
    meta = lint_module.CHECK_REGISTRY.get(check_id)
    if meta is None:
        typer.echo(
            f"❌ unknown check: {check_id}. "
            f"{', '.join(sorted(lint_module.CHECK_REGISTRY, key=lambda c: int(c[1:])))} 중 하나.",
            err=True,
        )
        raise typer.Exit(1)
    fn_name = meta.get("fn")
    if fn_name is None:
        typer.echo(
            f"❌ {check_id} ({meta['name']})는 link_module 기반이라 개별 실행을 "
            f"지원하지 않습니다 — `raven link check` 사용",
            err=True,
        )
        raise typer.Exit(1)
    fn = getattr(lint_module, fn_name)
    issues = fn(v)
    if json_out:
        typer.echo(json.dumps(issues, indent=2, ensure_ascii=False))
        return
    if not issues:
        typer.echo(f"✅ {check_id} ({meta['name']}): no issues")
        return
    typer.echo(f"🔍 {check_id} ({meta['name']}): {len(issues)} issues")
    for iss in issues:
        typer.echo(f"  [{iss.get('severity', '?'):8s}] {iss.get('slug', '?'):40s} {iss.get('message', '')}")
```

(이전의 모듈 레벨 `_CHECK_ID_TO_NAME = {...}` 딕셔너리 정의는 완전히 삭제 — 더 이상 참조하는 곳이 없다.)

- [x] **Step 5: `lint run`의 `--check` 도움말 문구, `lint_app` Typer 헬프, 섹션 주석의 오래된 개수 정리**

`raven/cli/__main__.py`에서:
- 1371줄: `help="특정 check만 (#1-#12)"` → `help="특정 check만 (예: #4)"`
- 1377줄: `"""vault에 대해 lint 18개 실행 (v0.7.109+)."""` → `"""vault에 대해 lint 전체 check 실행."""`
- 1415줄: `subject=f"lint 18개 ({c['critical']}C/{c['warning']}W/{c['info']}I)",` → `subject=f"lint {len(lint_module.CHECK_REGISTRY)}개 ({c['critical']}C/{c['warning']}W/{c['info']}I)",`
- 1365줄: `# ────────────────────────── lint (12 checks) ──────────────────────────` → `# ────────────────────────── lint (CHECK_REGISTRY 기반) ──────────────────────────`
- 38줄: `lint_app = typer.Typer(help="vault lint 18개 (v0.7.109+) — ...")` → `lint_app = typer.Typer(help="vault lint (raven.core.lint.CHECK_REGISTRY 참조) — broken/orphan/contradictions/stale/tier integrity/slug-title 1:1/growth/duplicate title/audit violation pattern 등.")`

- [x] **Step 6: 테스트 실행해서 통과 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_lint_cli_registry.py -v`
Expected: 3 passed

- [x] **Step 7: 전체 CLI 테스트 회귀 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_cli.py tests/test_lint_cli_registry.py -v`
Expected: 모두 PASS

- [x] **Step 8: 커밋**

```bash
git add raven/cli/__main__.py tests/test_lint_cli_registry.py
git commit -m "$(cat <<'EOF'
fix(cli): lint summary/check 하드코딩된 체크 목록을 CHECK_REGISTRY로 교체

raven lint summary가 #1-#13까지만 표시하던 것과, raven lint check의
_CHECK_ID_TO_NAME이 #1/#3을 둘 다 orphans로 잘못 매핑하고 #2,#14-#23이
빠져있던 버그를 CHECK_REGISTRY 참조로 근본 해결.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: 대시보드 `LintPage.tsx` 동적 렌더링

**Files:**
- Modify: `dashboard/src/lib/api.ts:246-259` (`LintResult`/`LintSummary` 타입)
- Modify: `dashboard/src/routes/LintPage.tsx:26-41` (`CHECK_NAMES` 제거), `:136`, `:189-235`, `:299-305`
- Test: `dashboard/tests/LintPage.dynamic-checks.contract.test.ts` (신규)

**Interfaces:**
- Consumes: API 응답의 `checks: Record<string, string>` 필드 (Task 2).
- Produces: 없음 (UI 최종 소비자). 기존 `dashboard/tests/LintPage.no-quickfix.contract.test.ts` 계약(`handleRebuild` 유지, quick-fix 관련 문자열 미포함)은 그대로 유지되어야 함.

- [x] **Step 1: 타입에 `checks` 필드 추가**

`dashboard/src/lib/api.ts`의 `LintResult`/`LintSummary` 인터페이스(246-259줄)를 수정:

```typescript
export interface LintResult {
  ok: boolean;
  vault: string;
  counts: Record<LintSeverity | "total", number>;
  by_check: Record<string, number>;
  checks: Record<string, string>;
  issues: LintIssue[];
}

export interface LintSummary {
  ok: boolean;
  vault: string;
  counts: Record<LintSeverity | "total", number>;
  by_check: Record<string, number>;
  checks: Record<string, string>;
}
```

- [x] **Step 2: 실패하는 계약 테스트 작성**

`dashboard/tests/LintPage.dynamic-checks.contract.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import LintPageSrc from "../src/routes/LintPage.tsx?raw";

describe("LintPage dynamic check registry contract", () => {
  it("does not hardcode a fixed check-id count for iteration", () => {
    expect(LintPageSrc).not.toMatch(/Array\.from\(\{\s*length:\s*(14|13|23)\s*\}/);
  });

  it("does not hardcode a static CHECK_NAMES map", () => {
    expect(LintPageSrc).not.toContain("CHECK_NAMES");
  });

  it("derives check names/order from summary.checks", () => {
    expect(LintPageSrc).toContain("summary?.checks");
  });

  it("keeps wiki.db rebuild as the only mutating toolbar action", () => {
    expect(LintPageSrc).toContain("wiki.db 리빌드");
    expect(LintPageSrc).toContain("handleRebuild");
  });
});
```

- [x] **Step 3: 테스트 실행해서 실패 확인**

Run: `cd dashboard && npx vitest run tests/LintPage.dynamic-checks.contract.test.ts`
Expected: FAIL — `CHECK_NAMES`가 여전히 존재, `Array.from({length:14}` 매치.

- [x] **Step 4: `CHECK_NAMES` 상수 제거 + 정렬 헬퍼 추가**

`dashboard/src/routes/LintPage.tsx`에서 26-41줄의 `CHECK_NAMES` 상수 정의를 통째로 삭제하고, 그 자리(파일 상단, `SEVERITY_LABELS` 정의 근처)에 정렬 헬퍼를 추가:

```typescript
function sortedCheckIds(checks: Record<string, string>): string[] {
  return Object.keys(checks).sort(
    (a, b) => Number(a.slice(1)) - Number(b.slice(1))
  );
}
```

- [x] **Step 5: 컴포넌트 본문에서 `summary.checks` 파생 변수 사용**

`LintPage()` 함수 본문, `return (` 이전에 다음을 추가:

```typescript
  const checkNames = summary?.checks ?? {};
  const checkIds = sortedCheckIds(checkNames);
```

- [x] **Step 6: 헤더 subtitle 동적화**

136줄:
```typescript
        subtitle="14개 lint check 결과 요약입니다."
```
→
```typescript
        subtitle={`${checkIds.length || ""}개 lint check 결과 요약입니다.`}
```

- [x] **Step 7: 체크별 이슈 분포 차트 루프 교체**

189줄 `{Array.from({ length: 14 }, (_, i) => \`#${i + 1}\`).map((cid) => {` 부터 이어지는 `.map` 블록을, `checkIds.map((cid) => {`로 시작하도록 교체 (블록 본문은 그대로 유지하되 `CHECK_NAMES[cid]` 참조를 전부 `checkNames[cid] ?? cid`로 바꾼다 — 레지스트리에 없는 미지의 id가 와도 최소한 원본 id는 표시):

```typescript
          {checkIds.map((cid) => {
            const n = summary.by_check[cid] || 0;
            const max = Math.max(...Object.values(summary.by_check), 1);
            const width = `${(n / max) * 100}%`;
            const isAccent = cid === "#1" || cid === "#2" || cid === "#11";
            const isActive = checkFilter === cid;
            return (
              <div
                key={cid}
                onClick={() => setCheckFilter(isActive ? "" : cid)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  marginBottom: 6,
                  fontSize: 13,
                  cursor: "pointer",
                  padding: "4px 8px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: isActive ? "var(--color-surface-soft, #f4f4f4)" : "transparent",
                  transition: "background-color 0.15s ease",
                }}
                className="hover-bg-soft"
                title={`${checkNames[cid] ?? cid} 필터링 토글 (${n}개)`}
              >
                <span
                  style={{
                    fontFamily: "ui-monospace, SFMono-Regular, monospace",
                    width: 32,
                    textAlign: "right",
                    color: "var(--color-muted)",
                  }}
                >
                  {cid}
                </span>
                <span
                  style={{
                    width: 192,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    color: "var(--color-body)",
                  }}
                >
                  {checkNames[cid] ?? cid}
                </span>
                <div
                  style={{
                    flex: 1,
                    background: "var(--color-surface-soft)",
                    borderRadius: 4,
                    height: 8,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width,
                      height: "100%",
                      background: isAccent
                        ? "var(--color-primary)"
                        : "var(--color-ink)",
                      transition: "width 0.2s ease",
                    }}
                    title={`${n} issues`}
                  />
                </div>
                <span
                  style={{
                    fontFamily: "ui-monospace, SFMono-Regular, monospace",
                    width: 40,
                    textAlign: "right",
                    color: "var(--color-ink)",
                  }}
                >
                  {n}
                </span>
              </div>
            );
          })}
```

- [x] **Step 8: 체크 필터 `<select>` 드롭다운 루프 교체**

기존 299-305줄 부근의:
```typescript
            <option value="">전체</option>
            {Array.from({ length: 14 }, (_, i) => `#${i + 1}`).map((cid) => (
              <option key={cid} value={cid}>
                {cid} {CHECK_NAMES[cid]}
              </option>
            ))}
```
을 다음으로 교체:
```typescript
            <option value="">전체</option>
            {checkIds.map((cid) => (
              <option key={cid} value={cid}>
                {cid} {checkNames[cid] ?? cid}
              </option>
            ))}
```

- [x] **Step 9: 테스트 실행해서 통과 확인**

Run: `cd dashboard && npx vitest run tests/LintPage.dynamic-checks.contract.test.ts tests/LintPage.no-quickfix.contract.test.ts`
Expected: 두 파일 모두 전체 PASS

- [x] **Step 10: 타입체크**

Run: `cd dashboard && npx tsc -b --noEmit`
Expected: 에러 없음 (특히 `LintPage.tsx`에서 `CHECK_NAMES` 미정의 참조가 남아있지 않은지 확인)

- [x] **Step 11: 커밋**

```bash
git add dashboard/src/lib/api.ts dashboard/src/routes/LintPage.tsx dashboard/tests/LintPage.dynamic-checks.contract.test.ts
git commit -m "$(cat <<'EOF'
fix(dashboard): LintPage가 백엔드 checks 레지스트리를 동적으로 반영하도록 수정

CHECK_NAMES 하드코딩(14개 고정) 및 Array.from({length:14}) 루프 2곳을 제거하고
API 응답의 checks 필드에서 이름/순회 목록을 파생하도록 변경. 이제 백엔드에
새 체크가 추가돼도 대시보드 코드 수정 없이 자동 반영됨.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: 전체 회귀 검증 (백엔드 + 프론트엔드)

**Files:** 없음 (검증 전용 태스크, 코드 변경 없음)

**Interfaces:**
- Consumes: Task 1-4 전체 산출물.
- Produces: 없음.

- [x] **Step 1: 전체 Python 테스트 스위트 실행**

Run: `scripts/.venv/bin/python -m pytest tests/ -q`
Expected: 전체 PASS, 실패 0건

- [x] **Step 2: 전체 dashboard 테스트 스위트 실행**

Run: `cd dashboard && npx vitest run`
Expected: 전체 PASS, 실패 0건

- [x] **Step 3: 대시보드 타입체크 + 빌드**

Run: `cd dashboard && npx tsc -b --noEmit && npm run build`
Expected: 에러 없음, `dist/` 생성 성공

- [x] **Step 4: 실제 vault로 CLI 수동 확인 (raven.sh 스택 없이, 격리된 임시 vault)**

```bash
scripts/.venv/bin/python - <<'EOF'
import tempfile, os
from pathlib import Path
os.environ["WIKI_VAULTS_DIR"] = tempfile.mkdtemp(prefix="raven-manual-check-")
from raven.core.vault import Vault
Vault.create("manual-check", Path(tempfile.mkdtemp(prefix="raven-manual-target-")) / "manual-check", bootstrap=False)
EOF
```

이어서 (같은 `WIKI_VAULTS_DIR` 값을 export한 셸에서):
```bash
raven lint summary --vault manual-check
```
Expected: `#1` 부터 `#23`까지 전부 출력됨 (13개에서 끊기지 않음).

- [x] **Step 5: 사용자에게 결과 보고**

다음을 포함해 보고 (AGENTS.md §12 형식):
- 무엇을 했는가: Task 1-4에서 수정한 5개 파일 + 신규 테스트 4개 파일 경로
- 왜 그렇게 했는가: 저장 신호 — 재사용성(향후 체크 추가 시 1곳만 수정) + 실패 기록(drift 버그 재발 방지 회귀 테스트)
- 검증: Step 1-4의 pytest/vitest/tsc/build 결과
- 다음에 무엇이 가능한가: per-check enable/disable 토글 UI, threshold 설정 UI, auto-fix 액션(이번 스코프 제외됨) 등 후속 후보

(커밋 없음 — 검증 전용 태스크)

---
