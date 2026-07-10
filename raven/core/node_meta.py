"""Shared minimal node metadata helpers."""
from __future__ import annotations

import json
from typing import Any


def collection_for_slug(slug: str) -> str:
    first = (slug or "").split("/", 1)[0].strip()
    return first or "root"


def normalize_status(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "current"


def normalize_aliases(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = []
    aliases: list[str] = []
    seen: set[str] = set()
    for item in items:
        alias = str(item).strip()
        if not alias or alias in seen:
            continue
        aliases.append(alias)
        seen.add(alias)
    return aliases


def aliases_to_json(value: Any) -> str:
    return json.dumps(normalize_aliases(value), ensure_ascii=False)


def aliases_from_json(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return normalize_aliases(value)
    try:
        return normalize_aliases(json.loads(str(value)))
    except Exception:
        return normalize_aliases(value)
