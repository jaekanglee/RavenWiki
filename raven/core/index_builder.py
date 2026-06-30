"""raven.core.index_builder.py — Auto-compiles index.md catalog from SQLite.

Scans the compiled SQLite DB index to rebuild the markdown catalog index
inside <vault>/content/index.md, preserving custom welcome headers.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Optional

from .vault import Vault


def build_index(vault: Vault) -> bool:
    """Rebuild <vault>/content/index.md.
    Returns True on success, False otherwise.
    """
    index_path = vault.root / "content" / "index.md"
    
    # 1. Ensure DB is populated
    from .db import connect, build_db
    if not vault.db_path.exists():
        build_db(vault, run_lint=False)
        
    try:
        conn = connect(vault)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT slug, title, type, created, updated, content FROM pages"
        )
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"[index_builder] failed to query wiki.db: {e}")
        return False

    # 2. Filter & Group pages
    # Exclude index itself and WIP/scratch/system files
    pages = []
    for slug, title, ptype, created, updated, content in rows:
        slug_lower = slug.lower()
        if (
            slug_lower == "index" or
            slug_lower == "content/index" or
            slug_lower.startswith("wip/") or
            slug_lower.startswith("content/wip/") or
            slug_lower.startswith("scratch/") or
            slug_lower.startswith("content/scratch/") or
            slug_lower.startswith("_meta/")
        ):
            continue
        pages.append({
            "slug": slug,
            "title": title,
            "type": ptype,
            "created": created,
            "updated": updated,
            "summary": _extract_summary(content),
        })

    # Group by type
    groups: dict[str, list[dict]] = {}
    for p in pages:
        groups.setdefault(p["type"], []).append(p)

    # Sort groups and pages inside them
    sorted_types = sorted(groups.keys())
    for gtype in sorted_types:
        groups[gtype].sort(key=lambda x: x["title"].lower())

    # 3. Generate auto-index markdown block
    today = dt.date.today().isoformat()
    lines = [
        "## 📚 지식 카탈로그 (Auto-compiled)",
        f"마지막 자동 갱신: `{today}`",
        "",
    ]
    
    if not pages:
        lines.append("*아직 등록된 정제 페이지가 없습니다.*")
    else:
        for gtype in sorted_types:
            lines.append(f"### 📁 {gtype.capitalize()}s ({len(groups[gtype])})")
            for p in groups[gtype]:
                summary_suffix = f" — *{p['summary']}*" if p["summary"] else ""
                lines.append(f"- [[{p['slug']}]] — {p['title']}{summary_suffix}")
            lines.append("")

    auto_index_content = "\n".join(lines).strip()

    # 4. Load or initialize index.md with hybrid placeholders
    # If the directory doesn't exist, create it (e.g. fresh basic vault)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    
    if index_path.exists():
        try:
            raw_text = index_path.read_text(encoding="utf-8")
        except Exception:
            raw_text = ""
    else:
        raw_text = ""

    # Ensure placeholders exist
    start_marker = "<!-- AUTO_INDEX_START -->"
    end_marker = "<!-- AUTO_INDEX_END -->"

    if start_marker not in raw_text or end_marker not in raw_text:
        # Create default skeleton if missing
        if not raw_text:
            raw_text = f"""---
title: {vault.meta.name} 지식 홈
type: concept
tags: [index, home]
created: {today}
updated: {today}
---

# {vault.meta.name} 지식 보관소

{vault.meta.name} 보관소의 홈(Index) 페이지입니다.

{start_marker}
{end_marker}
"""
        else:
            # Append markers to the end of the existing content
            raw_text = raw_text.rstrip() + f"\n\n{start_marker}\n{end_marker}\n"

    # Replace content between placeholders
    pattern = re.compile(
        rf"({re.escape(start_marker)})(.*?)({re.escape(end_marker)})",
        re.DOTALL
    )
    
    replacement = f"\\1\n\n{auto_index_content}\n\n\\3"
    updated_text = pattern.sub(replacement, raw_text)

    # 5. Save updated file
    try:
        index_path.write_text(updated_text, encoding="utf-8")
        print(f"[index_builder] successfully updated {index_path}")
        return True
    except Exception as e:
        print(f"[index_builder] failed to write index.md: {e}")
        return False


def _extract_summary(content: str) -> str:
    """Extract a concise one-line summary from the page content (e.g. BLUF or first line)."""
    # 1. Search for BLUF section
    bluf_match = re.search(r"(?:##\s*BLUF|>)(.*?)(?:\n\n|\n#|$)", content, re.DOTALL | re.IGNORECASE)
    if bluf_match:
        text = bluf_match.group(1).strip().replace("\n", " ")
        text = re.sub(r"^>\s*", "", text).strip()
        if len(text) > 80:
            return text[:77] + "..."
        return text

    # 2. Fallback to the first non-empty non-header line
    lines = [
        line.strip() for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    for line in lines:
        if line.startswith(">"):
            line = line.lstrip(">").strip()
        if len(line) > 80:
            return line[:77] + "..."
        return line
    return ""
