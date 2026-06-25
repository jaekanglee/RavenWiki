"""Tests for wikisys.core.slug — slug validation + prefix normalization."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ensure repo root on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wikisys.core.slug import SlugError, normalize_prefix, validate


VAULT = Path("/tmp/test-vault-slug").resolve()


# ─── validate: success cases ─────────────────────────────────


def test_validate_normal_path():
    p = validate("content/foo", vault_root=VAULT)
    assert p == VAULT / "content" / "foo"
    assert p.is_absolute()


def test_validate_nested_path():
    p = validate("content/a/b/c", vault_root=VAULT)
    assert p == VAULT / "content" / "a" / "b" / "c"


def test_validate_meta_path():
    p = validate("_meta/welcome", vault_root=VAULT)
    assert p == VAULT / "_meta" / "welcome"


# ─── validate: rejection cases ──────────────────────────────


def test_validate_rejects_empty():
    with pytest.raises(SlugError, match="empty"):
        validate("", vault_root=VAULT)


def test_validate_rejects_whitespace():
    with pytest.raises(SlugError, match="empty"):
        validate("   ", vault_root=VAULT)


def test_validate_rejects_absolute_root():
    with pytest.raises(SlugError, match="absolute"):
        validate("/etc/passwd-test", vault_root=VAULT)


def test_validate_rejects_tilde_expansion():
    with pytest.raises(SlugError, match="~"):
        validate("~/.ssh-test", vault_root=VAULT)


def test_validate_rejects_parent_traversal():
    with pytest.raises(SlugError, match=r"\.\."):
        validate("../escape", vault_root=VAULT)


def test_validate_rejects_multi_parent_traversal():
    with pytest.raises(SlugError, match=r"\.\."):
        validate("../../../tmp/pwn", vault_root=VAULT)


def test_validate_rejects_mid_path_traversal():
    with pytest.raises(SlugError, match=r"\.\."):
        validate("content/../../escape", vault_root=VAULT)


def test_validate_rejects_nul_byte():
    with pytest.raises(SlugError, match="NUL"):
        validate("content/foo\0bar", vault_root=VAULT)


def test_validate_rejects_colon():
    with pytest.raises(SlugError, match=":"):
        validate("content/foo:bar", vault_root=VAULT)


def test_validate_rejects_double_slash():
    with pytest.raises(SlugError, match="empty"):
        validate("content//foo", vault_root=VAULT)


def test_validate_rejects_dot_segment():
    with pytest.raises(SlugError, match="empty"):
        validate("./content/foo", vault_root=VAULT)


# ─── normalize_prefix ───────────────────────────────────────


def test_normalize_short_name_gets_prefix():
    assert normalize_prefix("foo") == "content/foo"


def test_normalize_explicit_content_passthrough():
    assert normalize_prefix("content/foo") == "content/foo"


def test_normalize_explicit_meta_passthrough():
    assert normalize_prefix("_meta/welcome") == "_meta/welcome"


def test_normalize_nested_passthrough():
    assert normalize_prefix("content/a/b") == "content/a/b"


def test_normalize_strips_whitespace():
    assert normalize_prefix("  foo  ") == "content/foo"


def test_normalize_empty_stays_empty():
    assert normalize_prefix("") == ""
