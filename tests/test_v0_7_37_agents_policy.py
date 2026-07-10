"""v0.7.37+ — agents opt-in write allowlist regression guard.

Vaults can declare an `agents` allowlist in `.vault.json`. When declared,
ONLY the listed actors may write through `raven.core.contracts.write_page`.
Empty/missing = every actor allowed (backward compatible).

This file locks the contract across the three consumers:
  * raven.core.registry.VaultMeta round-trip (read/write of the field)
  * raven.core.vault.Vault.write_allowed_for (the gate)
  * raven.core.contracts.write_page (enforcement point)

No destructive behavior — opt-in vaults only.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from raven.core.contracts import write_page
from raven.core.registry import VaultMeta
from raven.core.vault import Vault


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path / "registry"))


# ────────────────────────── registry ──────────────────────────


def test_vaultmeta_agents_default_empty_tuple() -> None:
    """A new VaultMeta (no agents) → empty tuple, no policy."""
    meta = VaultMeta(name="x", path=Path("/tmp/x"))
    assert meta.agents == ()


def test_vaultmeta_agents_roundtrip_via_to_json() -> None:
    """Non-empty agents → to_json includes them; empty → omitted."""
    meta = VaultMeta(
        name="x",
        path=Path("/tmp/x"),
        agents=("alice", "bob"),
    )
    out = meta.to_json()
    assert sorted(out["agents"]) == ["alice", "bob"]

    meta_empty = VaultMeta(name="y", path=Path("/tmp/y"))
    assert "agents" not in meta_empty.to_json()


def test_vaultmeta_agents_from_json_normalized_sorted() -> None:
    """from_json normalizes a list of agents into a sorted tuple of strings."""
    meta = VaultMeta.from_json(
        "x",
        {"path": "/tmp/x", "agents": ["bob", "alice", 42]},  # 42 is coerced
        default_name="",
    )
    assert meta.agents == ("42", "alice", "bob")  # sorted, str-coerced


def test_vaultmeta_agents_from_json_missing_defaults_empty() -> None:
    """Vaults without `agents` key → empty tuple (no policy = permissive)."""
    meta = VaultMeta.from_json("x", {"path": "/tmp/x"}, default_name="")
    assert meta.agents == ()


# ────────────────────────── vault.write_allowed_for ──────────────────────────


def _make_vault_with_agents(agents: tuple[str, ...]) -> Vault:
    """Build a throwaway Vault whose meta declares the given agents allowlist."""
    meta = VaultMeta(name="probe", path=Path("/tmp/probe"), agents=agents)
    return Vault(meta=meta, root=meta.path)


def test_write_allowed_no_policy_allows_everyone() -> None:
    """Empty allowlist → permissive (backward compatible)."""
    v = _make_vault_with_agents(())
    assert v.write_allowed_for(None) is True
    assert v.write_allowed_for("anyone") is True
    assert v.write_allowed_for({"name": "anyone"}) is True


def test_write_allowed_blocks_unlisted_actor() -> None:
    """Non-empty allowlist + non-listed actor → False."""
    v = _make_vault_with_agents(("alice", "bob"))
    assert v.write_allowed_for("eve") is False
    assert v.write_allowed_for(None) is False  # anonymous ≠ alice/bob
    assert v.write_allowed_for({"name": "eve"}) is False


def test_write_allowed_admits_listed_actor() -> None:
    """Non-empty allowlist + listed actor → True."""
    v = _make_vault_with_agents(("alice", "bob"))
    assert v.write_allowed_for("alice") is True
    assert v.write_allowed_for("bob") is True
    assert v.write_allowed_for({"name": "alice"}) is True


def test_write_allowed_dict_name_extracted() -> None:
    """Dict actor's `.name` is what the gate checks."""
    v = _make_vault_with_agents(("alice",))
    assert v.write_allowed_for({"name": "alice"}) is True
    assert v.write_allowed_for({"name": "eve"}) is False


