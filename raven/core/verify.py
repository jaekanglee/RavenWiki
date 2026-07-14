"""verify — Bootstrap Self-Test (F3, M4).

After `Vault.create()` copies the Lite bootstrap templates into a new vault,
this module verifies that:

  1. Each of the 3 Lite bootstrap files exists in the vault.
  2. The 2 *template* files (SCHEMA.md, PROJECT-WORKFLOW.md) match the
     source templates byte-for-byte (SHA256 hash).
  3. `log.md` exists and is non-empty (it's an append-only working file,
     not a static template — so hash comparison would always fail once
     the vault's first `create` log entry is appended).

This is the M4 Trust & Tier safety answer to the v0.5.5 silent-write hotfix
(README.md §9): silent file leaks / dropouts are the same risk class as
silent write failures, so we add a deterministic read-back check.

Failure mode policy (mirrors the silent-write pattern in `vault.create`):
  - Verification failure → log warning, do NOT raise.
  - `Vault.create()` returns success; only a `warnings.warn` is emitted.
  - `verify_bootstrap(path)` itself is a pure read-only check, callable
    from CLI / API / tests for explicit verification.

Allowed dependencies: stdlib only (hashlib, pathlib, dataclasses, warnings).
"""
from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Optional


# Lite bootstrap files — 검증 대상.
# This list MUST mirror the `template_map` in `vault._bootstrap_lite` (the
# canonical write side). We keep it duplicated here (read-only) instead of
# importing, so `verify` is independent of any side-effects in `vault.py`.
LITE_BOOTSTRAP_FILES: tuple[str, ...] = (
    "_meta/agents/SCHEMA.md",
    "_meta/agents/RAVEN-CONTRACT.md",
    "log.md",
)

# Template source paths inside `raven.core` package.
TEMPLATE_MAP: dict[str, str] = {
    "_meta/agents/SCHEMA.md": "templates/agent/SCHEMA.md",
    "_meta/agents/RAVEN-CONTRACT.md": "templates/agent/RAVEN-CONTRACT.md",
    "log.md": "templates/log.md",
}

# log.md is append-only — its content evolves with every vault action.
# We verify its *existence + non-empty*, not byte equality. All other
# bootstrap files are static templates and MUST be byte-identical.
APPEND_ONLY_FILES: frozenset[str] = frozenset({"log.md"})


@dataclass
class FileCheck:
    """Per-file verification result.

    Status values:
      - "ok"            — file exists and matches expectations.
      - "missing"       — file not found on disk.
      - "mismatch"      — file content differs from template (hash mismatch).
      - "empty"         — file exists but is empty (only used for append-only).
      - "template_error" — could not read template resource (programmer error).
    """

    rel_path: str          # vault-relative path, e.g. "_meta/agents/SCHEMA.md"
    status: str            # "ok" | "missing" | "mismatch" | "empty" | "template_error"
    expected_sha256: Optional[str] = None
    actual_sha256: Optional[str] = None
    detail: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "file": self.rel_path,
            "status": self.status,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
            "detail": self.detail,
        }


@dataclass
class BootstrapVerifyResult:
    """Aggregate verification result for a vault's Lite bootstrap files.

    `ok` is True only when every file in `LITE_BOOTSTRAP_FILES` has
    `status == "ok"`. Any `missing` / `mismatch` / `empty` /
    `template_error` flips it to False.
    """

    vault_path: str
    checks: list[FileCheck] = field(default_factory=list)
    ok: bool = True

    @property
    def missing(self) -> list[str]:
        return [c.rel_path for c in self.checks if c.status == "missing"]

    @property
    def mismatches(self) -> list[str]:
        return [c.rel_path for c in self.checks if c.status == "mismatch"]

    @property
    def empty(self) -> list[str]:
        return [c.rel_path for c in self.checks if c.status == "empty"]

    @property
    def template_errors(self) -> list[str]:
        return [c.rel_path for c in self.checks if c.status == "template_error"]

    def summary(self) -> str:
        n = len(self.checks)
        n_ok = sum(1 for c in self.checks if c.status == "ok")
        return f"{n_ok}/{n} ok" + ("" if self.ok else f" — failures: {self.failures()}")

    def failures(self) -> list[FileCheck]:
        return [c for c in self.checks if c.status != "ok"]

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "vault_path": self.vault_path,
            "summary": self.summary(),
            "checks": [c.to_dict() for c in self.checks],
        }


def _sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_of_path(p: Path) -> str:
    return _sha256_of_bytes(p.read_bytes())


def _template_bytes(tmpl_rel_path: str) -> bytes:
    """Read template bytes from `raven.core` package resources.

    Raises FileNotFoundError if the template resource is missing — this
    indicates a packaging error, NOT a vault problem.
    """
    src = resources.files("raven.core").joinpath(tmpl_rel_path)
    return src.read_bytes()


