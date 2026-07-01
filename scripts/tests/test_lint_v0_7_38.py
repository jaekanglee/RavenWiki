"""v0.7.38+ — two new lint rules (detect-only).

Rule #17 (info): wikilink-format-consistency
    Surfaces wikilinks that use the bare `[[foo]]` form without a
    vault-relative prefix (`content/`, `_meta/`, etc.). Multi-author
    vaults can drift between short- and long-form usage; this rule
    surfaces the count + a sample so authors can decide whether to
    align. **Detect-only**: no silent auto-rewrite (that would
    violate user intent and is judged too domain-specific to bake
    into raven core).

Rule #18 (warning): log-append-rollback
    Surfaces time-reversed entries inside `<vault>/log.md`. Raven's
    append-only invariant (v0.7.20+ FileLock-protected writes) is
    silently violated when someone rewrites a portion of the file.
    This rule flags it so the operator notices.
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

# Make `scripts` importable as a package root so `scripts.lint` resolves.
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lint import _lint_all, Issue  # noqa: E402  (path injection above)


# ────────────────────────── helpers ──────────────────────────


def _make_db_with_pages(pages: list[dict]) -> sqlite3.Connection:
    """Spin up a sqlite3.Connection with wiki.db-compatible schema
    and the given pages. Path column = vault-relative.

    `pages` is a list of dicts with at least: {slug, path, content}.
    Other columns get sensible defaults so existing rules don't trip.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE pages (
            id INTEGER PRIMARY KEY,
            slug TEXT,
            path TEXT,
            title TEXT,
            type TEXT,
            created TEXT,
            updated TEXT,
            content TEXT,
            raw_content TEXT,
            frontmatter TEXT,
            outbound_count INTEGER DEFAULT 0,
            inbound_count INTEGER DEFAULT 0,
            contested INTEGER DEFAULT 0
        );
        CREATE TABLE links (
            id INTEGER PRIMARY KEY,
            source_slug TEXT,
            source_title TEXT,
            target_slug TEXT,
            target_title TEXT,
            intent TEXT,
            context TEXT
        );
        CREATE TABLE tags (
            id INTEGER PRIMARY KEY,
            page_slug TEXT,
            tag TEXT
        );
        """
    )
    today = date.today().isoformat()
    for p in pages:
        conn.execute(
            "INSERT INTO pages (slug, path, title, type, created, updated, content, raw_content, frontmatter, outbound_count, inbound_count, contested) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                p["slug"],
                p.get("path", f"content/{p['slug']}.md"),
                p.get("title", p["slug"]),
                p.get("type", "concept"),
                p.get("created", today),
                p.get("updated", today),
                p.get("content", ""),
                p.get("content", ""),  # raw_content mirrors content for tests
                p.get("frontmatter", ""),
                p.get("outbound_count", 0),
                p.get("inbound_count", 1),  # default non-zero so orphan rule skips
                p.get("contested", 0),
            ),
        )
    return conn


def _issues_for(pages: list[dict], vault_root: Path | None) -> list[Issue]:
    conn = _make_db_with_pages(pages)
    issues = _lint_all(conn, vault_root=vault_root)
    return [i for i in issues if i.rule in {"wikilink-format-consistency", "log-append-rollback"}]


# ────────────────────────── Rule #17: wikilink-format-consistency ──────────────────────────


def test_rule17_no_short_form_no_issue() -> None:
    """All wikilinks are long-form (have 'content/' prefix). → no Rule #17 issue."""
    pages = [
        {
            "slug": "a",
            "path": "content/a.md",
            "content": "see [[content/b]] and [[content/c]] for context.",
        }
    ]
    assert _issues_for(pages, vault_root=None) == []


def test_rule17_short_form_emits_info() -> None:
    """Bare [[foo]] form present → Rule #17 info issue surfaces with sample."""
    pages = [
        {
            "slug": "a",
            "path": "content/a.md",
            "content": "see [[b]] and [[c]] for context.",
        }
    ]
    issues = _issues_for(pages, vault_root=None)
    assert len(issues) == 1
    issue = issues[0]
    assert issue.rule == "wikilink-format-consistency"
    assert issue.severity == "info"
    assert issue.path == "(vault)"
    assert "2 short-form wikilink" in issue.message
    # Sample must include the bare targets
    assert "[[b]]" in issue.message
    assert "[[c]]" in issue.message


def test_rule17_long_form_with_intent_still_passes() -> None:
    """Intent-marked long-form wikilinks do not trigger the rule."""
    pages = [
        {
            "slug": "a",
            "path": "content/a.md",
            "content": "see [[content/b]]! for broken, [[content/c]]? for missing.",
        }
    ]
    assert _issues_for(pages, vault_root=None) == []


