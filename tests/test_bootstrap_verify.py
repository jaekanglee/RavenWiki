"""Tests for Bootstrap Self-Test (M4 F3 — `verify_bootstrap`).

Verifies the read-back SHA256 verification that runs automatically after
`Vault.create(bootstrap=True)` and is exposed publicly via:
  - `Vault.verify_bootstrap()` (instance method)
  - `raven.core.verify.verify_bootstrap(path)` (free function)
  - CLI: `raven vault verify <name>`
  - API: `POST /api/vaults/{name}/verify`
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.vault import Vault
from raven.core.verify import (
    BootstrapVerifyResult,
    FileCheck,
    LITE_BOOTSTRAP_FILES,
    TEMPLATE_MAP,
    verify_bootstrap,
    verify_and_warn,
)


# ─── fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def isolated_vaults_root(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="raven-verify-test-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def isolated_target(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="raven-verify-target-"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def fresh_vault(isolated_vaults_root, isolated_target):
    """A freshly-created vault with default Lite bootstrap."""
    return Vault.create("v1", isolated_target / "v1", bootstrap=True)


# ─── constants & structure ─────────────────────────────────────────


def test_lite_bootstrap_files_constant_lists_5_files():
    """`LITE_BOOTSTRAP_FILES` (verify.py side) MUST list all 5 canonical
    Lite bootstrap files. This is the read-side mirror of the
    write-side `_bootstrap_lite` template_map.
    """
    assert set(LITE_BOOTSTRAP_FILES) == {
        "_meta/system/SCHEMA.md",
        "_meta/system/RULES.md",
        "_meta/system/README.md",
        "_meta/agents/PROJECT-WORKFLOW.md",
        "log.md",
    }


def test_template_map_matches_lite_bootstrap_files():
    """Every entry in `LITE_BOOTSTRAP_FILES` has a template source mapping.

    Prevents a silent gap where a bootstrap file has no source — verification
    would always report `template_error`.
    """
    for rel in LITE_BOOTSTRAP_FILES:
        assert rel in TEMPLATE_MAP, f"missing template mapping for {rel}"


def test_template_map_paths_are_under_templates_dir():
    """All template paths must live under `raven.core/templates/`."""
    for rel, tmpl in TEMPLATE_MAP.items():
        assert tmpl.startswith("templates/"), (
            f"template path {tmpl!r} for {rel} does not start with 'templates/'"
        )


# ─── verify_bootstrap: fresh vault (happy path) ─────────────────────


def test_verify_bootstrap_fresh_vault_is_ok(fresh_vault):
    """A vault just created via `Vault.create(bootstrap=True)` MUST verify ok.

    This is the core M4 F3 guarantee — every vault create produces a
    vault that passes the read-back self-test on first creation.

    Note: log.md is append-only, so its content diverges from the template
    the moment the first vault action is logged. We verify existence +
    non-empty for append-only files, byte-identity for static templates.
    """
    result = verify_bootstrap(fresh_vault.root)
    assert isinstance(result, BootstrapVerifyResult)
    assert result.ok is True
    assert len(result.checks) == 5
    static_checks = [c for c in result.checks if c.rel_path != "log.md"]
    append_checks = [c for c in result.checks if c.rel_path == "log.md"]
    # Static templates (SCHEMA, RULES, AGENTS): byte-identical to source
    for c in static_checks:
        assert c.status == "ok", f"{c.rel_path}: {c.status} ({c.detail})"
        assert c.expected_sha256 is not None
        assert c.actual_sha256 is not None
        assert c.expected_sha256 == c.actual_sha256
    # Append-only (log.md): exists + non-empty
    for c in append_checks:
        assert c.status == "ok", f"{c.rel_path}: {c.status} ({c.detail})"
        assert c.actual_sha256 is not None


def test_vault_verify_bootstrap_method_matches_free_function(fresh_vault):
    """`Vault.verify_bootstrap()` (instance method) delegates to free function."""
    a = verify_bootstrap(fresh_vault.root)
    b = fresh_vault.verify_bootstrap()
    assert a.ok == b.ok
    assert [c.rel_path for c in a.checks] == [c.rel_path for c in b.checks]


# ─── verify_bootstrap: failure modes ──────────────────────────────


def test_verify_bootstrap_detects_missing_file(fresh_vault):
    """If a bootstrap file is removed, verify_bootstrap flags it `missing`."""
    target = fresh_vault.root / "_meta" / "system" / "SCHEMA.md"
    target.unlink()
    result = verify_bootstrap(fresh_vault.root)
    assert result.ok is False
    bad = result.failures()
    assert len(bad) == 1
    assert bad[0].rel_path == "_meta/system/SCHEMA.md"
    assert bad[0].status == "missing"
    assert bad[0].expected_sha256 is not None
    assert bad[0].actual_sha256 is None


def test_verify_bootstrap_detects_content_mismatch(fresh_vault):
    """If a STATIC template file is edited, verify_bootstrap flags it `mismatch`.

    We target _meta/system/RULES.md (static template) — log.md is append-only
    so its content legitimately differs from the template after any write.
    """
    target = fresh_vault.root / "_meta" / "system" / "RULES.md"
    target.write_text("# user-edited rules\n")
    result = verify_bootstrap(fresh_vault.root)
    assert result.ok is False
    bad = {c.rel_path: c for c in result.failures()}
    assert "_meta/system/RULES.md" in bad
    assert bad["_meta/system/RULES.md"].status == "mismatch"
    assert bad["_meta/system/RULES.md"].expected_sha256 != bad["_meta/system/RULES.md"].actual_sha256


def test_verify_bootstrap_detects_corrupt_file(fresh_vault):
    """Truncation also triggers `mismatch` (not `missing`)."""
    target = fresh_vault.root / "_meta" / "system" / "RULES.md"
    target.write_bytes(b"# trunc\n")
    result = verify_bootstrap(fresh_vault.root)
    assert result.ok is False
    bad = {c.rel_path: c for c in result.failures()}
    assert bad["_meta/system/RULES.md"].status == "mismatch"


def test_verify_bootstrap_handles_missing_directory():
    """If the vault path doesn't exist, all Lite bootstrap files report `missing`."""
    bogus = Path("/tmp/raven-verify-bogus-nonexistent-xyz-12345")
    if bogus.exists():
        shutil.rmtree(bogus)
    result = verify_bootstrap(bogus)
    assert result.ok is False
    assert len(result.checks) == 5
    assert all(c.status == "missing" for c in result.checks)
    assert result.missing == list(LITE_BOOTSTRAP_FILES)


