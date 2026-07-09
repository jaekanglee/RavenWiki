"""build_db.py — scan a wiki vault, emit a SQLite v2.4 query index.

Markdown files are the Source of Truth (git-tracked). This script builds a
SQLite database at <vault>/wiki.db that the dashboard / MCP server / lint
tools query. The DB is gitignored — always regenerable from markdown.

Usage:
    python3 build_db.py                          # default vault = ~/wiki
    python3 build_db.py /path/to/vault           # explicit vault
    python3 build_db.py /path/to/vault --db /tmp/x.db
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sqlite3
import sys
from pathlib import Path
from typing import Iterable, Optional

import frontmatter

# ─────────────────────────── constants ──────────────────────────────

EXCLUDED_TOP_DIRS = {"raw", "_archive", "scripts", "node_modules", ".venv", ".git"}
TODAY = dt.date.today().isoformat()

# Wikilink regex: [[target]] or [[target]]! or [[target]]?
# Captures: (target, intent_suffix) where intent_suffix in {'', '!', '?'}
WIKILINK_RE = re.compile(r"\[\[([^\[\]\n]+?)\]\]([!?]?)")
CONTEXT_RADIUS = 50  # chars on each side of the wikilink in the body


# ─────────────────────────── schema (v2.4) ──────────────────────────

SCHEMA_SQL = """
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

CREATE TABLE tags (
  page_slug TEXT NOT NULL,
  tag TEXT NOT NULL,
  PRIMARY KEY (page_slug, tag),
  FOREIGN KEY (page_slug) REFERENCES pages(slug) ON DELETE CASCADE
);
CREATE INDEX idx_tags_tag ON tags(tag);

CREATE TABLE links (
  source_slug TEXT NOT NULL,
  target_slug TEXT NOT NULL,
  context TEXT,
  intent TEXT DEFAULT 'auto',
  PRIMARY KEY (source_slug, target_slug),
  FOREIGN KEY (source_slug) REFERENCES pages(slug) ON DELETE CASCADE
);
CREATE INDEX idx_links_target ON links(target_slug);

CREATE TABLE relations (
  source_slug TEXT NOT NULL,
  target_slug TEXT NOT NULL,
  relation_type TEXT NOT NULL,
  confidence_semantic REAL,
  confidence_structural REAL,
  confidence_provenance REAL,
  verified_by TEXT,
  evidence TEXT,
  reason TEXT,
  PRIMARY KEY (source_slug, target_slug, relation_type),
  FOREIGN KEY (source_slug) REFERENCES pages(slug) ON DELETE CASCADE
);
CREATE INDEX idx_relations_target ON relations(target_slug);

CREATE VIRTUAL TABLE pages_fts USING fts5(
  slug, title, tags_concat, content
);

CREATE TRIGGER pages_ai AFTER INSERT ON pages BEGIN
  INSERT INTO pages_fts(rowid, slug, title, tags_concat, content)
  VALUES (
    new.rowid, new.slug, new.title,
    COALESCE((SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE page_slug = new.slug), ''),
    new.content
  );
END;

CREATE TRIGGER pages_ad AFTER DELETE ON pages BEGIN
  DELETE FROM pages_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER pages_au AFTER UPDATE ON pages BEGIN
  DELETE FROM pages_fts WHERE rowid = old.rowid;
  INSERT INTO pages_fts(rowid, slug, title, tags_concat, content)
  VALUES (
    new.rowid, new.slug, new.title,
    COALESCE((SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE page_slug = new.slug), ''),
    new.content
  );
END;

CREATE TRIGGER tags_ai AFTER INSERT ON tags BEGIN
  -- refresh FTS row for this page so new tag joins the index
  DELETE FROM pages_fts WHERE rowid = (SELECT rowid FROM pages WHERE slug = new.page_slug);
  INSERT INTO pages_fts(rowid, slug, title, tags_concat, content)
  SELECT p.rowid, p.slug, p.title,
         COALESCE((SELECT GROUP_CONCAT(tag, ' ') FROM tags WHERE page_slug = p.slug), ''),
         p.content
  FROM pages p WHERE p.slug = new.page_slug;
END;

CREATE VIEW v_backlinks AS
  SELECT l.target_slug AS slug, l.source_slug, p.title AS source_title,
         p.path AS source_path, l.context
  FROM links l JOIN pages p ON p.slug = l.source_slug;

CREATE VIEW v_pages_with_tags AS
  SELECT p.*, GROUP_CONCAT(t.tag, ',') AS tags_list
  FROM pages p LEFT JOIN tags t ON t.page_slug = p.slug
  GROUP BY p.slug;
