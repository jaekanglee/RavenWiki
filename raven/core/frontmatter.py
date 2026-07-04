"""frontmatter — single source of truth for parsing + rendering markdown frontmatter.

Public surface:
    parse(text) -> tuple[dict, str]
        Split `text` into (meta_dict, body). Parses the frontmatter block as
        real YAML (block lists like `tags:\n  - a` and nested `agents:` blocks
        included), falling back to the legacy line-based parser when the block
        is not valid YAML (e.g. unquoted `title: Foo: bar`). Dates/datetimes
        are normalized to ISO strings; empty values to "" (legacy semantics).

    render(meta, body, *, agents=None) -> str
        Render frontmatter + body. Preserves key insertion order. Scalar lists
        stay in flow style (`tags: [a, b]`); lists of dicts render as block
        sequences (same shape as the `agents:` provenance block). Appends an
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
import json
import re
from typing import Optional

import yaml


LIST_RE = re.compile(r"^\[(.*)\]$")


def _parse_value(raw: str):
    """Parse a frontmatter value into a Python value (legacy fallback).

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


def _parse_lines(fm_block: str) -> dict:
    """Legacy line-based parser — kept as fallback for non-YAML blocks
    (e.g. unquoted `title: Foo: bar` written by pre-v0.7.67 renderers)."""
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
    return meta


def _normalize(value):
    """Normalize YAML-loaded values to legacy-compatible Python values.

    - date/datetime → ISO string (files store dates unquoted; consumers
      compare them as strings)
    - None (empty value after `key:`) → "" (legacy parser semantics)
    - containers normalized recursively
    """
    if value is None:
        return ""
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


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
    meta: Optional[dict] = None
    try:
        loaded = yaml.safe_load(fm_block)
        if isinstance(loaded, dict):
            meta = {str(k): _normalize(v) for k, v in loaded.items()}
    except yaml.YAMLError:
        meta = None
    if meta is None:
        # Not a YAML mapping (or invalid YAML): legacy tolerant parsing.
        meta = _parse_lines(fm_block)
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
        lines.extend(_format_field(k, v))
    if agents:
        lines.append("agents:")
        for entry in agents:
            lines.append(f"  - name: {_scalar(entry['name'])}")
            lines.append(f"    timestamp: {_scalar(entry['timestamp'])}")
            if entry.get("run_id"):
                lines.append(f"    run_id: {_scalar(entry['run_id'])}")
            if entry.get("intent"):
                lines.append(f"    intent: {_scalar(entry['intent'])}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


_SPECIAL_LEAD = set("-?:,[]{}#&*!|>'\"%@`")


def _needs_quote(s: str, *, flow: bool = False) -> bool:
    """True when a plain YAML scalar would parse back differently."""
    if s == "":
        return False  # `key: ` round-trips to "" via _normalize
    if s != s.strip() or "\n" in s:
        return True
    if ": " in s or s.endswith(":") or " #" in s:
        return True
    if s[0] in _SPECIAL_LEAD:
        return True
    if flow and ("," in s or "[" in s or "]" in s):
        return True
    return False


def _scalar(value, *, flow: bool = False) -> str:
    """Format a scalar value, quoting strings only when YAML requires it."""
    if isinstance(value, bool):
        return str(value).lower()
    s = str(value)
    if isinstance(value, str) and _needs_quote(s, flow=flow):
        return json.dumps(s, ensure_ascii=False)  # valid YAML double-quoted
    return s


def _format_field(key: str, value) -> list[str]:
    """Format a single frontmatter field as one or more lines."""
    if isinstance(value, list):
        if value and all(isinstance(x, dict) for x in value):
            # block sequence of mappings (e.g. `agents:` provenance)
            lines = [f"{key}:"]
            for entry in value:
                first = True
                for k, v in entry.items():
                    prefix = "  - " if first else "    "
                    lines.append(f"{prefix}{k}: {_scalar(v)}")
                    first = False
            return lines
        items = ", ".join(_scalar(x, flow=True) for x in value)
        return [f"{key}: [{items}]"]
    if isinstance(value, dict):
        lines = [f"{key}:"]
        for k, v in value.items():
            lines.append(f"  {k}: {_scalar(v)}")
        return lines
    return [f"{key}: {_scalar(value)}"]


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
