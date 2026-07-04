"""tests/test_contracts.py — regression guards for raven.core.contracts.

These tests are the contract's spec — they encode what `write_page()` MUST
do so the entrypoints (CLI/API/Agent) can rely on it.

v0.6.2+: required to merge the contracts refactor (AGENTS.md §8 mandates
minimum 5 tests for any write contract change).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from raven.core.contracts import write_page
from raven.core.registry import VaultMeta
from raven.core.vault import Vault


# ────────────────────────── fixtures ───────────────────────────────


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    """Minimal vault in a temp dir, content/ pre-created."""
    (tmp_path / "content").mkdir()
    meta = VaultMeta(name="test", path=tmp_path, mode="personal", owner="user")
    return Vault.load(meta)


# ────────────────────────── tests ───────────────────────────────────


def test_write_page_creates_new_file(vault: Vault) -> None:
    """Happy path: create a brand-new page."""
    result = write_page(
        vault, "hello", "body", title="Hello", type="concept", tags=["demo"]
    )
    assert result.ok is True
    assert result.slug == "content/hello"
    assert result.created is True
    assert result.created_date is not None
    assert (vault.root / "content" / "hello.md").is_file()
    text = (vault.root / "content" / "hello.md").read_text()
    assert "title: Hello" in text
    assert "type: concept" in text
    assert "created:" in text  # set on first write


def test_write_page_overwrite_preserves_created(vault: Vault) -> None:
    """Overwrite must preserve `created` date (matches CLI/API pre-v0.6.2)."""
    r1 = write_page(vault, "hello", "v1", title="Hello")
    assert r1.ok and r1.created is True
    first_created = r1.created_date

    r2 = write_page(vault, "hello", "v2", overwrite=True)
    assert r2.ok and r2.created is False
    assert r2.created_date == first_created  # preserved
    text = (vault.root / "content" / "hello.md").read_text()
    assert "v2" in text


def test_write_page_rejects_exists_when_no_overwrite(vault: Vault) -> None:
    """create-only semantics: 409-style error without touching disk."""
    write_page(vault, "hello", "v1")
    r = write_page(vault, "hello", "v2", overwrite=False)
    assert r.ok is False
    assert r.error == "exists"
    # file unchanged
    assert "v1" in (vault.root / "content" / "hello.md").read_text()


def test_write_page_normalize_prefixes_short_slugs(vault: Vault) -> None:
    """CLI/API behavior: bare slug auto-prefixed to content/."""
    r = write_page(vault, "hello", "body", normalize=True)
    assert r.ok
    assert r.slug == "content/hello"
    assert (vault.root / "content" / "hello.md").is_file()
    # no file at vault root
    assert not (vault.root / "hello.md").exists()


def test_write_page_normalize_false_keeps_bare_slug(vault: Vault) -> None:
    """Agent behavior: bare slug stays at vault root (LLM agent uses explicit paths)."""
    r = write_page(vault, "hello", "body", normalize=False)
    assert r.ok
    assert r.slug == "hello"
    assert (vault.root / "hello.md").is_file()
    assert not (vault.root / "content" / "hello.md").exists()


def test_write_page_rejects_bad_slug(vault: Vault) -> None:
    """Bad slug returns ok=False with descriptive error (no disk write)."""
    r = write_page(vault, "../bad", "x")
    assert r.ok is False
    assert "invalid slug" in (r.error or "")
    assert not (vault.root / "bad.md").exists()


def test_write_page_preserves_block_style_tags(vault: Vault) -> None:
    """평가 A#3 회귀 가드: Obsidian 표준 블록 리스트 tags가 있는 페이지를
    write_page로 갱신해도 tags가 소실되지 않는다 (pre-v0.7.67 데이터 손실 버그)."""
    fp = vault.root / "content" / "hello.md"
    fp.write_text(
        "---\ntitle: Hello\ntype: concept\ncreated: 2026-01-01\n"
        "tags:\n  - alpha\n  - beta\n---\n\nv1\n",
        encoding="utf-8",
    )
    r = write_page(vault, "content/hello", "v2", overwrite=True)
    assert r.ok
    from raven.core.frontmatter import parse
    meta, body = parse(fp.read_text(encoding="utf-8"))
    assert meta["tags"] == ["alpha", "beta"]  # NOT erased
    assert meta["created"] == "2026-01-01"
    assert "v2" in body


def test_write_page_preserves_existing_agents_history(vault: Vault) -> None:
    """평가 A#3 회귀 가드: 기존 agents: 이력이 있는 페이지에 새 actor로 쓰면
    이력이 초기화되지 않고 append된다."""
    fp = vault.root / "content" / "hello.md"
    fp.write_text(
        "---\ntitle: Hello\ntype: concept\nagents:\n"
        "  - name: old-bot\n    timestamp: 2026-01-01T00:00:00\n---\n\nv1\n",
        encoding="utf-8",
    )
    actor = {"name": "new-bot", "timestamp": "2026-06-27T00:00:00"}
    r = write_page(vault, "content/hello", "v2", actor=actor, overwrite=True)
    assert r.ok
    from raven.core.frontmatter import parse
    meta, _ = parse(fp.read_text(encoding="utf-8"))
    names = [a["name"] for a in meta["agents"]]
    assert names == ["old-bot", "new-bot"]  # history preserved + appended


def test_write_page_with_actor_attaches_agents_list(vault: Vault) -> None:
    """Agent provenance attaches as YAML list block (not Python repr)."""
    actor = {"name": "test-bot", "run_id": "r-1", "timestamp": "2026-06-27T00:00:00", "intent": "verify"}
    r = write_page(
        vault, "content/hello", "body",
        title="Hi", type="concept",
        actor=actor, overwrite=True,
    )
    assert r.ok
    text = (vault.root / "content" / "hello.md").read_text()
    # YAML list rendering (per frontmatter.render), not Python dict repr
    assert "agents:" in text
    assert "  - name: test-bot" in text
    assert "    timestamp: 2026-06-27T00:00:00" in text
    assert "    run_id: r-1" in text
    # Python repr would look like: agents: [{'name': ...}]
    assert "[{" not in text
