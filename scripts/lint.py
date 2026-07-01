"""lint.py — 11 lint rules operating on wiki.db (read-only).

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
       - 🔵 pkm_trace (v0.3.0: no page tagged pkm/note/agent — PKM 노트 정정)
       - 🔵 agent_relevance (v0.3.0: vault missing 사람/단일/멀티 중 1+ 카테고리)

Usage:
    python3 lint.py --db ~/wiki/wiki.db --vault ~/wiki
    # exit 0 if no CRITICAL issues, 1 otherwise
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

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
    """Run all 11 rules against `db_path`. Returns a list of issues."""
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

    # --- Rule 10: pkm_trace (v0.3.0 PKM 노트 프로덕트 정정) ---
    PKM_RELATED_TAGS = frozenset({"pkm", "note", "notes", "agent"})
    pkm_seen = 0
    for slug, tags in tags_by_slug.items():
        if any(t.lower() in PKM_RELATED_TAGS for t in tags):
            pkm_seen += 1
    if pkm_seen == 0:
        # No page tagged as PKM — this is OK for pure operational vaults but flag for awareness
        issues.append(Issue(
            rule="pkm_trace",
            severity="info",
            path="(vault)",
            message="No page tagged as pkm/note/agent. If this vault is intended as PKM, consider tagging at least the index page.",
        ))

    # --- Rule 11: agent_relevance (v0.3.0 사용자 3종 — 사람/단일/멀티 에이전트) ---
    pages_rows = list(conn.execute("SELECT slug, type FROM pages"))
    person_count = sum(1 for p in pages_rows if p["type"] == "person")
    agent_single_count = sum(
        1 for slug, tags in tags_by_slug.items()
        if any(t.lower() in {"agent", "agent-single"} for t in tags)
    )
    agent_multi_count = sum(
        1 for slug, tags in tags_by_slug.items()
        if any(t.lower() in {"multi-agent", "agents"} for t in tags)
    )
    missing: List[str] = []
    if person_count == 0:
        missing.append("person type")
    if agent_single_count == 0:
        missing.append("agent/agent-single tag")
    if agent_multi_count == 0:
        missing.append("multi-agent/agents tag")
    if missing:
        issues.append(Issue(
            rule="agent_relevance",
            severity="info",
            path="(vault)",
            message=(
                f"Vault doesn't cover all 3 user types (사람/단일/멀티 에이전트). "
                f"Missing: {', '.join(missing)}. (v0.3.0 PKM 노트 프로덕트 정정)"
            ),
        ))

    # --- Rule 17: wikilink-format-consistency (v0.7.38+) -- Detect use of
    # **short-form wikilinks** (`[[foo]]`) that DON'T include a vault-relative
    # prefix (`content/`, `_meta/`, `_archive/`, `_deprecated/`, `raw/`).
    # Multi-author vaults (one vault, multiple agents writing) repeatedly
    # mix `[[foo]]` and `[[content/foo]]` in adjacent pages, breaking
    # readability without breaking the build (the build resolves either).
    # This rule is **detect-only** — no auto-rewrite — because (a) silent
    # rewrite would violate user's intent and (b) the standardization
    # surface itself is judged too domain-specific to bake into raven
    # core. Vaults can configure their own normalize_format via future
    # v0.7.39+ extensions; for now, this just informs the author.
    if pages:
        short_form: List[Tuple[str, str]] = []  # (slug, sample_wikilink)
        total_short = 0
        for p in pages:
            content = p["content"] or ""
            for m in re.finditer(r"\[\[([^\]!|?]+)(?:[!?]?)(?:\|[^\]]+)?\]\]", content):
                target = m.group(1).strip()
                if not target:
                    continue
                # Skip if it already has a recognized system prefix or is a
                # bare anchor / URL-like. Anything with '/' or starting with
                # a system prefix is "long form".
                if "/" in target:
                    continue
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                total_short += 1
                if len(short_form) < 5:  # sample cap to keep message readable
                    short_form.append((p["slug"], target))

        if total_short:
            samples = ", ".join(f"[[{t}]]" for _, t in short_form[:5])
            extra = f" (+{total_short - 5} more)" if total_short > 5 else ""
            issues.append(Issue(
                rule="wikilink-format-consistency",
                severity="info",
                path="(vault)",
                message=(
                    f"{total_short} short-form wikilink(s) found without a "
                    f"vault-relative prefix (e.g. {samples}{extra}). "
                    f"Consider `content/<slug>` form for cross-author readability."
                ),
            ))

    # --- Rule 18: log-append-rollback (v0.7.38+) -- Detect time-reversed
    # entries in `<vault>/log.md`. The append-only log policy (R9.x / v0.7.20+
    # FileLock-protected writes) is broken if entries appear with a date
    # earlier than the immediately previous one — that pattern only arises
    # when someone has rewritten a portion of the file (rollback / edit).
    # This rule is **detect-only** — silent auto-repair of log.md would
    # hide the very signal it's meant to surface, so we just flag.
    # Vault-rooted scan: we read the log.md at `vault_root / log.md`. The
    # connection's vault_root is a `Path` or None; both shapes handled.
    log_path = None
    if vault_root is not None:
        log_path = Path(vault_root) / "log.md"
    if log_path is not None and log_path.exists():
        try:
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            log_dates = re.findall(
                r"^##\s+\[(\d{4}-\d{2}-\d{2})\]\s+\S+\s*\|", log_text, re.MULTILINE
            )
            rollback_pairs: List[Tuple[str, str, int]] = []
            for i in range(1, len(log_dates)):
                prev_d = log_dates[i - 1]
                cur_d = log_dates[i]
                if cur_d < prev_d:
                    rollback_pairs.append((prev_d, cur_d, i + 1))
            if rollback_pairs:
                samples = ", ".join(
                    f"line {ln}: [{cur}] after [{prev}]"
                    for prev, cur, ln in rollback_pairs[:3]
                )
                extra = (
                    f" (+{len(rollback_pairs) - 3} more)"
                    if len(rollback_pairs) > 3 else ""
                )
                issues.append(Issue(
                    rule="log-append-rollback",
                    severity="warning",
                    path="log.md",
                    message=(
                        f"{len(rollback_pairs)} time-reversed entry(s) in "
                        f"log.md (later entry has earlier date than previous). "
                        f"log.md is supposed to be append-only. "
                        f"Sample: {samples}{extra}"
                    ),
                ))
        except Exception:
            # log.md unreadable or malformed — don't 500 the lint. Other
            # rules already cover path/IO issues.
            pass

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
    _default_vault = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Lint wiki.db against 11 SCHEMA-defined rules.",
    )
    parser.add_argument(
        "--db",
        default=str(_default_vault / "wiki.db"),
        help=f"Path to wiki.db (default: {_default_vault}/wiki.db)",
    )
    parser.add_argument(
        "--vault",
        default=str(_default_vault),
        help=f"Vault root for raw/ freshness heuristic (default: {_default_vault})",
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
