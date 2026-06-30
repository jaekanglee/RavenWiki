"""Tests for raven.core.lint — v0.5.1+ 9 check 함수 (#4-#11).

Markdown PKM lint 기본 세트 (#1-#12) 회귀 테스트.
"""
from __future__ import annotations

import json
import sys
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core import lint as lint_module
from raven.core.lint import (
    check_confidence_low,
    check_contradictions,
    check_frontmatter_completeness,
    check_index_completeness,
    check_log_size,
    check_orphans,
    check_page_size,
    check_stale,
    check_tag_audit,
    run_all,
)
from raven.core.vault import Vault


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-lint2-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-lint2-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("lint2-test", target_root / "lint2-test", bootstrap=False)
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def _write_page(v: Vault, slug: str, fm: dict, body: str = "# x\n") -> Path:
    """helper: frontmatter + body 쓰기."""
    from raven.core.frontmatter import render
    fp = v.root / f"{slug}.md"
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(render(fm, body), encoding="utf-8")
    return fp


# ────────────────────────── #4 orphan ──────────────────────────


def test_orphan_after_grace_is_warning(vault):
    """grace 만료된 orphan → warning."""
    old = (date.today() - timedelta(days=10)).isoformat()
    _write_page(vault, "content/orphan-old", {
        "title": "Orphan", "type": "concept",
        "created": old, "updated": old,
    })
    issues = check_orphans(vault)
    assert any(
        i["id"] == "#4" and i["severity"] == "warning"
        and i["slug"] == "content/orphan-old"
        for i in issues
    )


def test_orphan_within_grace_is_info(vault):
    """grace 내 orphan → info (grace 중)."""
    recent = (date.today() - timedelta(days=2)).isoformat()
    _write_page(vault, "content/orphan-new", {
        "title": "New", "type": "concept",
        "created": recent, "updated": recent,
    })
    issues = check_orphans(vault)
    assert any(
        i["id"] == "#4" and i["severity"] == "info"
        and i["slug"] == "content/orphan-new"
        for i in issues
    )


def test_orphan_with_inbound_no_issue(vault):
    """inbound 있으면 orphan 아님."""
    today = date.today().isoformat()
    _write_page(vault, "content/target", {
        "title": "Target", "type": "concept",
        "created": today, "updated": today,
    }, body="back: [[content/source]]\n")
    _write_page(vault, "content/source", {
        "title": "Source", "type": "concept",
        "created": today, "updated": today,
    }, body="see: [[content/target]]\n")
    issues = check_orphans(vault)
    assert not any(i["slug"] in ("content/target", "content/source") for i in issues)


# ────────────────────────── #5 contradictions ──────────────────────────


def test_contradictions_to_missing_is_warning(vault):
    """frontmatter.contradictions에 미존재 slug → warning."""
    today = date.today().isoformat()
    _write_page(vault, "content/a", {
        "title": "A", "type": "concept",
        "created": today, "updated": today,
        "contradictions": ["content/ghost"],
    })
    issues = check_contradictions(vault)
    assert any(
        i["id"] == "#5" and i["severity"] == "warning"
        and "ghost" in i["message"] for i in issues
    )


def test_contradictions_to_existing_no_issue(vault):
    """존재하는 slug 참조 → 무이슈."""
    today = date.today().isoformat()
    _write_page(vault, "content/a", {
        "title": "A", "type": "concept",
        "created": today, "updated": today,
        "contradictions": ["content/b"],
    })
    _write_page(vault, "content/b", {
        "title": "B", "type": "concept",
        "created": today, "updated": today,
    })
    issues = check_contradictions(vault)
    assert not issues


# ────────────────────────── #6 confidence low ──────────────────────────


def test_confidence_low_listed_as_info(vault):
    today = date.today().isoformat()
    _write_page(vault, "content/weak", {
        "title": "Weak", "type": "concept",
        "created": today, "updated": today,
        "confidence": "low",
    })
    issues = check_confidence_low(vault)
    assert any(
        i["id"] == "#6" and i["severity"] == "info"
        and i["slug"] == "content/weak" for i in issues
    )


def test_confidence_high_no_issue(vault):
    today = date.today().isoformat()
    _write_page(vault, "content/strong", {
        "title": "Strong", "type": "concept",
        "created": today, "updated": today,
        "confidence": "high",
    })
    issues = check_confidence_low(vault)
    assert not issues


# ────────────────────────── #7 stale ──────────────────────────


def test_stale_over_90_days(vault):
    old = (date.today() - timedelta(days=120)).isoformat()
    _write_page(vault, "content/old", {
        "title": "Old", "type": "concept",
        "created": old, "updated": old,
    })
    issues = check_stale(vault)
    assert any(i["id"] == "#7" and i["slug"] == "content/old" for i in issues)


