"""Tests for raven.core.digest — M5 F5 Dashboard Digest aggregator.

사람 운영자 진입 시 '오늘 vault 상태' 한 화면 요약. 단일 endpoint 가
log + lint + links + pages 를 일관된 payload 로 반환하는지 검증.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core import digest as digest_module
from raven.core.digest import compute_digest
from raven.core.frontmatter import render
from raven.core.log import append as log_append
from raven.core.vault import Vault


# ────────────────────────── fixtures ──────────────────────────


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-digest-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-digest-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("digest-test", target_root / "digest-test", bootstrap=False)
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def _write_page(v: Vault, slug: str, fm: dict, body: str = "# x\n") -> Path:
    fp = v.root / f"{slug}.md"
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(render(fm, body), encoding="utf-8")
    return fp


# ────────────────────────── shape ──────────────────────────


def test_digest_shape_keys(vault):
    """digest payload 가 약속된 키만 가짐 (front-end 가 기대하는 5개 section)."""
    d = compute_digest(vault)
    assert d["vault"] == vault.meta.name
    assert "generated_at" in d
    assert set(d.keys()) >= {
        "vault", "generated_at", "today", "this_week",
        "lint", "log_recent", "stats",
    }


def test_digest_lint_shape(vault):
    """lint sub-payload 가 ok/counts/by_check/top_issues 4개 키."""
    d = compute_digest(vault)
    lint = d["lint"]
    assert {"ok", "counts", "by_check", "top_issues"} <= set(lint.keys())
    for sev in ("critical", "warning", "info"):
        assert isinstance(lint["top_issues"][sev], list)


def test_digest_stats_shape(vault):
    """stats sub-payload 가 5개 카운트 키."""
    d = compute_digest(vault)
    s = d["stats"]
    for k in ("total_pages", "types", "recent_pages", "broken_links", "missing_links"):
        assert k in s, f"missing stats.{k}"


# ────────────────────────── aggregation ──────────────────────────


def test_digest_today_filters_correctly(vault):
    """today 섹션: 오늘 날짜 entry 만 포함."""
    today_iso = date.today().isoformat()
    log_append(vault, action="update", subject="marker-today", date_str=today_iso)
    d = compute_digest(vault)
    subjects = [e["subject"] for e in d["today"]]
    assert "marker-today" in subjects
    # 모든 today entry 가 오늘 날짜
    assert all(e["date"] == today_iso for e in d["today"])
    # 어제 entry 는 today 에 없음
    log_append(vault, action="update", subject="marker-yesterday",
               date_str=(date.today() - timedelta(days=1)).isoformat())
    d2 = compute_digest(vault)
    subjects2 = [e["subject"] for e in d2["today"]]
    assert "marker-yesterday" not in subjects2
    assert "marker-today" in subjects2


def test_digest_this_week_grouped_by_date(vault):
    """this_week: days=N 일 때 N개 entry, 각 entry 가 date/count/by_action 가짐."""
    log_append(vault, action="create", subject="a", date_str=(date.today() - timedelta(days=2)).isoformat())
    log_append(vault, action="update", subject="b", date_str=(date.today() - timedelta(days=2)).isoformat())
    log_append(vault, action="chore", subject="c", date_str=(date.today() - timedelta(days=3)).isoformat())
    d = compute_digest(vault, days=7)
    assert len(d["this_week"]) == 7
    # 2일 전: count=2 (create, update)
    bucket_2 = next(b for b in d["this_week"] if b["date"] == (date.today() - timedelta(days=2)).isoformat())
    assert bucket_2["count"] == 2
    assert bucket_2["by_action"].get("create") == 1
    assert bucket_2["by_action"].get("update") == 1
    # 3일 전: count=1 (chore)
    bucket_3 = next(b for b in d["this_week"] if b["date"] == (date.today() - timedelta(days=3)).isoformat())
    assert bucket_3["count"] == 1
    assert bucket_3["by_action"].get("chore") == 1


def test_digest_log_recent_is_descending(vault):
    """log_recent: 최신 entry 가 먼저 (reverse)."""
    log_append(vault, action="create", subject="old", date_str=(date.today() - timedelta(days=5)).isoformat())
    log_append(vault, action="update", subject="new", date_str=date.today().isoformat())
    d = compute_digest(vault)
    # 첫 entry 가 오늘 것 (latest first)
    assert d["log_recent"][0]["subject"] == "new"


def test_digest_stats_total_pages(vault):
    """total_pages: content_root .md 수."""
    _write_page(vault, "content/a", {"title": "A", "type": "concept"})
    _write_page(vault, "content/b", {"title": "B", "type": "person"})
    _write_page(vault, "content/c", {"title": "C", "type": "concept"})
    d = compute_digest(vault)
    assert d["stats"]["total_pages"] == 3
    assert d["stats"]["types"]["concept"] == 2
    assert d["stats"]["types"]["person"] == 1


def test_digest_recent_pages_sorted_by_updated(vault):
    """recent_pages: updated desc 정렬."""
    old = (date.today() - timedelta(days=10)).isoformat()
    new = date.today().isoformat()
    _write_page(vault, "content/old-page", {"title": "Old", "type": "concept", "updated": old})
    _write_page(vault, "content/new-page", {"title": "New", "type": "concept", "updated": new})
    d = compute_digest(vault)
    assert d["stats"]["recent_pages"][0]["slug"] == "content/new-page"
    assert len(d["stats"]["recent_pages"]) == 2


def test_digest_recent_pages_limit(vault):
    """recent_pages: 최대 5개."""
    for i in range(8):
        _write_page(
            vault,
            f"content/page-{i}",
            {"title": f"P{i}", "type": "concept", "updated": (date.today() - timedelta(days=i)).isoformat()},
        )
    d = compute_digest(vault)
    assert len(d["stats"]["recent_pages"]) == 5


def test_digest_broken_link_count(vault):
    """broken_links: 깨진 wikilink (path-style) 수.

    link_module.find_broken 는 target 에 '/' 가 있는 path-style 만 본다
    (bare [[name]] 은 자동 link, 무시).
    """
    _write_page(
        vault,
        "content/source",
        {"title": "Src", "type": "concept"},
        body="# S\n\nSee [[content/missing-1]] and [[content/missing-2]].",
    )
    d = compute_digest(vault)
    assert d["stats"]["broken_links"] >= 2


# ────────────────────────── boundaries ──────────────────────────


def test_digest_empty_vault_safe(vault):
    """페이지 없는 vault: log/lint/link 모두 zero 상태로 안전하게 반환.

    vault.create() 가 'vault created' log entry 를 자동 append 하므로
    today/log_recent 은 1개 entry, this_week 의 다른 day 는 모두 0.
    """
    d = compute_digest(vault)
    assert isinstance(d["today"], list)
    assert all(e["date"] == date.today().isoformat() for e in d["today"])
    assert len(d["this_week"]) == 7
    # 오늘을 제외한 모든 날짜는 0 count
    today_iso = date.today().isoformat()
    for bucket in d["this_week"]:
        if bucket["date"] != today_iso:
            assert bucket["count"] == 0
    assert d["stats"]["total_pages"] == 0
    assert d["stats"]["broken_links"] == 0
    assert d["stats"]["missing_links"] == 0


def test_digest_days_clamped(vault):
    """days < 1 → 1 로 보정, days > 30 → 30 으로 보정."""
    d = compute_digest(vault, days=0)
    assert len(d["this_week"]) == 1
    d = compute_digest(vault, days=999)
    assert len(d["this_week"]) == 30
    d = compute_digest(vault, days=-5)
    assert len(d["this_week"]) == 1


def test_digest_days_default_7(vault):
    """days 기본값 = 7."""
    d = compute_digest(vault)
    assert len(d["this_week"]) == 7


# ────────────────────────── API smoke ──────────────────────────


def test_digest_module_exported():
    """raven.core.digest_module 가 노출됨 (server.py 가 import 하므로 필수)."""
    import raven.core
    assert hasattr(raven.core, "digest_module")
    assert hasattr(raven.core.digest_module, "compute_digest")