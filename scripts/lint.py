"""lint.py — 9 lint rules operating on wiki.db (read-only).

Spec: SCHEMA.md §"Lint 자동 탐지" (L140-150)
       - 🔴 frontmatter missing/empty
       - 🔴 broken_link (links.intent == 'broken')
       - 🔵 missing_link (links.intent == 'missing')
       - 🟡 orphan (inbound_count == 0 AND age > 7d)
       - 🟡 oversized (raw_content lines > 200)
       - 🔵 weak_connection (type ∈ {concept, person, tool} AND outbound < 2)
       - 🔵 custom_tag (tag not in core taxonomy)
       - 🔵 contested (pages.contested == 1)
       - 🔵 stale (updated > 90d ago AND no recent raw source)

Usage:
    python3 lint.py --db ~/wiki/wiki.db --vault ~/wiki
    # exit 0 if no CRITICAL issues, 1 otherwise
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Sequence

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# SCHEMA.md L140-150 — fixed taxonomy for the lint pass.
CORE_TAGS: frozenset[str] = frozenset(
    {
        # 시스템
        "system", "tool", "ui", "search", "viewer",
        "schema", "mcp", "dashboard",
        # 컨텐츠
        "concept", "person", "comparison", "project",
        "rule", "query", "journal",
        # 도메인
        "ai", "wiki", "karpathy", "llm-wiki",
        "tailscale", "react", "python", "docker",
        # 상태
        "draft", "review", "final", "deprecated", "orphan",
    }
)

# Pages whose type is exempt from the weak_connection rule.
# (comparison pages can stand on their own with a single target.)
WEAK_CONN_EXEMPT_TYPES: frozenset[str] = frozenset({"comparison"})

# Thresholds
ORPHAN_GRACE_DAYS = 7
OVERSIZED_LINES = 200
STALE_DAYS = 90
WEAK_CONNECTION_MIN_OUTBOUND = 2

SEVERITY_EMOJI = {
    "critical": "🔴",
    "warning": "🟡",
    "info": "🔵",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Issue:
    rule: str
    severity: str   # "critical" | "warning" | "info"
    path: str       # vault-relative path
    message: str

    def format(self) -> str:
        emoji = SEVERITY_EMOJI.get(self.severity, "·")
        return f"{emoji} [{self.severity}] {self.path}: {self.message}"


# ---------------------------------------------------------------------------
# Lint engine
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> Optional[date]:
    """Parse ISO-8601 YYYY-MM-DD. Returns None for empty/garbage."""
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _raw_source_fresh(vault_root: Optional[Path], page_path: str) -> bool:
    """True if the page's underlying raw source was modified within STALE_DAYS.

    We check both the page itself (if a raw mirror exists) and the matching
    `raw/` file (heuristic: same stem under raw/). Used to suppress the
    "stale" rule when the *source* is current even if the wiki page hasn't
    been re-rendered.
    """
    if vault_root is None:
        return False
    vault = Path(vault_root)
    raw_dir = vault / "raw"
    if not raw_dir.is_dir():
        return False
    stem = Path(page_path).stem
    candidate = raw_dir / f"{stem}.md"
    if not candidate.is_file():
        candidate = raw_dir / stem
        if not candidate.is_file():
            return False
    mtime = datetime.fromtimestamp(candidate.stat().st_mtime).date()
    return (date.today() - mtime) <= timedelta(days=STALE_DAYS)


def lint_db(db_path: str, vault_root: Optional[Path] = None) -> List[Issue]:
    """Run all 9 rules against `db_path`. Returns a list of issues."""
    if not os.path.isfile(db_path):
        raise SystemExit(f"DB not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return _lint_all(conn, vault_root)
    finally:
        conn.close()


def _lint_all(conn: sqlite3.Connection, vault_root: Optional[Path]) -> List[Issue]:
    issues: List[Issue] = []
    today = date.today()

    pages = list(conn.execute("SELECT * FROM pages"))
    if not pages:
        return issues

    # Inbound + outbound counts per slug (one pass each)
    inbound_rows = conn.execute(
        "SELECT target_slug, COUNT(*) AS c FROM links GROUP BY target_slug"
    ).fetchall()
    inbound: dict[str, int] = {r["target_slug"]: r["c"] for r in inbound_rows}

    outbound_rows = conn.execute(
        "SELECT source_slug, COUNT(*) AS c FROM links GROUP BY source_slug"
    ).fetchall()
    outbound: dict[str, int] = {r["source_slug"]: r["c"] for r in outbound_rows}

    # Tags by slug
    tag_rows = conn.execute(
        "SELECT page_slug, tag FROM tags ORDER BY page_slug, tag"
    ).fetchall()
    tags_by_slug: dict[str, List[str]] = {}
    for r in tag_rows:
        tags_by_slug.setdefault(r["page_slug"], []).append(r["tag"])

    # --- Rule 1: broken_link (links.intent == 'broken')
    for r in conn.execute(
        "SELECT l.source_slug, l.target_slug, l.context, p.path AS source_path "
        "FROM links l JOIN pages p ON p.slug = l.source_slug "
        "WHERE l.intent = 'broken'"
    ):
        issues.append(Issue(
            rule="broken_link",
            severity="critical",
            path=r["source_path"],
            message=f"broken wikilink [[{r['target_slug']}]]! - target missing",
        ))

    # --- Rule 2: missing frontmatter (created NULL/empty)
    for p in pages:
        created = (p["created"] or "").strip()
        if not created:
            issues.append(Issue(
                rule="missing_frontmatter",
                severity="critical",
                path=p["path"],
                message="missing or empty `created:` in frontmatter",
            ))

    # --- Rule 3: missing_link (links.intent == 'missing') -> INFO
    for r in conn.execute(
        "SELECT l.source_slug, l.target_slug, l.context, p.path AS source_path "
        "FROM links l JOIN pages p ON p.slug = l.source_slug "
        "WHERE l.intent = 'missing'"
    ):
        issues.append(Issue(
            rule="missing_link",
            severity="info",
            path=r["source_path"],
            message=f"placeholder wikilink [[{r['target_slug']}]]? - intentional TODO",
        ))

    # --- Rule 4: orphan (inbound==0 AND age > 7d)
    for p in pages:
        if inbound.get(p["slug"], 0) > 0:
            continue
        created = _parse_date(p["created"])
        if created is None:
            continue
        age_days = (today - created).days
        if age_days <= ORPHAN_GRACE_DAYS:
            continue
        issues.append(Issue(
            rule="orphan",
            severity="warning",
            path=p["path"],
            message=f"orphan ({age_days}d, no inbound)",
        ))

    # --- Rule 5: oversized (>200 lines)
    for p in pages:
        raw = p["raw_content"] or ""
        line_count = len(raw.split("\n"))
        if line_count > OVERSIZED_LINES:
            issues.append(Issue(
                rule="oversized",
                severity="warning",
                path=p["path"],
                message=f"{line_count} lines (>{OVERSIZED_LINES})",
            ))

    # --- Rule 6: weak connection (concept/person/tool with outbound < 2)
    for p in pages:
        if p["type"] not in {"concept", "person", "tool"}:
            continue
        if p["type"] in WEAK_CONN_EXEMPT_TYPES:
            continue
        out_n = outbound.get(p["slug"], 0)
        if out_n < WEAK_CONNECTION_MIN_OUTBOUND:
            issues.append(Issue(
                rule="weak_connection",
                severity="info",
                path=p["path"],
                message=(
                    f"weak connection ({out_n} outbound, "
                    f"≥{WEAK_CONNECTION_MIN_OUTBOUND} 권장)"
                ),
            ))

    # --- Rule 7: custom_tag (not in core taxonomy)
    for p in pages:
        custom = [t for t in tags_by_slug.get(p["slug"], []) if t not in CORE_TAGS]
        if custom:
            issues.append(Issue(
                rule="custom_tag",
                severity="info",
                path=p["path"],
                message=f"tag not in core taxonomy: {', '.join(custom)}",
            ))

    # --- Rule 8: contested (pages.contested == 1)
    for p in pages:
        if p["contested"]:
            issues.append(Issue(
                rule="contested",
                severity="info",
                path=p["path"],
                message="contested: true — listed in 'contested' index",
            ))

    # --- Rule 9: stale (updated > 90d AND no recent raw source)
    for p in pages:
        updated = _parse_date(p["updated"])
        if updated is None:
            continue
        age_days = (today - updated).days
        if age_days <= STALE_DAYS:
            continue
        if _raw_source_fresh(vault_root, p["path"]):
            continue
        issues.append(Issue(
            rule="stale",
            severity="info",
            path=p["path"],
            message=f"stale ({age_days}d since updated, raw source not recent)",
        ))

    return issues


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def summarize(issues: Sequence[Issue]) -> str:
    """Headline metric: `N critical, M warning, K info, T total`."""
    n_crit = sum(1 for i in issues if i.severity == "critical")
    n_warn = sum(1 for i in issues if i.severity == "warning")
    n_info = sum(1 for i in issues if i.severity == "info")
    return f"📊 {n_crit} critical, {n_warn} warning, {n_info} info, {len(issues)} total"


def _print_report(issues: Sequence[Issue], stream=sys.stdout) -> None:
    # Sort: critical → warning → info, then by path
    sev_order = {"critical": 0, "warning": 1, "info": 2}
    for iss in sorted(issues, key=lambda i: (sev_order.get(i.severity, 9), i.path, i.rule)):
        print(iss.format(), file=stream)
    print(summarize(issues), file=stream)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint wiki.db against 9 SCHEMA-defined rules.",
    )
    parser.add_argument(
        "--db",
        default=str(Path.home() / "wiki" / "wiki.db"),
        help="Path to wiki.db (default: ~/wiki/wiki.db)",
    )
    parser.add_argument(
        "--vault",
        default=str(Path.home() / "wiki"),
        help="Vault root for raw/ freshness heuristic (default: ~/wiki)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-issue output; print summary only.",
    )
    args = parser.parse_args(argv)

    try:
        issues = lint_db(args.db, Path(args.vault) if args.vault else None)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2

    if not args.quiet:
        _print_report(issues)
    else:
        print(summarize(issues))

    return 1 if any(i.severity == "critical" for i in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
