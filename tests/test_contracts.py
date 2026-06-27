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
