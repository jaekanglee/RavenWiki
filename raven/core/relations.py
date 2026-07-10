"""Shared semantic relation contract.

Markdown frontmatter is the source of truth, but every writer/indexer must
agree on the same minimal relation invariant before data reaches wiki.db.
"""
from __future__ import annotations

from typing import Any


SEMANTIC_RELATION_TYPES: frozenset[str] = frozenset(
    {"uses", "depends_on", "implements", "implemented_by", "related"}
)


def is_valid_relation_type(value: Any) -> bool:
    return isinstance(value, str) and value in SEMANTIC_RELATION_TYPES


def has_relation_evidence(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return value is not None


def has_relation_reason(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_valid_relation_payload(rel: Any) -> bool:
    if not isinstance(rel, dict):
        return False
    if not is_valid_relation_type(rel.get("type")):
        return False
    target = rel.get("target")
    if not isinstance(target, str) or not target.strip():
        return False
    if not has_relation_evidence(rel.get("evidence")):
        return False
    if not has_relation_reason(rel.get("reason")):
        return False
    return True
