"""Tests for raven.core.frontmatter — parse, render, merge."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.frontmatter import merge, parse, render


# ─── parse ───────────────────────────────────────────────────


def test_parse_empty_string():
    meta, body = parse("")
    assert meta == {}
    assert body == ""


def test_parse_no_frontmatter():
    meta, body = parse("# hello\nbody text\n")
    assert meta == {}
    assert body.startswith("# hello")


def test_parse_simple_keys():
    text = "---\ntitle: Foo\ntype: concept\n---\n\nbody\n"
    meta, body = parse(text)
    assert meta == {"title": "Foo", "type": "concept"}
    assert body == "body\n"


def test_parse_list_tags():
    text = "---\ntags: [a, b, c]\n---\n\n"
    meta, _ = parse(text)
    assert meta["tags"] == ["a", "b", "c"]


def test_parse_empty_list():
    text = "---\ntags: []\n---\n\n"
    meta, _ = parse(text)
    assert meta["tags"] == []


def test_parse_ignores_nested_keys():
    text = "---\nagents:\n  - name: bot\n    timestamp: 2026-06-25\n---\n\nbody\n"
    meta, body = parse(text)
    # top-level only: 'agents' shows up as empty string (presence only)
    # nested lines are skipped
    assert meta.get("agents") == ""
    assert body == "body\n"


def test_parse_malformed_returns_empty_meta():
    # only opening '---', no closing
    text = "---\ntitle: Foo\nstill going\n"
    meta, _ = parse(text)
    assert meta == {}


# ─── render ──────────────────────────────────────────────────


def test_render_simple():
    out = render({"title": "Foo", "type": "concept"}, "body text")
    assert out.startswith("---\n")
    assert "title: Foo" in out
    assert "type: concept" in out
    assert "body text" in out
    assert out.endswith("\n")


def test_render_list_value():
    out = render({"title": "Foo", "tags": ["a", "b"]}, "")
    assert "tags: [a, b]" in out


def test_render_with_agents():
    out = render(
        {"title": "Foo"},
        "body",
        agents=[{"name": "bot", "timestamp": "2026-06-25T10:00:00", "run_id": "r1", "intent": "test"}],
    )
    assert "agents:" in out
    assert "  - name: bot" in out
    assert "    timestamp: 2026-06-25T10:00:00" in out
    assert "    run_id: r1" in out
    assert "    intent: test" in out


def test_render_without_agents_no_block():
    out = render({"title": "Foo"}, "body")
    assert "agents:" not in out


def test_render_roundtrip():
    original = "---\ntitle: Foo\ntype: concept\ntags: [a, b]\n---\n\nbody\n"
    meta, body = parse(original)
    rendered = render(meta, body)
    assert "title: Foo" in rendered
    assert "type: concept" in rendered
    assert "tags: [a, b]" in rendered


# ─── merge ───────────────────────────────────────────────────


def test_merge_preserves_created():
    existing = {"created": "2026-01-01", "title": "Old"}
    out = merge(existing, {"created": "2099-12-31", "title": "New"})
    assert out["created"] == "2026-01-01"  # preserved
    assert out["title"] == "New"           # updated


def test_merge_updated_forced_to_today():
    existing = {"updated": "2026-01-01"}
    out = merge(existing, {"updated": "2099-12-31"}, today="2026-06-25")
    assert out["updated"] == "2026-06-25"


def test_merge_tags_string_split():
    out = merge({}, {"tags": "a, b, c"})
    assert out["tags"] == ["a", "b", "c"]


def test_merge_tags_string_single():
    out = merge({}, {"tags": "solo"})
    assert out["tags"] == ["solo"]


def test_merge_tags_list_passthrough():
    out = merge({}, {"tags": ["x", "y"]})
    assert out["tags"] == ["x", "y"]


def test_merge_tags_none_becomes_empty():
    out = merge({}, {"tags": None})
    assert out["tags"] == []


def test_merge_no_created_in_existing_uses_updates():
    out = merge({}, {"created": "2026-05-01", "title": "X"})
    assert out["created"] == "2026-05-01"


def test_merge_no_created_anywhere_uses_today():
    out = merge({}, {"title": "X"}, today="2026-06-25")
    assert out["created"] == "2026-06-25"
    assert out["updated"] == "2026-06-25"


def test_merge_agents_key_skipped():
    out = merge({}, {"agents": [{"name": "bot"}], "title": "X"})
    assert "agents" not in out
    assert out["title"] == "X"


def test_merge_tags_tuple_becomes_list():
    """AgentScope.default_tags is a tuple — must not stringify it."""
    out = merge({}, {"tags": ("agent-output",)})
    assert out["tags"] == ["agent-output"]


def test_merge_tags_list_of_tuples_flattened():
    out = merge({}, {"tags": [("a", "b"), "c"]})
    assert out["tags"] == ["('a', 'b')", "c"]


def test_merge_does_not_mutate_existing():
    existing = {"title": "Old", "tags": ["a"]}
    updates = {"title": "New", "tags": ["b"]}
    out = merge(existing, updates)
    assert existing == {"title": "Old", "tags": ["a"]}  # unchanged
    assert out["title"] == "New"
    assert out["tags"] == ["b"]
