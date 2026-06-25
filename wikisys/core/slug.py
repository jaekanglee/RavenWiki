"""slug — vault-relative path safety.

Public surface:
    validate(slug, *, vault_root) -> Path
        Return absolute, resolved Path inside vault_root if safe.
        Raise ValueError on any safety violation.

    normalize_prefix(slug) -> str
        If slug has no '/', prepend 'content/'. Otherwise return unchanged.
        Used by `wikisys page new <slug>`.

Rejection rules:
    - empty / whitespace-only
    - absolute (starts with '/' or '~')
    - contains '..' as a path segment (resolved escape)
    - contains NUL byte ('\\0')
    - contains ':' (Windows drive letter, even on macOS — defensive)
    - resolved path not within vault_root after symlink/.. resolution
"""
from __future__ import annotations

from pathlib import Path


class SlugError(ValueError):
    """Raised when a slug is unsafe to use as a vault-relative path."""


def validate(slug: str, *, vault_root: Path) -> Path:
    """Validate `slug` as a vault-relative path; return resolved absolute Path.

    Args:
        slug: vault-relative path WITHOUT '.md' suffix. e.g. 'content/foo'.
        vault_root: absolute Path to the vault root.

    Returns:
        Absolute, resolved Path guaranteed to be inside vault_root.

    Raises:
        SlugError: if the slug is empty, absolute, escapes via '..', contains
                   NUL/colon, or resolves outside vault_root.
    """
    if not isinstance(slug, str):
        raise SlugError(f"slug must be str, got {type(slug).__name__}")
    s = slug.strip()
    if not s:
        raise SlugError("slug is empty")
    if "\0" in s:
        raise SlugError("slug contains NUL byte")
    if s.startswith("/"):
        raise SlugError("slug is absolute (starts with '/')")
    if s.startswith("~"):
        raise SlugError("slug starts with '~' (would expand user home)")
    if ":" in s:
        # Windows drive letter or URL-ish; we don't allow it on any OS
        raise SlugError("slug contains ':' (Windows drive / URL)")
    # '..' as path segment check — split on '/' and '.' must not appear alone
    parts = s.split("/")
    for part in parts:
        if part in ("", "."):
            # empty segments = 'a//b' or './a' — both suspicious
            raise SlugError(f"slug contains empty/'. ' segment: {slug!r}")
        if part == "..":
            raise SlugError(f"slug contains '..' segment: {slug!r}")

    vault_abs = vault_root.expanduser().resolve()
    # candidate path = vault_root / slug (no suffix added)
    candidate = (vault_abs / s).resolve()
    try:
        candidate.relative_to(vault_abs)
    except ValueError:
        raise SlugError(
            f"slug resolves outside vault root: {slug!r} → {candidate} (vault={vault_abs})"
        )
    return candidate


def normalize_prefix(slug: str) -> str:
    """If `slug` has no '/', prepend 'content/'.

    Used by `wikisys page new <slug>` so users can type short names.
    Explicit paths like '_meta/welcome' or 'content/foo' pass through.

    Note: this does NOT validate; call validate() afterwards for safety.
    """
    s = slug.strip()
    if not s:
        return s
    if "/" in s:
        return s
    return f"content/{s}"