def verify_bootstrap(path: Path | str) -> BootstrapVerifyResult:
    """Verify the Lite bootstrap files in `path` match the source templates.

    This is a pure read-only check. It never raises on vault-side problems
    (missing file, hash mismatch, empty append-only file) — those become
    `FileCheck(status=...)` entries. It only raises on programmer errors
    (template resource missing, type errors).

    Verification rules per file:
      - Static templates (SCHEMA, PROJECT-WORKFLOW): must exist AND be
        byte-identical to the source template (SHA256 match).
      - Append-only working file (log.md): must exist AND be non-empty.
        (Its content will diverge from the template as soon as the first
        vault action is logged — this is expected, not a failure.)

    Args:
        path: vault root directory (must exist; we don't create anything).

    Returns:
        BootstrapVerifyResult with per-file status + overall `ok` flag.
    """
    path = Path(path).expanduser().resolve()
    result = BootstrapVerifyResult(vault_path=str(path))

    if not path.is_dir():
        # Not a directory → all files "missing"
        for rel in LITE_BOOTSTRAP_FILES:
            result.checks.append(FileCheck(
                rel_path=rel,
                status="missing",
                detail=f"vault path is not a directory: {path}",
            ))
        result.ok = False
        return result

    for rel in LITE_BOOTSTRAP_FILES:
        target = path / rel
        tmpl_rel = TEMPLATE_MAP.get(rel)
        if tmpl_rel is None:
            # Should never happen — list/code mismatch is a bug.
            result.checks.append(FileCheck(
                rel_path=rel,
                status="template_error",
                detail=f"no template mapping for {rel}",
            ))
            result.ok = False
            continue

        # Read template (always — needed for both static + append-only)
        try:
            expected_bytes = _template_bytes(tmpl_rel)
        except Exception as e:
            result.checks.append(FileCheck(
                rel_path=rel,
                status="template_error",
                detail=f"could not read template {tmpl_rel}: {type(e).__name__}: {e}",
            ))
            result.ok = False
            continue
        expected_hash = _sha256_of_bytes(expected_bytes)

        if not target.is_file():
            result.checks.append(FileCheck(
                rel_path=rel,
                status="missing",
                expected_sha256=expected_hash if rel not in APPEND_ONLY_FILES else None,
                actual_sha256=None,
                detail=f"file not found at {target}",
            ))
            result.ok = False
            continue

        # Read actual
        try:
            actual_bytes = target.read_bytes()
        except Exception as e:
            result.checks.append(FileCheck(
                rel_path=rel,
                status="template_error",
                expected_sha256=expected_hash if rel not in APPEND_ONLY_FILES else None,
                detail=f"could not read vault file: {type(e).__name__}: {e}",
            ))
            result.ok = False
            continue
        actual_hash = _sha256_of_bytes(actual_bytes)

        if rel in APPEND_ONLY_FILES:
            # Append-only working file: existence + non-empty is "ok".
            if len(actual_bytes) == 0:
                result.checks.append(FileCheck(
                    rel_path=rel,
                    status="empty",
                    actual_sha256=actual_hash,
                    detail=f"append-only file is empty (should have at least the template header)",
                ))
                result.ok = False
            else:
                result.checks.append(FileCheck(
                    rel_path=rel,
                    status="ok",
                    actual_sha256=actual_hash,
                    detail="append-only file (content may diverge from template — that's expected)",
                ))
            continue

        # Static template: must be byte-identical.
        if actual_hash != expected_hash:
            result.checks.append(FileCheck(
                rel_path=rel,
                status="mismatch",
                expected_sha256=expected_hash,
                actual_sha256=actual_hash,
                detail="hash differs from template (file may have been edited or corrupted)",
            ))
            result.ok = False
        else:
            result.checks.append(FileCheck(
                rel_path=rel,
                status="ok",
                expected_sha256=expected_hash,
                actual_sha256=actual_hash,
            ))

    return result


def verify_and_warn(path: Path | str, *, context: str = "vault.create") -> BootstrapVerifyResult:
    """Convenience wrapper used by `Vault.create()`.

    Runs `verify_bootstrap(path)` and emits a `warnings.warn` on failure,
    matching README.md §9 silent-failure policy (loud, not silent).

    Returns the BootstrapVerifyResult regardless of outcome — caller decides.
    """
    result = verify_bootstrap(path)
    if not result.ok:
        # Loud, not silent. Caller (CLI) will surface this.
        bad = ", ".join(c.rel_path for c in result.failures())
        warnings.warn(
            f"[{context}] Bootstrap self-test FAILED for {path}: {bad}. "
            f"Vault create() succeeded but tier-2 templates may be corrupt. "
            f"Re-run `raven meta sync --lite` or recreate the vault.",
            RuntimeWarning,
            stacklevel=2,
        )
    return result
