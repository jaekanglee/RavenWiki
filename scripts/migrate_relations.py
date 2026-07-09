#!/usr/bin/env python3
"""scripts/migrate_relations.py — 기존 wikilink들을 relations frontmatter로 일괄 마이그레이션.

동작 원리:
1. content/ 하위 모든 마크다운 파일들의 wikilink([[target]])를 추출합니다.
2. 각 wikilink의 앞뒤 문맥(context, radius 60자)을 파싱하여, 다음과 같이 관계의 type을 추론합니다:
   - "uses", "사용", "이용" -> uses
   - "depends on", "의존", "필요" -> depends_on
   - "implements", "구현" -> implements
   - "implemented by", "구현체" -> implemented_by
   - 그 외 -> related
3. 만약 target이 단축 slug 형태이면, vault 내에 실존하는 canonical slug로 해소합니다.
4. 해소된 target과 추론된 type을 가지고 frontmatter relations 필드를 채웁니다.
5. evidence 에는 파일 경로를, reason 에는 "Auto-extracted from context: '{context}'"를 넣어 규약을 준수합니다.
6. --dry-run (기본값) 모드와 --apply 모드를 제공합니다.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Add project root to sys.path to allow importing raven packages
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from raven.core import frontmatter as fm_mod
from raven.core.vault import Vault


def build_slug_map(vault: Vault) -> dict[str, str]:
    """Build a mapping from page base name (slug segment or filename stem) to full canonical slug.

    Supports short-slug resolution.
    """
    slug_map = {}
    duplicate_basenames = set()
    
    # scan content/
    for p in vault.content_root.rglob("*.md"):
        if any(part in {"raw", "_archive", "_meta", "scripts"} for part in p.relative_to(vault.root).parts):
            continue
        rel_path = p.relative_to(vault.root)
        slug = str(rel_path.with_suffix("")).replace("\\", "/")
        basename = p.stem
        
        # also handle fm_slug if defined
        try:
            text = p.read_text(encoding="utf-8")
            meta, _ = fm_mod.parse(text)
            if meta and "slug" in meta:
                slug = meta["slug"].strip()
        except Exception:
            pass

        if basename in slug_map:
            duplicate_basenames.add(basename)
        else:
            slug_map[basename] = slug

    # Remove duplicates to avoid ambiguous short slug resolution
    for dup in duplicate_basenames:
        if dup in slug_map:
            del slug_map[dup]

    return slug_map


def infer_relation_type(context: str) -> str:
    """Infer relation type based on terms in the surrounding context."""
    ctx_lower = context.lower()
    
    # check implements/implemented_by
    if "implemented by" in ctx_lower or "구현체" in ctx_lower or "구현됨" in ctx_lower:
        return "implemented_by"
    if "implements" in ctx_lower or "구현" in ctx_lower:
        return "implements"
        
    # check depends_on
    if "depends on" in ctx_lower or "depends_on" in ctx_lower or "의존" in ctx_lower or "필수" in ctx_lower:
        return "depends_on"
        
    # check uses
    if "uses" in ctx_lower or "사용" in ctx_lower or "이용" in ctx_lower:
        return "uses"
        
    return "related"


def extract_relations_from_text(text: str, current_slug: str, slug_map: dict[str, str]) -> list[dict]:
    """Parse text body for wikilinks and build semantic relations with evidence & context."""
    # Find all [[target]] or [[target|alias]]
    # We also preserve the optional intent suffix (! or ?) if present, but resolve base target.
    wikilink_re = re.compile(r"\[\[([^\[\]\n]+?)\]\]")
    
    relations = []
    
    for m in wikilink_re.finditer(text):
        raw = m.group(1).strip()
        
        # Split alias
        parts = raw.split("|", 1)
        target = parts[0].strip()
        
        # Remove intent suffix
        if target.endswith("?") or target.endswith("!"):
            target = target[:-1].strip()
            
        # Ignore template placeholders (e.g. {var} or <var>)
        if "{" in target or "}" in target or "<" in target or ">" in target:
            continue
            
        if not target:
            continue

        # Resolve slug
        resolved_target = target
        if "/" not in target:
            # try to resolve short slug
            resolved_target = slug_map.get(target, target)

        if resolved_target == current_slug:
            # skip self-referencing links
            continue

        # Extract context around the link (radius: 40 chars before, 15 chars after)
        start, end = m.span()
        ctx_start = max(0, start - 40)
        ctx_end = min(len(text), end + 15)
        context = text[ctx_start:ctx_end].replace("\n", " ").strip()
        
        # Infer type
        rel_type = infer_relation_type(context)
        
        # Build relation object conforming to schema
        relations.append({
            "type": rel_type,
            "target": resolved_target,
            "confidence": {
                "semantic": 0.80,
                "structural": 0.90,
                "provenance": 0.95
            },
            "verified_by": ["system"],
            "evidence": [f"content/{current_slug.split('/')[-1]}.md"],
            "reason": f"Auto-extracted from context: '{context}'"
        })
        
    return relations


def main():
    parser = argparse.ArgumentParser(description="Migrate wikilinks to relations in frontmatter.")
    parser.add_argument("--vault", help="Name of the vault to process (default: active vault)")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run only)")
    args = parser.parse_args()

    # Resolve vault
    try:
        from raven.core import resolve_active_vault
        vault = resolve_active_vault(args.vault)
    except Exception as e:
        print(f"Error resolving vault: {e}")
        sys.exit(1)

    print(f"[*] Processing vault: {vault.meta.name} ({vault.root})")
    print(f"[*] Mode: {'APPLY (Modifying files)' if args.apply else 'DRY-RUN (No changes)'}")

    # Build slug map for short-slug resolution
    slug_map = build_slug_map(vault)
    print(f"[*] Built slug map with {len(slug_map)} unique pages.")

    modified_count = 0
    total_relations_added = 0

    # Scan and process all .md files
    for p in vault.content_root.rglob("*.md"):
        rel_path = p.relative_to(vault.root)
        if any(part in {"raw", "_archive", "_meta", "scripts", "_index"} for part in rel_path.parts):
            continue
        if str(rel_path.as_posix()) == "content/index.md":
            continue
            
        try:
            raw_text = p.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  [Error] Failed to read {p.name}: {e}")
            continue

        rel_path = p.relative_to(vault.root)
        current_slug = str(rel_path.with_suffix("")).replace("\\", "/")

        meta, body = fm_mod.parse(raw_text)
        if meta is None:
            meta = {}

        # Parse relations from body text
        extracted_rels = extract_relations_from_text(body, current_slug, slug_map)
        if not extracted_rels:
            continue

        existing_rels = meta.get("relations") or []
        if not isinstance(existing_rels, list):
            existing_rels = []

        # Merge extracted relations into existing relations
        # Match by (target, type) to avoid duplicates
        merged_rels = list(existing_rels)
        added_in_file = 0

        for ext_rel in extracted_rels:
            # Check if this target and type already exist
            duplicate = False
            for exist_rel in existing_rels:
                if not isinstance(exist_rel, dict):
                    continue
                if exist_rel.get("target") == ext_rel["target"] and exist_rel.get("type") == ext_rel["type"]:
                    duplicate = True
                    break
            
            if not duplicate:
                merged_rels.append(ext_rel)
                added_in_file += 1

        if added_in_file > 0:
            modified_count += 1
            total_relations_added += added_in_file
            
            print(f"  [+] {current_slug}: Added {added_in_file} new relations.")
            
            if args.apply:
                meta["relations"] = merged_rels
                new_content = fm_mod.render(meta, body)
                p.write_text(new_content, encoding="utf-8")

    print(f"\n[Done] Processed all files.")
    print(f"       Total files with new relations: {modified_count}")
    print(f"       Total relations added: {total_relations_added}")
    if not args.apply:
        print(f"       (Run with --apply to actually modify the files)")


if __name__ == "__main__":
    main()
