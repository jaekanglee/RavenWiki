# Semantic Lint Pass — 실행 메커니즘 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 새 read-only MCP tool `wiki_semantic_lint_queue`를 추가한다 — 기존 lint 신호 #4(orphan)/#5(contradiction)/#6(confidence low)/#7(stale)/#17(duplicate-title)/#20(placeholder)를 슬러그 단위로 그룹핑한 "판단이 필요한 후보 큐"를 반환하고, CURATION.md §1 결정트리(⛔/⚠️/✅ 판정)와 §3/§4 조치는 이 tool을 호출하는 외부 에이전트가 직접 수행하도록 한다.

**Architecture:** (1) `raven/mcp/tools/semantic_lint.py` — `lint.run_all(vault)`을 호출해 6개 허용 체크만 필터링하고 슬러그 단위로 그룹핑하는 순수 함수 `wiki_semantic_lint_queue(*, vault, checks=None, limit=20)`. `#17`(duplicate-title)의 `"slug_a ↔ slug_b"` 복합 slug 포맷만 분리해 양쪽에 `paired_with`를 붙인다. (2) `raven/mcp/cli.py::register_tools`에 이 함수를 감싸는 `@mcp.tool` 1개 추가 — 기존 `wiki_relations_list` 바로 뒤, `if mode in ("write","admin")` 블록 이전 (읽기 전용이라 모드 게이트 불필요).

**Tech Stack:** Python 3 / `raven.core.lint.run_all` / `raven.core.frontmatter` / FastMCP (`mcp.server.fastmcp`) / pytest

## Global Constraints

- 허용 체크 id는 정확히 `{"#4", "#5", "#6", "#7", "#17", "#20"}` 6개뿐이다 — 이 밖의 id를 `checks` 인자로 넘기면 `ValueError`로 즉시 실패시킨다 (design spec §3.3 Step 2, §5).
- CURATION.md §1의 ⛔/⚠️/✅ 결정트리 로직을 Python으로 재구현하지 않는다 — 응답에는 `guide_ref` 문자열 참조만 담는다 (design spec §3.3 Step 6, §7).
- 새 frontmatter 필드를 만들지 않는다 — 기존 `status`/`confidence`/`updated`/`sources` 4개만 후보 응답에 포함한다 (design spec §3.3 Step 4).
- `lint.py`의 `CHECK_REGISTRY`에 새 키를 추가하지 않는다 — 이 tool은 새 체크가 아니라 기존 체크의 뷰다 (design spec §6).
- 새 SQLite 테이블/상태 추적을 만들지 않는다 — 다음 `lint.run_all()` 재실행이 재판단 근거다 (design spec §4).
- 새 CLI 서브커맨드, 새 write MCP tool을 만들지 않는다 — MCP read tool 1개로 범위를 고정한다 (design spec §2, §7).

---

### Task 1: `raven/mcp/tools/semantic_lint.py` — 후보 큐 집계 함수

**Files:**
- Create: `raven/mcp/tools/semantic_lint.py`
- Test: `tests/test_mcp_semantic_lint_queue.py` (신규)

**Interfaces:**
- Consumes: `raven.core.lint.run_all(vault: Vault) -> dict` (기존, `result["issues"]`가 `{"id", "severity", "slug", "message"}` dict 리스트), `raven.core.registry.VaultMeta(name, path)`, `raven.core.vault.Vault(meta, root)`, `raven.core.frontmatter.parse(text) -> (dict, str)` (기존).
- Produces: `wiki_semantic_lint_queue(*, vault: Path, checks: Optional[list[str]] = None, limit: int = 20) -> dict`. Task 2가 이 함수를 그대로 MCP tool에서 호출한다.

- [x] **Step 1: 실패하는 테스트 작성**

`tests/test_mcp_semantic_lint_queue.py` 신규 생성:

```python
"""test_mcp_semantic_lint_queue.py — wiki_semantic_lint_queue 후보 큐 집계 검증.

이 tool은 판단하지 않는다 — CURATION.md §1이 참조하는 기존 lint 신호
(#4/#5/#6/#7/#17/#20)를 슬러그 단위로 그룹핑해 반환하기만 한다. 결정트리
적용은 호출한 에이전트의 책임이다 (2026-07-13 spec).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from raven.core.registry import VaultMeta
from raven.core.vault import Vault
from raven.mcp.tools.semantic_lint import (
    ALLOWED_CHECKS,
    wiki_semantic_lint_queue,
)


def _vault(tmp_path: Path, name: str = "lint-vault") -> Path:
    root = tmp_path / name
    (root / "content").mkdir(parents=True)
    (root / "_meta").mkdir()
    meta = VaultMeta(name=name, path=root)
    (root / ".vault.json").write_text(
        json.dumps(meta.to_json(), indent=2), encoding="utf-8"
    )
    return root


def _write_page(root: Path, slug: str, frontmatter: dict, body: str = "본문") -> None:
    from raven.core import frontmatter as core_frontmatter

    path = root / "content" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(core_frontmatter.render(frontmatter, body), encoding="utf-8")


def test_confidence_low_and_stale_grouped_on_same_slug(tmp_path: Path):
    root = _vault(tmp_path)
    _write_page(
        root,
        "weak-page",
        {
            "title": "Weak Page",
            "type": "concept",
            "confidence": "low",
            "created": "2020-01-01",
            "updated": "2020-01-01",
        },
    )

    result = wiki_semantic_lint_queue(vault=root)

    assert result["ok"] is True
    assert result["checks_considered"] == list(ALLOWED_CHECKS)
    matched = [c for c in result["candidates"] if c["slug"] == "content/weak-page"]
    assert len(matched) == 1
    cand = matched[0]
    ids = {chk["id"] for chk in cand["matched_checks"]}
    assert ids == {"#6", "#7"}
    assert cand["frontmatter"]["confidence"] == "low"
    assert cand["title"] == "Weak Page"


def test_checks_filter_narrows_candidates(tmp_path: Path):
    root = _vault(tmp_path)
    _write_page(
        root,
        "weak-page",
        {
            "title": "Weak Page",
            "type": "concept",
            "confidence": "low",
            "created": "2020-01-01",
            "updated": "2020-01-01",
        },
    )

    result = wiki_semantic_lint_queue(vault=root, checks=["#7"])

    assert result["checks_considered"] == ["#7"]
    cand = next(c for c in result["candidates"] if c["slug"] == "content/weak-page")
    ids = {chk["id"] for chk in cand["matched_checks"]}
    assert ids == {"#7"}


def test_disallowed_check_id_raises_value_error(tmp_path: Path):
    root = _vault(tmp_path)

    with pytest.raises(ValueError) as excinfo:
        wiki_semantic_lint_queue(vault=root, checks=["#9"])

    message = str(excinfo.value)
    for cid in ALLOWED_CHECKS:
        assert cid in message


def test_limit_truncates_and_flags(tmp_path: Path):
    root = _vault(tmp_path)
    for i in range(3):
        _write_page(
            root,
            f"weak-page-{i}",
            {
                "title": f"Weak Page {i}",
                "type": "concept",
                "confidence": "low",
                "created": "2026-07-01",
                "updated": "2026-07-01",
            },
        )

    result = wiki_semantic_lint_queue(vault=root, limit=2)

    assert result["candidate_count"] == 2
    assert len(result["candidates"]) == 2
    assert result["truncated"] is True


def test_no_candidates_is_not_an_error(tmp_path: Path):
    root = _vault(tmp_path)
    _write_page(
        root,
        "healthy-page",
        {
            "title": "Healthy Page",
            "type": "concept",
            "confidence": "high",
            "created": "2026-07-10",
            "updated": "2026-07-10",
        },
    )

    result = wiki_semantic_lint_queue(vault=root)

    assert result["ok"] is True
    assert result["candidate_count"] == 0
    assert result["candidates"] == []
    assert result["truncated"] is False


def test_duplicate_title_pair_gets_paired_with_on_both_sides(tmp_path: Path):
    root = _vault(tmp_path)
    _write_page(
        root,
        "python-guide",
        {
            "title": "Python 입문 가이드",
            "type": "concept",
            "created": "2026-07-01",
            "updated": "2026-07-01",
        },
    )
    _write_page(
        root,
        "python-guide-2",
        {
            "title": "Python 입문 가이드 2",
            "type": "concept",
            "created": "2026-07-01",
            "updated": "2026-07-01",
        },
    )

    result = wiki_semantic_lint_queue(vault=root, checks=["#17"])

    by_slug = {c["slug"]: c for c in result["candidates"]}
    assert set(by_slug) == {"content/python-guide", "content/python-guide-2"}
    a = by_slug["content/python-guide"]["matched_checks"][0]
    b = by_slug["content/python-guide-2"]["matched_checks"][0]
    assert a["id"] == "#17" and a["paired_with"] == "content/python-guide-2"
    assert b["id"] == "#17" and b["paired_with"] == "content/python-guide"
```