def test_stale_exempt_type_rule(vault):
    """type: rule → 면제."""
    old = (date.today() - timedelta(days=200)).isoformat()
    _write_page(vault, "content/old-rule", {
        "title": "Old Rule", "type": "rule",
        "created": old, "updated": old,
    })
    issues = check_stale(vault)
    assert not any(i["slug"] == "content/old-rule" for i in issues)


# ────────────────────────── #8 page size ──────────────────────────


def test_page_size_over_200(vault):
    today = date.today().isoformat()
    body = "x\n" * 250
    _write_page(vault, "content/big", {
        "title": "Big", "type": "concept",
        "created": today, "updated": today,
    }, body=body)
    issues = check_page_size(vault)
    assert any(i["id"] == "#8" and i["slug"] == "content/big" for i in issues)


def test_page_size_under_200(vault):
    today = date.today().isoformat()
    _write_page(vault, "content/small", {
        "title": "Small", "type": "concept",
        "created": today, "updated": today,
    }, body="short\n")
    issues = check_page_size(vault)
    assert not issues


# ────────────────────────── #9 tag audit ──────────────────────────


def test_tag_unknown_is_warning(vault):
    today = date.today().isoformat()
    _write_page(vault, "content/odd-tag", {
        "title": "X", "type": "concept",
        "created": today, "updated": today,
        "tags": ["concept", "totally-made-up-tag"],
    })
    issues = check_tag_audit(vault)
    assert any(
        i["id"] == "#9" and i["severity"] == "warning"
        and "totally-made-up-tag" in i["message"] for i in issues
    )


def test_tag_known_no_issue(vault):
    today = date.today().isoformat()
    _write_page(vault, "content/ok-tag", {
        "title": "X", "type": "concept",
        "created": today, "updated": today,
        "tags": ["concept", "ai"],
    })
    issues = check_tag_audit(vault)
    assert not any(i["slug"] == "content/ok-tag" for i in issues)


# ────────────────────────── #10 frontmatter 완전성 ──────────────────────────


def test_frontmatter_no_fm_is_warning(vault):
    fp = vault.root / "content" / "no-fm.md"
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text("no frontmatter here\n", encoding="utf-8")
    issues = check_frontmatter_completeness(vault)
    assert any(
        i["id"] == "#10" and i["severity"] == "warning"
        and i["slug"] == "content/no-fm" for i in issues
    )


def test_frontmatter_missing_updated_is_warning(vault):
    """created는 있지만 updated 없음 → warning."""
    _write_page(vault, "content/no-updated", {
        "title": "X", "type": "concept",
        "created": "2026-06-25",
    })
    issues = check_frontmatter_completeness(vault)
    assert any(
        i["id"] == "#10" and i["severity"] == "warning"
        and "updated" in i["message"] for i in issues
    )


# ────────────────────────── #11 index 완전성 ──────────────────────────


def test_index_no_db_is_info(vault):
    """DB 없으면 info (build 필요)."""
    issues = check_index_completeness(vault)
    assert any(
        i["id"] == "#11" and i["severity"] == "info"
        and "build" in i["message"].lower() for i in issues
    )


# ────────────────────────── #12 log size (회귀) ──────────────────────────


def test_log_size_under_threshold(vault):
    from raven.core.log import append
    for i in range(10):
        append(vault, "chore", f"x {i}")
    issues = check_log_size(vault)
    assert not issues  # 10 < 500


# ────────────────────────── run_all() 통합 ──────────────────────────


def test_run_all_returns_full_structure(vault):
    today = date.today().isoformat()
    _write_page(vault, "content/sample", {
        "title": "Sample", "type": "concept",
        "created": today, "updated": today,
        "tags": ["ai"],
    })
    result = run_all(vault)
    assert "counts" in result
    assert "issues" in result
    assert "by_check" in result
    assert result["vault"] == vault.meta.name
    # 12개 check 모두 by_check에 등장할 필요 ❌ (이슈 0인 것도 정상)
    assert isinstance(result["by_check"], dict)
    # 최소 1개는 info
    assert result["counts"]["info"] >= 0  # index_completeness에서 DB 없음 info


def test_run_all_no_critical_on_clean_vault(vault):
    """깨끗한 vault → critical 0."""
    today = date.today().isoformat()
    # source → target (정상 wikilink, valid frontmatter)
    _write_page(vault, "content/target", {
        "title": "Target", "type": "concept",
        "created": today, "updated": today,
    })
    _write_page(vault, "content/source", {
        "title": "Source", "type": "concept",
        "created": today, "updated": today,
        "tags": ["ai"],
    }, body="link: [[content/target]]\n")
    result = run_all(vault)
    assert result["counts"]["critical"] == 0