def test_rule17_sample_cap_at_five() -> None:
    """Even with 50 short-form links, the message shows ≤5 samples + overflow hint."""
    pages = [
        {
            "slug": "a",
            "path": "content/a.md",
            "content": " ".join(f"[[link{i}]]" for i in range(50)),
        }
    ]
    issues = _issues_for(pages, vault_root=None)
    assert len(issues) == 1
    msg = issues[0].message
    assert "50 short-form wikilink" in msg
    assert "(+45 more)" in msg
    # Exactly 5 sampled links are listed
    samples = re.findall(r"\[\[link\d+\]\]", msg)
    assert len(samples) == 5


def test_rule17_skips_url_like_targets() -> None:
    """URL-prefixed brackets (`[[http://...]]`) are not surface-area."""
    pages = [
        {
            "slug": "a",
            "path": "content/a.md",
            "content": "see [[https://example.com]] here.",
        }
    ]
    assert _issues_for(pages, vault_root=None) == []


def test_rule17_url_only_short_form_still_flagged() -> None:
    """A short URL bare (`[[example.com]]` without https://) still counts."""
    pages = [
        {
            "slug": "a",
            "path": "content/a.md",
            "content": "weird [[example.com]] link here",
        }
    ]
    issues = _issues_for(pages, vault_root=None)
    assert len(issues) == 1
    assert "1 short-form wikilink" in issues[0].message


# ────────────────────────── Rule #18: log-append-rollback ──────────────────────────


def test_rule18_no_log_no_issue() -> None:
    """No log.md present → no Rule #18 issue (and don't 500)."""
    pages = [{"slug": "a", "path": "content/a.md"}]
    with tempfile.TemporaryDirectory() as tmp:
        # No log.md in tmp
        issues = _issues_for(pages, vault_root=Path(tmp))
        assert issues == []


def test_rule18_monotonic_log_no_issue() -> None:
    """Chronologically ordered log → no Rule #18 issue."""
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        log_text = "\n".join(
            f"## [{d}] update | page X" for d in ["2026-06-29", "2026-06-30", "2026-07-01"]
        ) + "\n"
        (vault_root / "log.md").write_text(log_text, encoding="utf-8")
        pages = [{"slug": "x", "path": "content/x.md"}]
        issues = _issues_for(pages, vault_root=vault_root)
        assert issues == []


def test_rule18_reversed_entry_emits_warning() -> None:
    """A time-reversed entry (later line has earlier date) → WARNING."""
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        log_text = "\n".join(
            f"## [{d}] update | page X" for d in ["2026-06-29", "2026-07-01", "2026-06-30"]
        ) + "\n"
        (vault_root / "log.md").write_text(log_text, encoding="utf-8")
        pages = [{"slug": "x", "path": "content/x.md"}]
        issues = _issues_for(pages, vault_root=vault_root)
        assert len(issues) == 1
        issue = issues[0]
        assert issue.rule == "log-append-rollback"
        assert issue.severity == "warning"
        assert issue.path == "log.md"
        assert "1 time-reversed entry" in issue.message
        assert "[2026-06-30] after [2026-07-01]" in issue.message


def test_rule18_multiple_reversals_sampled() -> None:
    """Multiple reversals: message shows ≤3 samples + overflow hint."""
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        # 7-entry pattern producing 4 reversals:
        #   i=0: 07-01
        #   i=1: 07-02 (upgrade)
        #   i=2: 07-01 (reversal 1)
        #   i=3: 07-02 (upgrade)
        #   i=4: 07-01 (reversal 2)
        #   i=5: 07-02 (upgrade)
        #   i=6: 07-01 (reversal 3)... wait, len=7 → 6 comparisons
        # Recompute: alternating between 07-01 and 07-02 of odd length 7:
        #   [07-01, 07-02, 07-01, 07-02, 07-01, 07-02, 07-01]
        #   i=1: upgrade; i=2: reversal; i=3: upgrade; i=4: reversal;
        #   i=5: upgrade; i=6: reversal → 3 reversals. Below 4.
        # Use a longer trigger: insert a single "today" entry at the end
        # so the last comparison also has a reversal.
        log_text = "\n".join(
            f"## [{d}] update | p" for d in [
                "2026-06-30",  # baseline
                "2026-07-02", "2026-07-01",
                "2026-07-02", "2026-07-01",
                "2026-07-02", "2026-07-01",
            ]
        ) + "\n"
        (vault_root / "log.md").write_text(log_text, encoding="utf-8")
        pages = [{"slug": "p", "path": "content/p.md"}]
        issues = _issues_for(pages, vault_root=vault_root)
        assert len(issues) == 1
        msg = issues[0].message
        assert "3 time-reversed" in msg
        # 3 reversals, equals sample cap → exactly 3 samples, no overflow suffix.
        assert "(+" not in msg
        samples = re.findall(r"line \d+:", msg)
        assert len(samples) == 3


