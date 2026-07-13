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
    # Old page with no inbound links triggers #4 (orphan), #6 (low confidence), #7 (stale)
    assert ids == {"#4", "#6", "#7"}
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
    # Create mutually-linked pages so neither is orphaned, with distinct titles
    _write_page(
        root,
        "concept-foo",
        {
            "title": "Concepts of Foo",
            "type": "concept",
            "confidence": "high",
            "created": "2026-07-10",
            "updated": "2026-07-10",
        },
        "[[content/guide-bar]]",
    )
    _write_page(
        root,
        "guide-bar",
        {
            "title": "Guide to Bar",
            "type": "concept",
            "confidence": "high",
            "created": "2026-07-10",
            "updated": "2026-07-10",
        },
        "[[content/concept-foo]]",
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