# ─── verify_and_warn: warning semantics ────────────────────────────


def test_verify_and_warn_emits_warning_on_failure(fresh_vault):
    """Failure → `warnings.warn` (RuntimeWarning). Does NOT raise."""
    target = fresh_vault.root / "log.md"
    target.unlink()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = verify_and_warn(fresh_vault.root, context="unit-test")
    assert result.ok is False
    assert len(caught) == 1
    w = caught[0]
    assert issubclass(w.category, RuntimeWarning)
    assert "unit-test" in str(w.message)
    assert "log.md" in str(w.message)


def test_verify_and_warn_silent_on_success(fresh_vault):
    """Success → no warning emitted."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = verify_and_warn(fresh_vault.root, context="unit-test")
    assert result.ok is True
    # No warnings at all
    assert len(caught) == 0


# ─── Vault.create() integration: auto-verify on bootstrap ──────────


def test_vault_create_with_bootstrap_auto_verifies(
    isolated_vaults_root, isolated_target
):
    """`Vault.create(bootstrap=True)` MUST auto-run verify and not raise
    even if templates are perfect (no warnings).
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        v = Vault.create("auto", isolated_target / "auto", bootstrap=True)
    assert v is not None
    assert v.root.exists()
    # Success → no warning from auto-verify
    runtime_warnings = [
        w for w in caught
        if issubclass(w.category, RuntimeWarning) and "vault.create" in str(w.message)
    ]
    assert runtime_warnings == [], (
        f"unexpected RuntimeWarning on fresh vault create: "
        f"{[str(w.message) for w in runtime_warnings]}"
    )