- [x] **Step 2: 테스트 실행해서 실패 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_mcp_semantic_lint_queue.py -v`
Expected: 전부 FAIL — `raven.mcp.tools.semantic_lint` 모듈이 없어 `ImportError`.

- [x] **Step 3: `raven/mcp/tools/semantic_lint.py` 구현**

```python
"""semantic_lint.py — wiki_semantic_lint_queue (read-only candidate aggregator).

CURATION.md §1 판정 기준(신호 테이블)이 참조하는 lint 신호(#4/#5/#6/#7/#17/#20)를
슬러그 단위로 모아 "판단이 필요한 후보 큐"를 만든다. 판단(⛔/⚠️/✅ 결정트리 적용)은
이 tool을 호출하는 외부 에이전트가 CURATION.md를 근거로 직접 수행한다 — 결정트리
로직은 여기서 재구현하지 않는다 (2026-07-13 spec).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from raven.core import frontmatter as core_frontmatter
from raven.core.lint import run_all
from raven.core.registry import VaultMeta
from raven.core.vault import Vault

ALLOWED_CHECKS: tuple[str, ...] = ("#4", "#5", "#6", "#7", "#17", "#20")

GUIDE_REF = "raven docs show agent-curation §1 (판정 기준 SoT — 결정트리는 여기서 재구현하지 않음)"

_FRONTMATTER_FIELDS: tuple[str, ...] = ("status", "confidence", "updated", "sources")

_PAIR_SEP = " ↔ "


def _frontmatter_for_slug(vault_root: Path, slug: str) -> dict:
    fp = vault_root / f"{slug}.md"
    if not fp.exists():
        return {}
    try:
        text = fp.read_text(encoding="utf-8")
    except OSError:
        return {}
    fm, _body = core_frontmatter.parse(text)
    return fm or {}


def _new_candidate(vault_root: Path, slug: str) -> dict:
    fm = _frontmatter_for_slug(vault_root, slug)
    title = fm.get("title")
    return {
        "slug": slug,
        "title": title if isinstance(title, str) else None,
        "frontmatter": {k: fm[k] for k in _FRONTMATTER_FIELDS if k in fm},
        "matched_checks": [],
    }


def wiki_semantic_lint_queue(
    *,
    vault: Path,
    checks: Optional[list[str]] = None,
    limit: int = 20,
) -> dict:
    """CURATION.md §1이 참조하는 lint 신호를 슬러그 단위로 모아 반환 (read-only).

    Args:
        vault: vault 루트 경로 (이미 resolve된 절대 경로).
        checks: 좁힐 체크 id 부분집합. 생략 시 ALLOWED_CHECKS 전부.
            허용목록 밖 id가 있으면 ValueError.
        limit: 반환할 최대 candidate 수. 초과분은 잘리고 truncated=True.

    Returns:
        {"ok", "vault", "checks_considered", "guide_ref",
         "candidate_count", "truncated", "candidates": [...]}
    """
    selected = list(checks) if checks is not None else list(ALLOWED_CHECKS)
    bad = [c for c in selected if c not in ALLOWED_CHECKS]
    if bad:
        raise ValueError(
            f"checks에 허용목록 밖 id가 있음: {bad}. "
            f"허용목록: {list(ALLOWED_CHECKS)}"
        )
    selected_set = set(selected)

    vault_obj = Vault(meta=VaultMeta(name=vault.name, path=vault), root=vault)
    result = run_all(vault_obj)
    issues = [iss for iss in result["issues"] if iss.get("id") in selected_set]

    grouped: dict[str, dict] = {}

    def _ensure(slug: str) -> dict:
        if slug not in grouped:
            grouped[slug] = _new_candidate(vault, slug)
        return grouped[slug]

    for iss in issues:
        raw_slug = iss.get("slug", "")
        check_entry = {
            "id": iss.get("id"),
            "severity": iss.get("severity"),
            "message": iss.get("message"),
        }
        if iss.get("id") == "#17" and _PAIR_SEP in raw_slug:
            slug_a, slug_b = [s.strip() for s in raw_slug.split(_PAIR_SEP, 1)]
            entry_a = dict(check_entry)
            entry_a["paired_with"] = slug_b
            _ensure(slug_a)["matched_checks"].append(entry_a)
            entry_b = dict(check_entry)
            entry_b["paired_with"] = slug_a
            _ensure(slug_b)["matched_checks"].append(entry_b)
        else:
            _ensure(raw_slug)["matched_checks"].append(check_entry)

    candidates = sorted(grouped.values(), key=lambda c: c["slug"])
    truncated = len(candidates) > limit
    candidates = candidates[:limit]

    return {
        "ok": True,
        "vault": vault_obj.meta.name,
        "checks_considered": selected,
        "guide_ref": GUIDE_REF,
        "candidate_count": len(candidates),
        "truncated": truncated,
        "candidates": candidates,
    }
```

- [x] **Step 4: 테스트 실행해서 통과 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_mcp_semantic_lint_queue.py -v`
Expected: 6개 전부 PASS.

- [x] **Step 5: 커밋**

```bash
git add raven/mcp/tools/semantic_lint.py tests/test_mcp_semantic_lint_queue.py
git commit -m "feat(mcp): wiki_semantic_lint_queue 후보 큐 집계 함수 추가

CURATION.md §1이 참조하는 lint 신호(#4/#5/#6/#7/#17/#20)를 슬러그 단위로
그룹핑해 반환. 결정트리(⛔/⚠️/✅) 판정은 재구현하지 않고 참조만 남겨,
실제 판단은 호출하는 외부 에이전트가 수행하도록 한다."
```

---

### Task 2: `raven/mcp/cli.py`에 `wiki_semantic_lint_queue` MCP tool 등록

**Files:**
- Modify: `raven/mcp/cli.py:284-299` (기존 `wiki_relations_list` 블록 바로 뒤, `# ─── 6. wiki_update (write / admin) ───` 앞)
- Test: `tests/test_mcp_semantic_lint_queue.py` (Task 1에서 만든 파일에 통합 테스트 추가)

**Interfaces:**
- Consumes: Task 1의 `raven.mcp.tools.semantic_lint.wiki_semantic_lint_queue(*, vault, checks, limit)`, 기존 `resolve_vault_path(vault: str) -> Path`, 기존 `register_tools(mcp: Any, mode: str) -> None`.
- Produces: MCP tool 이름 `"wiki_semantic_lint_queue"` — 이후 다른 태스크가 참조하지 않음 (본 계획의 마지막 태스크).

- [x] **Step 1: 실패하는 통합 테스트 작성**

`tests/test_mcp_semantic_lint_queue.py`에 다음을 append (기존 import 블록 아래에 추가 import 필요):

```python
import asyncio

from mcp.server.fastmcp.exceptions import ToolError

from raven.mcp.cli import register_tools


def _call_tool_result(mcp: FastMCP, name: str, arguments: dict):
    """FastMCP의 `call_tool` 반환 shape을 원래 값으로 정규화.

    tests/test_mcp_multi_vault.py의 동일 헬퍼와 같은 정규화 규칙.
    """
    result = asyncio.run(mcp.call_tool(name, arguments))
    if isinstance(result, tuple):
        _, structured = result
        return structured["result"]
    return json.loads(result[0].text)


def test_tool_registered_and_reachable_by_vault_name(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path))
    from raven.core.registry import VaultRegistry

    root = _vault(tmp_path, name="reg-vault")
    _write_page(
        root,
        "weak-page",
        {
            "title": "Weak Page",
            "type": "concept",
            "confidence": "low",
            "created": "2020-01-01",
            "updated": "2020-01-01",
        },
    )
    reg = VaultRegistry(root=tmp_path)
    reg.add(VaultMeta(name="reg-vault", path=root))

    mcp = FastMCP("wiki")
    register_tools(mcp, "read")

    payload = _call_tool_result(
        mcp, "wiki_semantic_lint_queue", {"vault": "reg-vault"}
    )

    assert payload["ok"] is True
    slugs = {c["slug"] for c in payload["candidates"]}
    assert "content/weak-page" in slugs


def test_tool_rejects_disallowed_check_id_as_tool_error(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path))
    from raven.core.registry import VaultRegistry

    root = _vault(tmp_path, name="reg-vault-2")
    reg = VaultRegistry(root=tmp_path)
    reg.add(VaultMeta(name="reg-vault-2", path=root))

    mcp = FastMCP("wiki")
    register_tools(mcp, "read")

    with pytest.raises(ToolError) as excinfo:
        asyncio.run(
            mcp.call_tool(
                "wiki_semantic_lint_queue",
                {"vault": "reg-vault-2", "checks": ["#9"]},
            )
        )

    message = str(excinfo.value)
    for cid in ALLOWED_CHECKS:
        assert cid in message
```

- [x] **Step 2: 테스트 실행해서 실패 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_mcp_semantic_lint_queue.py -v`
Expected: Task 1의 6개는 PASS, 새로 추가한 2개는 FAIL — `"wiki_semantic_lint_queue"`가 아직 등록되지 않아 `ToolError: Unknown tool` 류로 실패.

- [x] **Step 3: `raven/mcp/cli.py`에 tool 등록**

파일 상단 import 블록(38번째 줄 근처, `from raven.mcp.tools import stale as stale_tools` 바로 아래)에 추가:

```python
from raven.mcp.tools import stale as stale_tools  # ADR-2026-07-06 §1.3 신규 도구
from raven.mcp.tools import semantic_lint as semantic_lint_tools  # 2026-07-13 spec
```

다음 블록(기존 `wiki_relations_list` 정의, `raven/mcp/cli.py:285-298`)을 찾는다:

```python
    # ─── 7.6. wiki_relations_list ───
    @mcp.tool(
        name="wiki_relations_list",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "List semantic relations, optionally filtered by source slug or type."
        ),
    )
    def wiki_relations_list(
        vault: str,
        slug: Optional[str] = None,
        relation_type: Optional[str] = None,
    ) -> list[dict]:
        ctx = VaultContext(vault=resolve_vault_path(vault), mode=permission_mode)
        return read_tools.wiki_relations_list(slug=slug, relation_type=relation_type, ctx=ctx)

    # ─── 6. wiki_update (write / admin) ───
```

그 사이(`wiki_relations_list` 함수 정의 끝 ~ `# ─── 6. wiki_update` 주석 사이)에 다음을 삽입:

```python
    # ─── 7.7. wiki_semantic_lint_queue (2026-07-13 spec) ───
    @mcp.tool(
        name="wiki_semantic_lint_queue",
        description=(
            EXPERIMENTAL_PREFIX + VAULT_ARG_NOTE
            + "Read-only candidate queue for CURATION.md §1's pre-compile "
            + "source-vetting decision tree. Groups existing lint signals "
            + "#4 (orphan) / #5 (contradiction) / #6 (confidence low) / #7 "
            + "(stale) / #17 (duplicate-title) / #20 (placeholder) by slug. "
            + "Does NOT apply the decision tree itself — see `raven docs show "
            + "agent-curation` §1 for the criteria; the calling agent applies it "
            + "and writes verdicts back via wiki_update / wiki_generate_draft."
        ),
    )
    def wiki_semantic_lint_queue(
        vault: str,
        checks: Optional[list[str]] = None,
        limit: int = 20,
    ) -> dict:
        return semantic_lint_tools.wiki_semantic_lint_queue(
            vault=resolve_vault_path(vault), checks=checks, limit=limit,
        )
```

- [x] **Step 4: 테스트 실행해서 통과 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_mcp_semantic_lint_queue.py -v`
Expected: 8개 전부 PASS.

- [x] **Step 5: 전체 회귀 테스트 실행**

Run: `scripts/.venv/bin/python -m pytest tests/ -q`
Expected: 기존 테스트 스위트 전부 PASS, 신규 8개 포함해 총 개수 증가. 실패 시 원인 파악 후 수정 (특히 `raven/mcp/cli.py` import 순서/순환import 여부 확인).

- [x] **Step 6: 커밋**

```bash
git add raven/mcp/cli.py tests/test_mcp_semantic_lint_queue.py
git commit -m "feat(mcp): wiki_semantic_lint_queue를 MCP read tool로 등록

wiki_relations_list 뒤에 배치, write/admin 게이트 없이 read 모드에서도
사용 가능 (읽기 전용). 응답의 guide_ref가 raven docs show agent-curation
§1을 참조하도록 하여 판정 기준의 단일 소스를 CURATION.md로 유지한다."
```

---

## 완료 조건

- `wiki_semantic_lint_queue(vault, checks=None, limit=20)`이 lint #4/#5/#6/#7/#17/#20 신호를 슬러그 단위로 그룹핑해 반환한다.
- 허용목록 밖 `checks` id 요청 시 CLI 레벨(`ValueError`)과 MCP 레벨(`ToolError`) 양쪽에서 명확히 실패한다.
- `#17` duplicate-title 쌍은 양쪽 슬러그 모두에 `paired_with`가 채워진 candidate로 나타난다.
- `limit` 초과 시 `truncated: true`가 정확히 반환되고 결과가 조용히 잘리지 않는다.
- candidate 0개인 vault에서도 에러 없이 정상 응답한다.
- `raven/core/lint.py`의 `CHECK_REGISTRY`와 `tests/test_lint_check_registry.py`는 변경되지 않는다.
- `tests/` 전체 스위트가 회귀 없이 통과한다.
