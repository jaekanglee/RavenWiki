import os
import re
import sys
from pathlib import Path

def main():
    if len(sys.argv) > 1:
        vault_root = Path(sys.argv[1])
    else:
        vaults_dir = Path(os.environ.get("RAVEN_VAULTS_DIR", Path.home() / "Raven"))
        vault_root = vaults_dir / "raven-dev"
    content_dir = vault_root / "content"
    
    # 1. 스캔하여 basename -> full slug 맵 구축
    # slug = content/concept/filename (확장자 제외, slash 구분자)
    slug_map = {}
    duplicate_basenames = set()
    
    for p in content_dir.rglob("*.md"):
        # content 기준 relative path
        rel_path = p.relative_to(vault_root)
        slug = str(rel_path.with_suffix("")).replace("\\", "/")
        basename = p.stem
        
        if basename in slug_map:
            duplicate_basenames.add(basename)
        else:
            slug_map[basename] = slug

    # 중복 제거
    for dup in duplicate_basenames:
        if dup in slug_map:
            del slug_map[dup]
            
    print(f"[Scan] Found {len(slug_map)} unique page basenames. (Duplicates: {list(duplicate_basenames)})")

    # 2. 각 파일의 wikilink 보정
    # regex: [[target]] or [[target|alias]]
    # we match everything inside [[...]] which does not contain [ or ]
    wikilink_re = re.compile(r"\[\[([^\[\]\n]+?)\]\]")
    
    total_files_modified = 0
    total_links_fixed = 0

    for p in content_dir.rglob("*.md"):
        content = p.read_text(encoding="utf-8")
        modified = False
        
        def replace_link(match):
            nonlocal modified, total_links_fixed
            raw = match.group(1).strip()
            
            # alias | 가 있으면 분리
            parts = raw.split("|", 1)
            target = parts[0].strip()
            alias = f"|{parts[1]}" if len(parts) > 1 else ""
            
            # intent marker (? or !) 가 있으면 떼어둠
            suffix = ""
            if target.endswith("?") or target.endswith("!"):
                suffix = target[-1]
                target = target[:-1].strip()
                
            # target에 이미 '/'가 들어가 있거나 (예: content/concept/...)
            # target이 template placeholder(예: {x}) 인 경우는 스킵
            if "/" in target or "{" in target or "}" in list(target) or len(target) <= 1:
                return match.group(0)
                
            if target in slug_map:
                new_target = slug_map[target]
                fixed_raw = f"{new_target}{suffix}{alias}"
                total_links_fixed += 1
                modified = True
                print(f"  Fixed in {p.name}: [[{raw}]] -> [[{fixed_raw}]]")
                return f"[[{fixed_raw}]]"
                
            return match.group(0)
            
        new_content = wikilink_re.sub(replace_link, content)
        
        if modified:
            p.write_text(new_content, encoding="utf-8")
            total_files_modified += 1

    print(f"\n[Done] Fixed {total_links_fixed} links across {total_files_modified} files.")

if __name__ == "__main__":
    main()
