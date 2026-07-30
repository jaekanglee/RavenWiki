"""raven.core.link — wikilink parser + audit.

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


def _scan_targets(
    vault: Vault, pages: Optional[list[tuple[str, str]]]
) -> list[tuple[str, str]]:
    """(slug, text) 목록. `pages`가 주어지면 그것을 쓰고, 없으면 vault를 직접 스캔한다.

    v0.7.179 (docs/issues/link-module-rglob-3회-잔여.md): `lint.run_all()`은 이미
    한 번 스캔한 목록을 `_ScanCache`에 갖고 있다. 그걸 넘겨받아 find_* 세 함수가
    같은 vault를 세 번 다시 rglob하지 않게 한다. `None`은 기존 동작(직접 스캔)이며,
    빈 목록과 구분된다 — 빈 목록은 "스캔할 페이지가 없다"는 유효한 입력이다.
    """
    if pages is not None:
        return list(pages)
    return [
        (str(p.relative_to(vault.root))[:-3], p.read_text(errors="replace"))
        for p in vault.content_root.rglob("*.md")
    ]


def find_broken(
    vault: Vault,
    slug: Optional[str] = None,
    *,
    pages: Optional[list[tuple[str, str]]] = None,
) -> list[dict]:
    """Return wikilinks whose target does not exist in the vault.

    Excludes intentional placeholders (`[[x]]?` and `[[x]]!` are by design).
    """
    if slug:
        fp = vault.root / f"{slug}.md"
        if not fp.exists():
            return [{"source_slug": slug, "target": "(missing source)", "intent": "auto"}]
        targets = [(slug, fp.read_text(errors="replace"))]
    else:
        targets = _scan_targets(vault, pages)
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


def find_missing(
    vault: Vault,
    slug: Optional[str] = None,
    *,
    pages: Optional[list[tuple[str, str]]] = None,
) -> list[dict]:
    """Return intentional placeholder wikilinks (`[[x]]?`) whose target still doesn't exist."""
    if slug:
        fp = vault.root / f"{slug}.md"
        if not fp.exists():
            return []
        targets = [(slug, fp.read_text(errors="replace"))]
    else:
        targets = _scan_targets(vault, pages)
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


def rewrite_links(
    vault: Vault,
    old_slug: str,
    new_slug: str,
    *,
    excluded: Optional[set[str]] = None,
) -> int:
    """Rewrite every inbound ``[[old_slug]]`` wikilink to ``[[new_slug]]``.

    Preserves the optional intent suffix (``!``/``?``). Returns the number
    of occurrences rewritten across the vault. Relocated from
    ``raven.mcp.tools.write.wiki_rename`` (v0.7.68, 평가 B#2) — pure file
    I/O with no MCP-specific state, so CLI/MCP rename share one implementation.
    """
    excluded = excluded or {"raw", "_archive", "scripts", "node_modules", ".venv", ".git", "dashboard"}
    pattern = re.compile(r"\[\[" + re.escape(old_slug) + r"(!|\?)?\]\]")
    rewritten = 0
    for md in vault.root.rglob("*.md"):
        if any(part in excluded for part in md.relative_to(vault.root).parts):
            continue
        try:
            content = md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new_content, n = pattern.subn(
            lambda m: "[[" + new_slug + (m.group(1) or "") + "]]",
            content,
        )
        if n > 0:
            md.write_text(new_content, encoding="utf-8")
            rewritten += n
    return rewritten


def find_broken_intent(
    vault: Vault,
    slug: Optional[str] = None,
    *,
    pages: Optional[list[tuple[str, str]]] = None,
) -> list[dict]:
    """#2: `[[x]]!` 인데 target 존재 → CRITICAL (잘못된 intent).

    의도적으로 broken 표시했는데 실제론 존재 → 모순. 사용자가 확인 필요.
    """
    if slug:
        fp = vault.root / f"{slug}.md"
        if not fp.exists():
            return []
        targets = [(slug, fp.read_text(errors="replace"))]
    else:
        targets = _scan_targets(vault, pages)
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
