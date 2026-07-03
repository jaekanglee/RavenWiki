#!/usr/bin/env python3
"""export_static.py — vault → dashboard/public/api/*.json 빌드 시 export.

Reads `wiki.db` (SQLite, built by scripts/build_db.py) and emits:

    dashboard/public/api/
        index.json            # every page with tags (sidebar + Home source)
        graph.json            # { nodes, edges } for the graph view
        page-<slug>.json      # individual page payloads (PageView)
        tree.json             # nested tree for the Sidebar
        search.idx.json       # pre-built MiniSearch index

Run from the project root:

    cd scripts && ./.venv/bin/python export_static.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------- helpers ----------


def _slug_to_json_name(slug: str) -> str:
    """Convert a vault slug to a JSON filename safe across the wire.

    Slug like ``"concepts/wiki"`` → ``"page-concepts_wiki.json"``.
    Only forward slashes are rewritten (everything else is filesystem-safe).
    """
    return f"page-{slug.replace('/', '_')}.json"


def _fetch_all(conn: sqlite3.Connection, sql: str, params=()) -> List[Dict[str, Any]]:
    cur = conn.execute(sql, params)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _build_tree(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Group flat pages into a nested tree by path prefix."""
    root: Dict[str, Any] = {"slug": "", "title": "root", "type": "root", "children": {}}
    for p in pages:
        path = p["path"] or p["slug"]
        parts = path.split("/")
        node = root
        for i, part in enumerate(parts):
            is_leaf = i == len(parts) - 1
            if is_leaf:
                # Insert/overwrite the leaf.
                slug = p["slug"]
                node["children"][part] = {
                    "slug": slug,
                    "title": p.get("title") or part,
                    "type": p.get("type", "page"),
                }
            else:
                # Intermediate directory node.
                child = node["children"].get(part)
                if child is None or "children" not in child:
                    child = {
                        "slug": "/".join(parts[: i + 1]),
                        "title": part,
                        "type": "folder",
                        "children": {},
                    }
                    node["children"][part] = child
                node = child
    return _tree_to_list(root)


def _tree_to_list(node: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively turn the dict-based tree into a list-based one.

    The dashboard Sidebar expects ``children: [...]``.
    """
    children_dict = node.get("children") or {}
    children: List[Dict[str, Any]] = []
    for key in sorted(children_dict.keys()):
        child = children_dict[key]
        if "children" in child:
            children.append(_tree_to_list(child))
        else:
            children.append(child)
    out = {k: v for k, v in node.items() if k != "children"}
    out["children"] = children
    return out


def _serialize(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


# ---------- main export ----------


def export(vault: Path, out_dir: Optional[Path] = None) -> Optional[int]:
    """Vault 데이터를 out_dir/*.json으로 export.

    반환: 페이지 수. wiki.db가 없으면 None (실패 — 성공 위장 금지).
    """
    db_path = vault / "wiki.db"
    if not db_path.exists():
        print(f"❌ {db_path} 없음. `raven build` 먼저 실행하세요.")
        return None

    if out_dir is None:
        out_dir = vault / "dashboard" / "public" / "api"
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 1) index.json (page list with aggregated tags).
    rows = conn.execute(
        """
        SELECT p.slug, p.title, p.type, p.path, p.created, p.updated,
               GROUP_CONCAT(t.tag, ',') AS tags
        FROM pages p
        LEFT JOIN tags t ON t.page_slug = p.slug
        WHERE p.slug NOT LIKE '.%'
          AND p.slug NOT LIKE 'node_modules/%'
          AND p.slug NOT LIKE 'dashboard/%'
        GROUP BY p.slug
        ORDER BY p.type, p.slug
        """
    ).fetchall()
    pages = [dict(r) for r in rows]
    pages_out = []
    for p in pages:
        # Drop heavy fields from the index payload; per-page JSON has the body.
        pages_out.append(
            {
                "slug": p["slug"],
                "title": p["title"],
                "type": p["type"],
                "path": p["path"],
                "created": p["created"],
                "updated": p["updated"],
                "tags": p["tags"] or "",
            }
        )

    (out_dir / "index.json").write_text(
        _serialize(pages_out), encoding="utf-8"
    )

    # 2) tree.json (nested tree for the Sidebar).
    tree = _build_tree(pages)
    (out_dir / "tree.json").write_text(_serialize(tree), encoding="utf-8")

    # 3) graph.json
    nodes = [
        dict(r) for r in conn.execute(
            """
            SELECT slug, title, type FROM pages
            WHERE slug NOT LIKE '.%'
              AND slug NOT LIKE 'node_modules/%'
              AND slug NOT LIKE 'dashboard/%'
            ORDER BY slug
            """
        ).fetchall()
    ]
    edges = [
        dict(r) for r in conn.execute(
            "SELECT source_slug, target_slug, intent FROM links"
        ).fetchall()
    ]
    (out_dir / "graph.json").write_text(
        _serialize({"nodes": nodes, "edges": edges}), encoding="utf-8"
    )

    # 4) Per-page JSON with content + backlinks.
    n_pages = 0
    for p in pages:
        slug = p["slug"]
        # page row + content
        page_row = conn.execute(
            "SELECT slug, title, type, path, created, updated, content FROM pages WHERE slug = ?",
            (slug,),
        ).fetchone()
        if page_row is None:
            continue
        page = dict(page_row)
        page["tags"] = p.get("tags") or ""

        # Backlinks from v_backlinks (DB view built by build_db.py).
        try:
            backlinks = [
                dict(r) for r in conn.execute(
                    "SELECT source_slug, source_title FROM v_backlinks WHERE slug = ?",
                    (slug,),
                ).fetchall()
            ]
        except sqlite3.OperationalError:
            # View not present in this vault — degrade gracefully.
            backlinks = []
        page["backlinks"] = backlinks

        (out_dir / _slug_to_json_name(slug)).write_text(
            _serialize(page), encoding="utf-8"
        )
        n_pages += 1

    # 5) search.idx.json — minimal stub with title+slug so MiniSearch can boot.
    # A full BM25 index can be built in JS at dev time; for now the static
    # payload lets the SearchBar degrade to a plain in-memory title scan.
    (out_dir / "search.idx.json").write_text(
        _serialize(
            {
                "_comment": "client-side build path; static stub keeps MiniSearch happy",
                "documents": pages_out,
            }
        ),
        encoding="utf-8"
    )

    conn.close()

    print(
        f"✅ Exported {n_pages} pages + graph + tree + index → {out_dir}/"
    )
    return n_pages


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="vault → 정적 JSON export")
    parser.add_argument(
        "vault", nargs="?", default=str(Path(__file__).resolve().parent.parent),
        help="vault 루트 경로 (기본: 저장소 루트 — legacy 호환)",
    )
    parser.add_argument("--out", default=None, help="출력 디렉토리")
    args = parser.parse_args()

    n = export(Path(args.vault), Path(args.out) if args.out else None)
    if n is None:
        sys.exit(1)
