"""Tests for lint.py — 9 rules operating on wiki.db.

TDD: tests written first; rules implemented until they pass.

Each test seeds a tiny in-memory or temp-file wiki.db (matching the v2.4
schema that build_db.py produces) and asserts on the issues lint() returns.
The fixture build_db tests in test_build_db.py use the same schema; we
build it ourselves here to keep lint self-contained.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, List, Optional

import pytest

import lint  # the module under test


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

PAGES_DDL = """
CREATE TABLE pages (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT NOT NULL,
    created TEXT NOT NULL,
    updated TEXT NOT NULL,
    path TEXT NOT NULL,
    confidence TEXT,
    contested INTEGER DEFAULT 0,
    content TEXT NOT NULL,
    raw_content TEXT NOT NULL
);
"""

TAGS_DDL = """
CREATE TABLE tags (
    page_slug TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (page_slug, tag),
    FOREIGN KEY (page_slug) REFERENCES pages(slug) ON DELETE CASCADE
);
"""

LINKS_DDL = """
CREATE TABLE links (
    source_slug TEXT NOT NULL,
    target_slug TEXT NOT NULL,
    context TEXT,
    intent TEXT DEFAULT 'auto',
    PRIMARY KEY (source_slug, target_slug),
    FOREIGN KEY (source_slug) REFERENCES pages(slug) ON DELETE CASCADE
);
"""

BACKLINKS_VIEW = """
CREATE VIEW v_backlinks AS
SELECT l.target_slug AS slug, l.source_slug, p.title AS source_title,
       p.path AS source_path, l.context
