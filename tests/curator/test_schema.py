"""raven.curator.schema — collections.yaml 검증 테스트.

v3 합의안 4종 path 검증:
- `**` ❌
- bare `*` ❌ (단, `*.md` ✅)
- `..` ❌
- 절대경로 ❌
- content/ 또는 _ 시작
"""
from __future__ import annotations

from pathlib import Path

import pytest

from raven.curator.schema import (
    CollectionsYaml,
    CollectionsYamlError,
    load_and_validate,
    validate_path,
    validate_paths,
)


# ───────────── validate_path ─────────────

def test_validate_path_simple():
    validate_path("content/harumoa")
    validate_path("_meta/log.md")
    validate_path("content/_system/llm-wiki.md")


def test_validate_path_rejects_double_star():
    with pytest.raises(CollectionsYamlError, match="\\*\\*"):
        validate_path("content/**")


def test_validate_path_rejects_double_star_mid():
    with pytest.raises(CollectionsYamlError, match="\\*\\*"):
        validate_path("content/**/foo.md")


def test_validate_path_rejects_bare_star():
    """`*`이 단일 segment 전체면 ❌."""
    with pytest.raises(CollectionsYamlError, match="bare"):
        validate_path("content/*")


def test_validate_path_accepts_md_suffix_glob():
    """`*.md`는 단일 레벨 suffix glob으로 ✅."""
    validate_path("content/*.md")


def test_validate_path_rejects_partial_glob():
    """`foo*bar`, `*foo` 같은 부분 글롭 ❌."""
    with pytest.raises(CollectionsYamlError, match="partial glob"):
        validate_path("content/foo*bar")
    with pytest.raises(CollectionsYamlError, match="partial glob"):
        validate_path("content/*foo")


def test_validate_path_rejects_parent_traversal():
    with pytest.raises(CollectionsYamlError, match="parent traversal"):
        validate_path("../etc/passwd")
    with pytest.raises(CollectionsYamlError, match="parent traversal"):
        validate_path("content/../escape")


def test_validate_path_rejects_absolute():
    with pytest.raises(CollectionsYamlError, match="absolute"):
        validate_path("/etc/passwd")


def test_validate_path_requires_content_or_underscore():
    with pytest.raises(CollectionsYamlError, match="must start with"):
        validate_path("etc/foo")


def test_validate_path_empty():
    with pytest.raises(CollectionsYamlError, match="empty"):
        validate_path("")


# ───────────── validate_paths (batch) ─────────────

def test_validate_paths_first_violation_raises():
    with pytest.raises(CollectionsYamlError):
        validate_paths(["content/harumoa", "content/**"])


def test_validate_paths_all_valid():
    validate_paths(["content/harumoa", "content/homeauto/*.md", "_meta/log.md"])


# ───────────── load_and_validate ─────────────

def test_load_minimal_yaml(tmp_path: Path):
    p = tmp_path / "collections.yaml"
    p.write_text(
        """schema_version: 1
defaults:
  first_run_strategy: skip_silent
  sync_policy: warn
collections:
  - id: harumoa
    paths:
      - content/harumoa
    description: Harumoa project
"""
    )
    y = load_and_validate(p)
    assert y.schema_version == 1
    assert len(y.collections) == 1
    assert y.collections[0].id == "harumoa"
    assert y.collections[0].paths == ["content/harumoa"]
    assert y.collections[0].first_run_strategy == "skip_silent"
    assert y.collections[0].auto_detect is True  # default


def test_load_full_yaml(tmp_path: Path):
    p = tmp_path / "collections.yaml"
    p.write_text(
        """schema_version: 1
collections:
  - id: wiki-core
    vault: wiki
    paths:
      - content/_system
      - content/*.md
    description: Core wiki
    auto_detect: false
    first_run_strategy: full_scan
  - id: retired
    paths:
      - content/old
    retired_at: '2026-05-01'
    merged_into: wiki-core
"""
    )
    y = load_and_validate(p)
    assert len(y.collections) == 2
    wiki = y.collections[0]
    assert wiki.vault == "wiki"
    assert wiki.auto_detect is False
    assert wiki.first_run_strategy == "full_scan"
    retired = y.collections[1]
    assert retired.is_active is False
    assert retired.merged_into == "wiki-core"


def test_load_missing_schema_version(tmp_path: Path):
    p = tmp_path / "collections.yaml"
    p.write_text("collections: []\n")
    with pytest.raises(CollectionsYamlError, match="schema_version missing"):
        load_and_validate(p)


def test_load_wrong_schema_version(tmp_path: Path):
    p = tmp_path / "collections.yaml"
    p.write_text("schema_version: 99\ncollections: []\n")
    with pytest.raises(CollectionsYamlError, match="schema_version mismatch"):
        load_and_validate(p)


def test_load_duplicate_id(tmp_path: Path):
    p = tmp_path / "collections.yaml"
    p.write_text(
        """schema_version: 1
collections:
  - id: harumoa
    paths: [content/harumoa]
  - id: harumoa
    paths: [content/homeauto]
"""
    )
    with pytest.raises(CollectionsYamlError, match="duplicate id"):
        load_and_validate(p)


def test_load_invalid_first_run_strategy(tmp_path: Path):
    p = tmp_path / "collections.yaml"
    p.write_text(
        """schema_version: 1
collections:
  - id: harumoa
    paths: [content/harumoa]
    first_run_strategy: nonsense
"""
    )
    with pytest.raises(CollectionsYamlError, match="first_run_strategy"):
        load_and_validate(p)


def test_load_invalid_path_in_yaml(tmp_path: Path):
    p = tmp_path / "collections.yaml"
    p.write_text(
        """schema_version: 1
collections:
  - id: bad
    paths:
      - content/**
"""
    )
    with pytest.raises(CollectionsYamlError, match="harumoa|recursion"):
        # line 4 area; error format includes line number
        load_and_validate(p)


def test_load_missing_paths(tmp_path: Path):
    p = tmp_path / "collections.yaml"
    p.write_text(
        """schema_version: 1
collections:
  - id: harumoa
"""
    )
    with pytest.raises(CollectionsYamlError, match="paths must be non-empty"):
        load_and_validate(p)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