def test_rule18_overflow_above_cap() -> None:
    """When the reversal count exceeds the sample cap, overflow hint shown."""
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        # Build 5 reversals: 07-01 (baseline) → 5 alternating pairs that
        # always end on the earlier date → 5 reversals. We want ≥3 cap.
        log_text = "\n".join(
            f"## [{d}] update | p" for d in [
                "2026-07-01",  # baseline i=0
                "2026-07-02",  # upgrade i=1
                "2026-07-01",  # rev 1, i=2
                "2026-07-02",  # upgrade i=3
                "2026-07-01",  # rev 2, i=4
                "2026-07-02",  # upgrade i=5
                "2026-07-01",  # rev 3, i=6
                "2026-07-02",  # upgrade i=7
                "2026-07-01",  # rev 4, i=8
                "2026-07-02",  # upgrade i=9
                "2026-07-01",  # rev 5, i=10 — exceeds cap of 3
            ]
        ) + "\n"
        (vault_root / "log.md").write_text(log_text, encoding="utf-8")
        pages = [{"slug": "p", "path": "content/p.md"}]
        issues = _issues_for(pages, vault_root=vault_root)
        assert len(issues) == 1
        msg = issues[0].message
        assert "5 time-reversed" in msg
        assert "(+2 more)" in msg
        samples = re.findall(r"line \d+:", msg)
        assert len(samples) == 3  # cap


def test_rule18_under_cap_no_overflow_suffix() -> None:
    """When the reversal count is below the sample cap, no overflow hint."""
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        # 5 entries: 07-01 → 07-02 → 07-01 → 07-02 → 07-01
        # Adjacent comparisons:
        #   i=1 (07-02 vs 07-01): upgrade, no reversal
        #   i=2 (07-01 vs 07-02): reversal ❌
        #   i=3 (07-02 vs 07-01): upgrade, no reversal
        #   i=4 (07-01 vs 07-02): reversal ❌
        # → 2 reversals total, well under cap of 3.
        log_text = "\n".join(
            f"## [{d}] update | p" for d in [
                "2026-07-01", "2026-07-02", "2026-07-01",
                "2026-07-02", "2026-07-01",
            ]
        ) + "\n"
        (vault_root / "log.md").write_text(log_text, encoding="utf-8")
        pages = [{"slug": "p", "path": "content/p.md"}]
        issues = _issues_for(pages, vault_root=vault_root)
        assert len(issues) == 1
        msg = issues[0].message
        assert "2 time-reversed" in msg
        assert "(+" not in msg
        samples = re.findall(r"line \d+:", msg)
        assert len(samples) == 2


def test_rule18_corrupt_log_does_not_500() -> None:
    """Malformed log.md (no headers at all) — rule must not raise."""
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        (vault_root / "log.md").write_text("# just a comment, no entries\n", encoding="utf-8")
        pages = [{"slug": "p", "path": "content/p.md"}]
        issues = _issues_for(pages, vault_root=vault_root)
        assert issues == []  # no entries → no reversals to flag


def test_rule18_single_entry_log_no_issue() -> None:
    """A log with only one entry can't be reversed (no neighbor to compare)."""
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        (vault_root / "log.md").write_text(
            "## [2026-07-01] create | bootstrap\n", encoding="utf-8"
        )
        pages = [{"slug": "p", "path": "content/p.md"}]
        issues = _issues_for(pages, vault_root=vault_root)
        assert issues == []


def test_rule18_alternates_with_details_lines_ignored() -> None:
    """`{date} action | subject` header line is the only one parsed; the
    `- key: val` detail lines that follow each entry are ignored."""
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        log_text = (
            "## [2026-07-01] create | a\n"
            "- files: [a.md]\n"
            "## [2026-07-02] update | b\n"
            "- files: [b.md]\n"
            "## [2026-06-30] delete | c\n"  # reversed
            "- files: [c.md]\n"
        )
        (vault_root / "log.md").write_text(log_text, encoding="utf-8")
        pages = [{"slug": "x", "path": "content/x.md"}]
        issues = _issues_for(pages, vault_root=vault_root)
        assert len(issues) == 1
        assert issues[0].rule == "log-append-rollback"
        assert "[2026-06-30] after [2026-07-02]" in issues[0].message


# ────────────────────────── both rules together ──────────────────────────


def test_rules_17_and_18_coexist_independently() -> None:
    """A page can trigger Rule #17 (wikilinks) independently from
    Rule #18 (log). The two issues must not interfere with each other."""
    with tempfile.TemporaryDirectory() as tmp:
        vault_root = Path(tmp)
        # Reversed log AND page with short-form wikilinks.
        log_text = "\n".join(
            f"## [{d}] update | x" for d in ["2026-07-01", "2026-06-30"]
        ) + "\n"
        (vault_root / "log.md").write_text(log_text, encoding="utf-8")

        pages = [
            {
                "slug": "a",
                "path": "content/a.md",
                "content": "see [[b]]",
            }
        ]
        issues = _issues_for(pages, vault_root=vault_root)
        rules = {i.rule for i in issues}
        assert "wikilink-format-consistency" in rules
        assert "log-append-rollback" in rules