FROM links l JOIN pages p ON p.slug = l.source_slug;
"""


class FakePage:
    """Lightweight page record for the in-memory DB seed helpers."""

    def __init__(
        self,
        slug: str,
        title: str,
        type_: str = "concept",
        created: Optional[str] = None,
        updated: Optional[str] = None,
        path: Optional[str] = None,
        contested: int = 0,
        content: str = "",
        raw_content: str = "",
    ):
        self.slug = slug
        self.title = title
        self.type = type_
        # NB: created/updated accept None or "" — only None gets the default.
        # This lets tests seed pages with explicitly empty `created` to
        # exercise the missing-frontmatter lint rule.
        self.created = "2026-06-24" if created is None else created
        self.updated = "2026-06-24" if updated is None else updated
        self.path = path or f"content/{slug}.md"
        self.contested = contested
        self.content = content
        self.raw_content = raw_content or f"---\ntitle: {title}\n---\n\n# {title}\n\n{content}"


def build_test_db(
    tmp_path: Path,
    pages: Iterable[FakePage],
    tags: Optional[List[tuple]] = None,
    links: Optional[List[tuple]] = None,
) -> Path:
    """Build a wiki.db at tmp_path/db.sqlite3 with the given seed data."""
    tags = tags or []
    links = links or []
    db_path = tmp_path / "db.sqlite3"
    conn = sqlite3.connect(db_path)
    conn.executescript(PAGES_DDL + TAGS_DDL + LINKS_DDL + BACKLINKS_VIEW)
    for p in pages:
        conn.execute(
            "INSERT INTO pages (slug, title, type, created, updated, path, contested, content, raw_content) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                p.slug,
                p.title,
                p.type,
                p.created,
                p.updated,
                p.path,
                p.contested,
                p.content,
                p.raw_content,
            ),
        )
    for page_slug, tag in tags:
        conn.execute("INSERT INTO tags (page_slug, tag) VALUES (?, ?)", (page_slug, tag))
    for source, target, intent, ctx in links:
        conn.execute(
            "INSERT INTO links (source_slug, target_slug, intent, context) VALUES (?, ?, ?, ?)",
            (source, target, intent, ctx),
        )
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# 1. DB not found
# ---------------------------------------------------------------------------

def test_lint_db_not_found(tmp_path):
    missing = tmp_path / "nope.sqlite3"
    with pytest.raises(SystemExit) as excinfo:
        lint.lint_db(str(missing))
    assert "not found" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# 2. Clean DB → 0 issues
# ---------------------------------------------------------------------------

def test_lint_clean_db(tmp_path):
    today = date.today().isoformat()
    pages = [
        FakePage("a", "Alpha", type_="concept", created=today, updated=today),
        FakePage("b", "Beta", type_="concept", created=today, updated=today),
    ]
    tags = [("a", "concept"), ("b", "concept")]
    links = [
        ("a", "b", "auto", "see b"),
        ("b", "a", "auto", "see a"),
    ]
    db = build_test_db(tmp_path, pages, tags, links)
    issues = lint.lint_db(str(db))
    # No critical/warning issues on a clean, well-connected fresh DB.
    criticals = [i for i in issues if i.severity == "critical"]
    warnings = [i for i in issues if i.severity == "warning"]
    assert criticals == []
    assert warnings == []


# ---------------------------------------------------------------------------
# 3. broken_link (CRITICAL)
# ---------------------------------------------------------------------------

def test_lint_broken_link(tmp_path):
    today = date.today().isoformat()
    pages = [
        FakePage("src", "Source", type_="concept", created=today, updated=today),
    ]
    links = [("src", "ghost", "broken", "see [[ghost]]!")]
    db = build_test_db(tmp_path, pages, links=links)
    issues = lint.lint_db(str(db))
    broken = [i for i in issues if i.rule == "broken_link"]
    assert len(broken) == 1
    assert broken[0].severity == "critical"
    assert broken[0].path == "content/src.md"
    assert "ghost" in broken[0].message


# ---------------------------------------------------------------------------
# 4. missing_link (INFO)
# ---------------------------------------------------------------------------

def test_lint_missing_link(tmp_path):
    today = date.today().isoformat()
    pages = [
        FakePage("src", "Source", type_="concept", created=today, updated=today),
    ]
    links = [("src", "future", "missing", "see [[future]]?")]
    db = build_test_db(tmp_path, pages, links=links)
    issues = lint.lint_db(str(db))
    missing = [i for i in issues if i.rule == "missing_link"]
    assert len(missing) == 1
    assert missing[0].severity == "info"
    assert "future" in missing[0].message


# ---------------------------------------------------------------------------
# 5. Missing frontmatter (CRITICAL)
# ---------------------------------------------------------------------------

def test_lint_missing_frontmatter(tmp_path):
    today = date.today().isoformat()
    # `created` empty string signals frontmatter missing
    pages = [
        FakePage("naked", "Naked", type_="rule", created="", updated=today),
        FakePage("good", "Good", type_="rule", created=today, updated=today),
    ]
    db = build_test_db(tmp_path, pages)
    issues = lint.lint_db(str(db))
    crits = [i for i in issues if i.rule == "missing_frontmatter"]
    assert len(crits) == 1
    assert crits[0].path == "content/naked.md"
    assert crits[0].severity == "critical"


# ---------------------------------------------------------------------------
# 6. Orphan 7-day grace (younger than 7d → no warning)
# ---------------------------------------------------------------------------

def test_lint_orphan_7d_grace(tmp_path):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    pages = [
        FakePage("hub", "Hub", type_="concept", created=yesterday, updated=yesterday),
        FakePage("young", "Young", type_="concept", created=today, updated=today),
    ]
    # Young has no inbound, but it's < 7d old → no warning
    links = [("hub", "hub", "auto", "self")]  # ensure hub exists in links
    db = build_test_db(tmp_path, pages, links=links)
    issues = lint.lint_db(str(db))
    orph_warnings = [
        i for i in issues
        if i.rule == "orphan" and i.severity == "warning"
    ]
    assert orph_warnings == []


# ---------------------------------------------------------------------------
# 7. Orphan after 7d (WARNING)
# ---------------------------------------------------------------------------

def test_lint_orphan_after_7d(tmp_path):
    old = (date.today() - timedelta(days=30)).isoformat()
    pages = [
        FakePage("hub", "Hub", type_="concept", created=old, updated=old),
        FakePage("orphan", "Orphan", type_="concept", created=old, updated=old),
    ]
    db = build_test_db(tmp_path, pages)
    issues = lint.lint_db(str(db))
    orph = [i for i in issues if i.rule == "orphan" and i.severity == "warning"]
    slugs = [i.path for i in orph]
    assert any("orphan.md" in s for s in slugs)
    assert any("hub.md" in s for s in slugs)  # hub also has no inbound


# ---------------------------------------------------------------------------
# 8. Oversized (200+ lines, WARNING)
# ---------------------------------------------------------------------------

def test_lint_oversized(tmp_path):
    today = date.today().isoformat()
    # 201 lines of content
    big = "\n".join(f"line {i}" for i in range(201))
    pages = [
        FakePage("big", "Big", type_="concept", created=today, updated=today, raw_content=big),
        FakePage("normal", "Normal", type_="concept", created=today, updated=today),
    ]
    db = build_test_db(tmp_path, pages)
    issues = lint.lint_db(str(db))
    big_issues = [i for i in issues if i.rule == "oversized" and "big.md" in i.path]
    assert len(big_issues) == 1
    assert big_issues[0].severity == "warning"


# ---------------------------------------------------------------------------
# 9. Weak connection: concept + outbound < 2 → INFO
# ---------------------------------------------------------------------------

def test_lint_weak_connection_concept(tmp_path):
    today = date.today().isoformat()
    pages = [
        FakePage("c", "ConceptC", type_="concept", created=today, updated=today),
        FakePage("other", "Other", type_="concept", created=today, updated=today),
    ]
    # c has only 1 outbound; should be flagged
    links = [
        ("c", "other", "auto", "see other"),
        ("other", "c", "auto", "see c"),
    ]
    db = build_test_db(tmp_path, pages, links=links)
    issues = lint.lint_db(str(db))
    weak = [i for i in issues if i.rule == "weak_connection" and "c.md" in i.path]
    assert len(weak) == 1
    assert weak[0].severity == "info"
    assert "1 outbound" in weak[0].message


# ---------------------------------------------------------------------------
# 10. Weak connection: comparison + outbound < 2 → exempt (NO issue)
# ---------------------------------------------------------------------------

def test_lint_weak_connection_comparison_exempt(tmp_path):
    today = date.today().isoformat()
    pages = [
        FakePage("cmp", "Compare", type_="comparison", created=today, updated=today),
        FakePage("other", "Other", type_="comparison", created=today, updated=today),
    ]
    links = [
        ("cmp", "other", "auto", "see other"),
        ("other", "cmp", "auto", "see cmp"),
    ]
    db = build_test_db(tmp_path, pages, links=links)
    issues = lint.lint_db(str(db))
    weak = [i for i in issues if i.rule == "weak_connection"]
    assert weak == []


# ---------------------------------------------------------------------------
# 11. Custom tag (not in core taxonomy) → INFO
# ---------------------------------------------------------------------------

def test_lint_custom_tag(tmp_path):
    today = date.today().isoformat()
    pages = [FakePage("p", "P", type_="concept", created=today, updated=today)]
    tags = [("p", "kotlin"), ("p", "jetpack-compose")]
    db = build_test_db(tmp_path, pages, tags=tags)
    issues = lint.lint_db(str(db))
    custom = [i for i in issues if i.rule == "custom_tag" and "p.md" in i.path]
    assert len(custom) >= 1
    assert custom[0].severity == "info"
    msg = custom[0].message
    assert "kotlin" in msg or "jetpack" in msg


# ---------------------------------------------------------------------------
# 12. Core tag (in taxonomy) → NO custom_tag issue
# ---------------------------------------------------------------------------

def test_lint_core_tag(tmp_path):
    today = date.today().isoformat()
    pages = [FakePage("p", "P", type_="concept", created=today, updated=today)]
    tags = [("p", "system"), ("p", "tool"), ("p", "concept")]
    db = build_test_db(tmp_path, pages, tags=tags)
    issues = lint.lint_db(str(db))
    custom = [i for i in issues if i.rule == "custom_tag" and "p.md" in i.path]
    assert custom == []


# ---------------------------------------------------------------------------
# 13. Contested listed (contested=1 → INFO)
# ---------------------------------------------------------------------------

def test_lint_contested_listed(tmp_path):
    today = date.today().isoformat()
    pages = [
        FakePage("hot", "Hot", type_="concept", created=today, updated=today, contested=1),
        FakePage("calm", "Calm", type_="concept", created=today, updated=today, contested=0),
    ]
    db = build_test_db(tmp_path, pages)
    issues = lint.lint_db(str(db))
    contested = [i for i in issues if i.rule == "contested" and "hot.md" in i.path]
    assert len(contested) == 1
    assert contested[0].severity == "info"


# ---------------------------------------------------------------------------
# 14. Stale: 90+ days without new raw source (INFO)
# ---------------------------------------------------------------------------

def test_lint_stale(tmp_path):
    old = (date.today() - timedelta(days=120)).isoformat()
    pages = [
        FakePage("stale", "Stale", type_="concept", created=old, updated=old),
        FakePage("fresh", "Fresh", type_="concept", created=old, updated=old),
    ]
    # stale has no raw source recently, fresh was just edited
    links = [("stale", "fresh", "auto", "see fresh")]
    db = build_test_db(tmp_path, pages, links=links)
    issues = lint.lint_db(str(db), vault_root=None)  # vault_root=None → nothing is "fresh raw"
    stale = [i for i in issues if i.rule == "stale" and "stale.md" in i.path]
    assert len(stale) == 1
    assert stale[0].severity == "info"


# ---------------------------------------------------------------------------
# Additional: format/CLI smoke test
# ---------------------------------------------------------------------------

def test_lint_format_lines():
    """Issue formatting is the human-facing contract; pin it down."""
    from lint import Issue
    iss = Issue(
        rule="broken_link",
        severity="critical",
        path="content/bad.md",
        message="broken wikilink [[foo]]!",
    )
    line = iss.format()
    assert "🔴" in line
    assert "critical" in line
    assert "content/bad.md" in line
    assert "[[foo]]!" in line


def test_lint_summary(capsys):
    """CLI summary line is the headline metric for the orchestrator."""
    from lint import Issue, summarize
    issues = [
        Issue("broken_link", "critical", "a.md", "x"),
        Issue("broken_link", "critical", "b.md", "x"),
        Issue("orphan", "warning", "c.md", "x"),
        Issue("weak", "info", "d.md", "x"),
        Issue("weak", "info", "e.md", "x"),
    ]
    line = summarize(issues)
    assert "2 critical" in line
    assert "1 warning" in line
    assert "2 info" in line
    assert "5 total" in line


def test_lint_cli_exit_code_clean(tmp_path, capsys):
    today = date.today().isoformat()
    pages = [FakePage("a", "A", type_="concept", created=today, updated=today)]
    db = build_test_db(tmp_path, pages)
    rc = lint.main(["--db", str(db), "--vault", str(tmp_path)])
    assert rc == 0


def test_lint_cli_exit_code_critical(tmp_path):
    today = date.today().isoformat()
    pages = [FakePage("src", "Src", type_="concept", created=today, updated=today)]
    links = [("src", "ghost", "broken", "see [[ghost]]!")]
    db = build_test_db(tmp_path, pages, links=links)
    rc = lint.main(["--db", str(db), "--vault", str(tmp_path)])
    assert rc == 1