def test_write_allowed_object_name_extracted() -> None:
    """Objects with `.name` attribute work too (Agent-style provenance)."""
    class A:
        name = "alice"
    class E:
        name = "eve"

    v = _make_vault_with_agents(("alice",))
    assert v.write_allowed_for(A()) is True
    assert v.write_allowed_for(E()) is False


# ────────────────────────── contracts.write_page gate ──────────────────────────


def test_write_page_allowed_when_no_policy() -> None:
    """End-to-end: vault without agents policy → any actor may write."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "content").mkdir()
        Vault.create(name="probe", path=root, bootstrap=False, profile="basic")
        v = Vault.load(VaultMeta(name="probe", path=root))
        # No agents in the freshly-created vault → write_allowed_for == True
        # for every actor.
        result = write_page(v, "hello", "world", actor="anyone", normalize=False)
        assert result.ok is True, f"expected write ok, got {result}"


def test_write_page_denies_unlisted_actor_returns_error_result() -> None:
    """End-to-end: vault with agents policy + unlisted actor → WriteResult
    with ok=False and a clear error. No file should be created."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "content").mkdir()
        # Bootstrap=False + manually set agents in registry policy
        Vault.create(name="probe", path=root, bootstrap=False, profile="basic")
        # Inject agents allowlist into the .vault.json
        vj = json.loads((root / ".vault.json").read_text())
        vj["agents"] = ["alice", "bob"]
        (root / ".vault.json").write_text(json.dumps(vj, indent=2))

        # Re-load vault so it picks up the updated agents policy
        meta = VaultMeta.from_json("probe", vj, default_name="")
        v = Vault.load(meta)
        # Sanity: listed actor writes, unlisted denied
        assert v.write_allowed_for("alice") is True
        assert v.write_allowed_for("eve") is False

        # Eve attempts a write — must be denied, no file should exist.
        result = write_page(v, "evil", "should not exist", actor="eve", normalize=False)
        assert result.ok is False
        assert "not in vault's" in (result.error or "")
        assert not (root / "evil.md").exists(), (
            "denied write must NOT touch the filesystem"
        )

        # Alice writes — must succeed.
        result_ok = write_page(
            v, "ok-page", "alice's page", actor="alice", normalize=False
        )
        assert result_ok.ok is True
        assert (root / "ok-page.md").exists()


def test_write_page_denies_anonymous_when_policy_declared() -> None:
    """actor=None with policy declared → denied (default is "anonymous",
    which is not in the user-declared allowlist)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "content").mkdir()
        Vault.create(name="probe", path=root, bootstrap=False, profile="basic")
        vj = json.loads((root / ".vault.json").read_text())
        vj["agents"] = ["alice"]
        (root / ".vault.json").write_text(json.dumps(vj, indent=2))

        meta = VaultMeta.from_json("probe", vj, default_name="")
        v = Vault.load(meta)
        # anonymous is NOT in the allowlist → denied
        result = write_page(v, "anon", "x", actor=None, normalize=False)
        assert result.ok is False
        assert "anonymous" in (result.error or "")


# ────────────────────────── wiring sanity ──────────────────────────


def test_contract_guards_writes_for_opt_in_vaults_only() -> None:
    """Sanity: an opt-in vault's write gate is the SOURCE OF TRUTH for
    contracts.write_page. If this ever drifts (e.g. someone removes the
    guard from contracts), the test below will still pass — but the
    primary enforcement test (`test_write_page_denies_unlisted_actor_*`)
    is what catches a real regression."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "content").mkdir()
        Vault.create(name="probe", path=root, bootstrap=False, profile="basic")
        vj = json.loads((root / ".vault.json").read_text())
        vj["agents"] = ["alice"]
        (root / ".vault.json").write_text(json.dumps(vj, indent=2))
        meta = VaultMeta.from_json("probe", vj, default_name="")
        v = Vault.load(meta)
        # No agents path = permissive; should NOT be locked out just
        # because we happened to mention `agents` in this test.
        bare_meta = VaultMeta(name="bare", path=Path("/tmp/bare"))
        bare_v = Vault(meta=bare_meta, root=bare_meta.path)
        assert bare_v.meta.agents == ()
        assert bare_v.write_allowed_for("eve") is True
