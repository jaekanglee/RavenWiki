"""frontmatter — single source of truth for parsing + rendering markdown frontmatter.

Public surface:
    parse(text) -> tuple[dict, str]
        Split `text` into (meta_dict, body). Handles simple `key: value` and
        `key: [a, b, c]` list forms. No nested YAML for now (kept simple on
        purpose — see raven-guide.md "frontmatter rules").

    render(meta, body, *, agents=None) -> str
        Render frontmatter + body. Preserves key insertion order. Appends
        optional `agents:` provenance block at the end (one entry per agent).

    merge(existing, updates, *, today=None) -> dict
        Apply `updates` to `existing` with safety rules:
            - 'created' is preserved from existing (never overwritten)
            - 'updated' is forced to `today` (default: date.today())
            - 'tags' is forced to list (str input is split on comma)
            - 'agents' (if present) is preserved as-is

Designed to replace the three duplicated implementations in cli/api/agents.
"""
from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Optional, Union


LIST_RE = re.compile(r"^\[(.*)\]$")


def _parse_value(raw: str):
    """Parse a frontmatter value into a Python value.

    - '[a, b, c]' → ['a', 'b', 'c']
    - otherwise → strip whitespace, return as str (don't lie about types)
    """
    s = raw.strip()
    m = LIST_RE.match(s)
    if m:
        inner = m.group(1).strip()
        if not inner:
            return []
        # simple comma split — no nested quotes/comma handling for now
        return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
    return s


def parse(text: str) -> tuple[dict, str]:
    """Split markdown into (frontmatter_dict, body_str).

    Returns ({}, text) if no frontmatter present.
    """
    if not text or not text.startswith("---\n"):
        return {}, text
    try:
        _, fm_block, body = text.split("---\n", 2)
    except ValueError:
        # malformed (only one '---' line, no closing)
        return {}, text
    meta: dict = {}
    for line in fm_block.splitlines():
        line = line.rstrip()
        if not line or ":" not in line:
            continue
        # nested keys (like '  - name: x') are skipped; only top-level
        if line.startswith(" ") or line.startswith("\t"):
            continue
        key, _, raw_val = line.partition(":")
        meta[key.strip()] = _parse_value(raw_val)
    return meta, body.lstrip("\n")


def render(
    meta: dict,
    body: str,
    *,
    agents: Optional[list[dict]] = None,
) -> str:
    """Render frontmatter + body as markdown.

    Args:
        meta: frontmatter dict (insertion order preserved in Python 3.7+).
        body: markdown body text (without leading newline).
        agents: optional list of provenance dicts. Each must have
                `name`, `timestamp`; optionally `run_id`, `intent`.
                Rendered as:
                    agents:
                      - name: x
                        timestamp: y
                        run_id: z
    """
    lines = ["---"]
    for k, v in meta.items():
        lines.append(_format_field(k, v))
    if agents:
        lines.append("agents:")
        for entry in agents:
            lines.append(f"  - name: {entry['name']}")
            lines.append(f"    timestamp: {entry['timestamp']}")
            if entry.get("run_id"):
                lines.append(f"    run_id: {entry['run_id']}")
            if entry.get("intent"):
                lines.append(f"    intent: {entry['intent']}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


def _format_field(key: str, value) -> str:
    """Format a single frontmatter field."""
    if isinstance(value, list):
        items = ", ".join(str(x) for x in value)
        return f"{key}: [{items}]"
    if isinstance(value, bool):
        return f"{key}: {str(value).lower()}"
    return f"{key}: {value}"


def merge(
    existing: dict,
    updates: dict,
    *,
    today: Optional[str] = None,
) -> dict:
    """Apply `updates` to `existing` with safety rules.

    Rules:
        - 'created': preserved from `existing`; never overwritten by updates
                     (even if explicitly set in updates)
        - 'updated': forced to `today` (default: date.today().isoformat())
        - 'tags': forced to list. If str passed, split on comma.
        - 'agents': preserved as-is (caller passes fresh agents separately
                     to `render()`; do not include in `updates`)
        - all other keys: updates win; fall back to existing

    Returns a NEW dict (does not mutate existing).
    """
    today = today or _dt.date.today().isoformat()
    out = dict(existing)  # copy
    # apply updates except 'created' and 'updated'
    for k, v in updates.items():
        if k == "created":
            continue  # never overwrite
        if k == "updated":
            continue  # forced below
        if k == "tags":
            out[k] = _coerce_tags(v)
            continue
        if k == "agents":
            # skip — caller handles provenance separately via render()
            continue
        out[k] = v
    # 'created' preservation
    if "created" in existing:
        out["created"] = existing["created"]
    elif "created" in updates:
        out["created"] = updates["created"]
    else:
        out["created"] = today
    # 'updated' forced
    out["updated"] = today
    return out


def _coerce_tags(v) -> list[str]:
    """Normalize a tags value to list[str]. Accepts None/str/list/tuple."""
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if x]
    if isinstance(v, str):
        # comma-separated? otherwise single
        if "," in v:
            return [x.strip() for x in v.split(",") if x.strip()]
        return [v.strip()] if v.strip() else []
    return [str(v)]