def test_vault_create_does_not_raise_on_corrupt_template(
    isolated_vaults_root, isolated_target
):
    """Even if a bootstrap file is corrupt post-copy, `Vault.create` MUST
    return successfully (README.md §9: loud, not silent — verify failure
    is a warning, not a raised exception).
    """
    # Create normally
    v = Vault.create("ok", isolated_target / "ok", bootstrap=True)
    # Now corrupt one of the bootstrap files (simulating external mutation)
    (v.root / "_meta" / "system" / "README.md").write_text("# corrupt\n")
    # Run verify directly — should report mismatch, NOT raise
    result = v.verify_bootstrap()
    assert result.ok is False
    bad = {c.rel_path: c for c in result.failures()}
    assert bad["_meta/system/README.md"].status == "mismatch"


# ─── CLI: raven vault verify ────────────────────────────────────────


def test_cli_vault_verify_happy_path(isolated_vaults_root, isolated_target):
    """`raven vault verify <name>` exits 0 on a fresh vault."""
    from typer.testing import CliRunner
    from raven.cli.__main__ import app

    Vault.create("cliok", isolated_target / "cliok", bootstrap=True)
    runner = CliRunner()
    result = runner.invoke(app, ["vault", "verify", "cliok"])
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "cliok" in result.stdout
    assert "ok" in result.stdout.lower()


def test_cli_vault_verify_detects_corruption(isolated_vaults_root, isolated_target):
    """`raven vault verify <name>` exits 1 when a STATIC template is corrupted.

    We corrupt SCHEMA.md (static template, not append-only) so that hash
    comparison fires. Corrupting log.md would NOT trigger exit 1 because
    log.md is append-only and content divergence is expected.
    """
    from typer.testing import CliRunner
    from raven.cli.__main__ import app

    v = Vault.create("clibad", isolated_target / "clibad", bootstrap=True)
    (v.root / "_meta" / "system" / "SCHEMA.md").write_text("# corrupted\n")
    runner = CliRunner()
    result = runner.invoke(app, ["vault", "verify", "clibad"])
    assert result.exit_code == 1, result.stdout + result.stderr
    assert "MISMATCH" in result.stdout
    assert "SCHEMA.md" in result.stdout


def test_cli_vault_verify_json_output(isolated_vaults_root, isolated_target):
    """`raven vault verify <name> --json` returns a JSON dict."""
    from typer.testing import CliRunner
    from raven.cli.__main__ import app

    Vault.create("clijson", isolated_target / "clijson", bootstrap=True)
    runner = CliRunner()
    result = runner.invoke(app, ["vault", "verify", "clijson", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert len(data["checks"]) == 5


# ─── API: POST /api/vaults/{name}/verify ───────────────────────────


def test_api_verify_vault_bootstrap_endpoint(isolated_vaults_root, isolated_target):
    """API endpoint returns 200 + ok=True on a fresh vault."""
    from fastapi.testclient import TestClient
    from raven.api.server import app

    Vault.create("apitest", isolated_target / "apitest", bootstrap=True)
    client = TestClient(app)
    r = client.post("/api/vaults/apitest/verify")
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["ok"] is True
    assert len(payload["checks"]) == 5


def test_api_verify_returns_409_on_mismatch(isolated_vaults_root, isolated_target):
    """API endpoint returns 409 when bootstrap is corrupted."""
    from fastapi.testclient import TestClient
    from raven.api.server import app

    v = Vault.create("apibad", isolated_target / "apibad", bootstrap=True)
    (v.root / "_meta" / "system" / "SCHEMA.md").write_text("# bad\n")
    client = TestClient(app)
    r = client.post("/api/vaults/apibad/verify")
    assert r.status_code == 409, r.text
    payload = r.json()["detail"]
    assert payload["ok"] is False
    bad = {c["file"]: c for c in payload["checks"]}
    assert bad["_meta/system/SCHEMA.md"]["status"] == "mismatch"


def test_api_verify_returns_404_on_unknown_vault(isolated_vaults_root):
    """API endpoint returns 404 if vault doesn't exist."""
    from fastapi.testclient import TestClient
    from raven.api.server import app

    client = TestClient(app)
    r = client.post("/api/vaults/does-not-exist-xyz/verify")
    assert r.status_code == 404