"""


# ─────────────────────────── slug strategy (v2.2) ───────────────────

def derive_slug(md_path: Path, vault: Path, fm_slug: Optional[str]) -> str:
    """1. frontmatter slug wins; 2. vault-relative path (.md stripped); 3. _meta/ kept."""
    if fm_slug:
        return fm_slug.strip()
    return md_path.relative_to(vault).with_suffix("").as_posix()


# ─────────────────────────── frontmatter defaults ──────────────────

DEFAULT_FM = {
    "title": "Untitled",
    "type": "rule",
    "tags": [],
    "sources": [],
    "created": TODAY,
    "updated": TODAY,
    "confidence": None,
    "contested": False,
    "slug": None,
}


def parse_page(md_path: Path, vault: Path) -> dict:
    """Read a markdown file, parse frontmatter, derive slug. Returns a dict ready for INSERT."""
    raw = md_path.read_text(encoding="utf-8")
    try:
        post = frontmatter.loads(raw)
        fm = dict(post.metadata)
    except Exception:
        # Malformed frontmatter → treat as empty
        fm = {}

    # Apply defaults for missing required fields
    title = str(fm.get("title") or md_path.stem)
    page_type = str(fm.get("type") or "rule")
    created = str(fm.get("created") or TODAY)
    updated = str(fm.get("updated") or TODAY)
    confidence = fm.get("confidence")
    contested = 1 if fm.get("contested") else 0
    fm_slug = fm.get("slug")

    slug = derive_slug(md_path, vault, fm_slug)
    body = post.content if "post" in locals() else raw
    # Strip leading frontmatter if python-frontmatter didn't (safety)
    if body.startswith("---\n"):
        body = re.sub(r"^---\n.*?\n---\n", "", raw, count=1, flags=re.DOTALL)

    return {
        "slug": slug,
        "title": title,
        "type": page_type,
        "created": created,
        "updated": updated,
        "path": str(md_path.relative_to(vault)),
        "confidence": confidence,
        "contested": contested,
        "content": body.strip(),
        "raw_content": raw,
        "tags": list(fm.get("tags") or []),
        "relations": list(fm.get("relations") or []),
    }


# ─────────────────────────── wikilink extraction ───────────────────

def extract_links(content: str) -> Iterable[tuple[str, str, Optional[str]]]:
    """Yield (target_slug, intent, context) tuples from a markdown body.

    intent is one of: 'auto', 'broken', 'missing'.
    context is up to 50 chars on each side of the wikilink.
    """
    for m in WIKILINK_RE.finditer(content):
        target = m.group(1).strip()
        suffix = m.group(2)
        intent = {"!": "broken", "?": "missing"}.get(suffix, "auto")
        start, end = m.span()
        ctx_start = max(0, start - CONTEXT_RADIUS)
        ctx_end = min(len(content), end + CONTEXT_RADIUS)
        context = content[ctx_start:ctx_end].replace("\n", " ").strip()
        yield target, intent, context


# v0.6.10: slug normalize helpers — 옛 빌드 wikilink 짧은 slug 호환
def _slug_exists(conn, slug: str) -> bool:
    row = conn.execute("SELECT 1 FROM pages WHERE slug = ? LIMIT 1", (slug,)).fetchone()
    return row is not None


def _resolve_short_slug(conn, short_slug: str) -> Optional[str]:
    """pages 중 마지막 segment 매치로 짧은 slug 보정. 예: 'vault-structure' → 'concept/vault-structure'."""
    base = short_slug.rsplit("/", 1)[-1]
    rows = conn.execute(
        "SELECT slug FROM pages WHERE slug = ? OR slug LIKE ?",
        (base, "%/" + base),
    ).fetchall()
    if len(rows) == 1:
        return rows[0][0]
    if len(rows) > 1:
        # ambiguous — 가장 짧은 path 우선 (root 가까울수록 canonical)
        return min(rows, key=lambda r: len(r[0]))[0]
    return None


# ─────────────────────────── vault walking ─────────────────────────

def iter_markdown(vault: Path):
    """Yield every .md file in vault, skipping EXCLUDED_TOP_DIRS."""
    for path in sorted(vault.rglob("*.md")):
        rel_parts = path.relative_to(vault).parts
        if rel_parts and rel_parts[0] in EXCLUDED_TOP_DIRS:
            continue
        yield path


# ─────────────────────────── DB build ──────────────────────────────

def build_db(vault: Path, db_path: Path) -> tuple[int, int, int]:
    """Build wiki.db from vault. Returns (n_pages, n_links, n_tags)."""
    vault = vault.resolve()
    db_path = db_path.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Regenerate: remove existing
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.execute("PRAGMA foreign_keys = ON")

        n_pages = n_links = n_tags = 0
        for md_path in iter_markdown(vault):
            page = parse_page(md_path, vault)
            conn.execute(
                """INSERT INTO pages (slug, title, type, created, updated, path,
                                      confidence, contested, content, raw_content)
                   VALUES (:slug, :title, :type, :created, :updated, :path,
                           :confidence, :contested, :content, :raw_content)""",
                {**page, "tags": None, "relations": None},  # tags & relations not columns
            )
            n_pages += 1

            for tag in page["tags"]:
                tag = str(tag).strip()
                if not tag:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO tags (page_slug, tag) VALUES (?, ?)",
                    (page["slug"], tag),
                )
                n_tags += 1

            import json
            for rel in page["relations"]:
                if not isinstance(rel, dict):
                    continue
                rel_type = rel.get("type")
                target = rel.get("target")
                if not rel_type or not target:
                    continue

                conf = rel.get("confidence")
                conf_sem = None
                conf_str = None
                conf_prov = None
                if isinstance(conf, dict):
                    conf_sem = conf.get("semantic")
                    conf_str = conf.get("structural")
                    conf_prov = conf.get("provenance")
                elif conf is not None:
                    conf_sem = conf

                verified = rel.get("verified_by")
                if isinstance(verified, list):
                    verified_by_str = ", ".join(str(v) for v in verified)
                else:
                    verified_by_str = str(verified) if verified is not None else None

                ev = rel.get("evidence")
                evidence_str = json.dumps(ev) if ev is not None else None
                reason = rel.get("reason")

                normalized = target
                if target and not _slug_exists(conn, target):
                    candidate = _resolve_short_slug(conn, target)
                    if candidate:
                        normalized = candidate

                conn.execute(
                    """INSERT OR REPLACE INTO relations (source_slug, target_slug, relation_type,
                                                          confidence_semantic, confidence_structural, confidence_provenance,
                                                          verified_by, evidence, reason)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (page["slug"], normalized, rel_type, conf_sem, conf_str, conf_prov, verified_by_str, evidence_str, reason),
                )

            for target, intent, context in extract_links(page["content"]):
                # v0.6.10: target slug normalize — 옛 wikilink `[[vault-structure]]` (짧은 형태)
                # 가 pages에 `concept/vault-structure` (긴 형태)로 존재할 때 자동 매칭.
                # 1) 정확 매치: 그대로
                # 2) 마지막 segment 매치 (prefix 보정)
                # 3) 매치 없으면 intent = 'broken' 유지
                normalized = target
                if target and not _slug_exists(conn, target):
                    candidate = _resolve_short_slug(conn, target)
                    if candidate:
                        normalized = candidate
                conn.execute(
                    """INSERT OR REPLACE INTO links (source_slug, target_slug, context, intent)
                       VALUES (?, ?, ?, ?)""",
                    (page["slug"], normalized, context, intent),
                )
                n_links += 1

        conn.commit()

        # v0.6.10 post-processing pass: 옛 빌드 wikilink 짧은 slug → pages에 매칭되는 긴 slug로 보정.
        # 첫 번째 pass에서 자기 자신의 wikilink가 아직 INSERT되지 않은 다른 페이지를 가리키면
        # _resolve_short_slug가 None 반환. build_db 전체 끝난 후 다시 시도.
        # v0.6.10 post-processing pass: 옛 빌드 wikilink 짧은 slug → pages에 매칭되는 긴 slug로 보정.
        # 첫 번째 pass에서 self-reference race 발생 시 _resolve_short_slug가 None 반환.
        # build_db 전체 끝난 후 모든 links 다시 시도.
        # SQLite에는 id 컬럼 없음 → PRIMARY KEY (source_slug, target_slug)로 UPDATE.
        try:
            rows = conn.execute(
                "SELECT source_slug, target_slug, context, intent FROM links"
            ).fetchall()
            n_fixed = 0
            for src, tgt, ctx, intent in rows:
                if _slug_exists(conn, tgt):
                    continue  # 이미 정확
                cand = _resolve_short_slug(conn, tgt)
                if cand:
                    conn.execute(
                        "UPDATE links SET target_slug = ? WHERE source_slug = ? AND target_slug = ?",
                        (cand, src, tgt),
                    )
                    n_fixed += 1
            conn.commit()
        except Exception:
            pass

        # relations post-processing pass
        try:
            rows = conn.execute(
                "SELECT source_slug, target_slug, relation_type FROM relations"
            ).fetchall()
            for src, tgt, rel_type in rows:
                if _slug_exists(conn, tgt):
                    continue
                cand = _resolve_short_slug(conn, tgt)
                if cand:
                    conn.execute(
                        "UPDATE relations SET target_slug = ? WHERE source_slug = ? AND target_slug = ? AND relation_type = ?",
                        (cand, src, tgt, rel_type),
                    )
            conn.commit()
        except Exception:
            pass

        return n_pages, n_links, n_tags
    finally:
        conn.close()


# ─────────────────────────── CLI ───────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    _default_vault = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description=f"Build {_default_vault} SQLite query index.")
    p.add_argument("vault", nargs="?", default=str(_default_vault),
                   help=f"vault root (default: {_default_vault})")
    p.add_argument("--db", default=None,
                   help="output DB path (default: <vault>/wiki.db)")
    args = p.parse_args(argv)

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"❌ vault not found: {vault}", file=sys.stderr)
        return 1

    db_path = Path(args.db).expanduser().resolve() if args.db else vault / "wiki.db"
    n_pages, n_links, n_tags = build_db(vault, db_path)
    size_kb = db_path.stat().st_size / 1024
    print(f"✅ wiki.db ({size_kb:.1f} KB): {n_pages} pages, {n_links} links, {n_tags} tags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
