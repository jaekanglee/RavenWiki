"""wikisys.core.link — wikilink parser + audit.

Public surface:
    find_broken(vault)    → list of {source_slug, target, intent}
    find_missing(vault)   → list of {source_slug, target}
    parse(text)           → list of {target, intent, offset}

Intent suffix:
    [[link]]      → "auto"   (normal link, target should exist)
    [[link]]!     → "broken" (intentional broken — CRITICAL if target exists)
    [[link]]?     → "missing" (intentional placeholder — INFO if target missing)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .vault import Vault


WIKILINK_RE = re.compile(r"\[\[([^\[\]\n]+?)\]\]([!?]?)")


@dataclass(frozen=True)
class Link:
    target: str
    intent: str  # "auto" | "broken" | "missing"
    offset: int


def parse(text: str) -> list[Link]:
    """Extract all wikilinks with intent from raw markdown text."""
    out = []
    for m in WIKILINK_RE.finditer(text):
        target = m.group(1).strip()
        suffix = m.group(2)
        intent = {"!": "broken", "?": "missing"}.get(suffix, "auto")
        out.append(Link(target=target, intent=intent, offset=m.start()))
    return out


def _resolve(slug_or_target: str) -> str:
    """Strip alias part (`Page|display`) and return clean slug."""
    return slug_or_target.split("|", 1)[0].strip()


def find_broken(vault: Vault, slug: Optional[str] = None) -> list[dict]:
    """Return wikilinks whose target does not exist in the vault.

    Excludes intentional placeholders (`[[x]]?` and `[[x]]!` are by design).
    """
    if slug:
        fp = vault.root / f"{slug}.md"
        if not fp.exists():
            return [{"source_slug": slug, "target": "(missing source)", "intent": "auto"}]
        targets = [(slug, fp.read_text(errors="replace"))]
    else:
        targets = [
            (str(p.relative_to(vault.root))[:-3], p.read_text(errors="replace"))
            for p in vault.content_root.rglob("*.md")
        ]
    out = []
    for src, text in targets:
        for lnk in parse(text):
            if lnk.intent != "auto":
                continue
            tgt = _resolve(lnk.target)
            if "/" not in tgt:
                continue
            if not (vault.root / f"{tgt}.md").exists():
                out.append({"source_slug": src, "target": tgt, "intent": lnk.intent})
    return out


def find_missing(vault: Vault, slug: Optional[str] = None) -> list[dict]:
    """Return intentional placeholder wikilinks (`[[x]]?`) whose target still doesn't exist."""
    if slug:
        fp = vault.root / f"{slug}.md"
        if not fp.exists():
            return []
        targets = [(slug, fp.read_text(errors="replace"))]
    else:
        targets = [
            (str(p.relative_to(vault.root))[:-3], p.read_text(errors="replace"))
            for p in vault.content_root.rglob("*.md")
        ]
    out = []
    for src, text in targets:
        for lnk in parse(text):
            if lnk.intent != "missing":
                continue
            tgt = _resolve(lnk.target)
            if "/" not in tgt:
                continue
            if not (vault.root / f"{tgt}.md").exists():
                out.append({"source_slug": src, "target": tgt, "intent": lnk.intent})
    return out


def find_broken_intent(vault: Vault, slug: Optional[str] = None) -> list[dict]:
    """#2: `[[x]]!` 인데 target 존재 → CRITICAL (잘못된 intent).

    의도적으로 broken 표시했는데 실제론 존재 → 모순. 사용자가 확인 필요.
    """
    if slug:
        fp = vault.root / f"{slug}.md"
        if not fp.exists():
            return []
        targets = [(slug, fp.read_text(errors="replace"))]
    else:
        targets = [
            (str(p.relative_to(vault.root))[:-3], p.read_text(errors="replace"))
            for p in vault.content_root.rglob("*.md")
        ]
    out = []
    for src, text in targets:
        for lnk in parse(text):
            if lnk.intent != "broken":
                continue
            tgt = _resolve(lnk.target)
            if "/" not in tgt:
                continue
            if (vault.root / f"{tgt}.md").exists():
                out.append({"source_slug": src, "target": tgt, "intent": lnk.intent})
    return out
