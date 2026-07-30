"""lost update 방지 — Theme A.1 (계획: docs/superpowers/plans/2026-07-29-raven-concept-reinforcement.md §2).

`FileLock`은 write 순간만 직렬화하므로, read-modify-write 사이에 남이 저장하면
그 편집이 조용히 사라진다. `write_page(precondition=...)`가 이를 거부한다.

토큰은 `(st_mtime_ns, size)` 파생 문자열이다. 같은 mtime tick 안에서 크기까지
같은 두 write는 원리상 구분되지 않으므로, 아래 테스트는 sleep 대신 **길이가
다른** 중간 write로 stale 상태를 결정론적으로 만든다.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from raven.core.contracts import page_precondition, write_page
from raven.core.registry import VaultMeta
from raven.core.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    (tmp_path / "content").mkdir()
    meta = VaultMeta(name="test", path=tmp_path, mode="personal", owner="user")
    return Vault.load(meta)


def stat_token(vault: Vault, rel: str) -> str:
    st = os.stat(vault.root / f"{rel}.md")
    return f"{st.st_mtime_ns}-{st.st_size}"


def test_write_without_precondition_still_overwrites(vault: Vault) -> None:
    """하위 호환: 토큰을 주지 않으면 pre-v0.7.178처럼 그냥 덮어쓴다."""
    assert write_page(vault, "hello", "v1", title="Hello").ok is True
    r2 = write_page(vault, "hello", "v2-longer-body", title="Hello")
    assert r2.ok is True
    assert r2.error is None
    assert "v2-longer-body" in (vault.root / "content" / "hello.md").read_text()


def test_helper_token_matches_stat_derived_token(vault: Vault) -> None:
    """공개 헬퍼가 실제 (mtime_ns, size)와 같은 값을 내야 검사가 의미를 가진다."""
    write_page(vault, "hello", "base", title="Hello")
    assert page_precondition(vault, "content/hello") == stat_token(vault, "content/hello")


def test_stale_precondition_is_rejected_and_first_edit_survives(vault: Vault) -> None:
    """A가 읽은 뒤 B가 저장하면, A의 저장은 거부되고 B의 내용이 남는다."""
    write_page(vault, "hello", "base", title="Hello")
    token_a = stat_token(vault, "content/hello")

    r_b = write_page(vault, "hello", "B wrote a distinctly longer body", title="Hello")
    assert r_b.ok is True

    r_a = write_page(vault, "hello", "A overwrote", title="Hello", precondition=token_a)
    assert r_a.ok is False
    assert r_a.error == "stale_precondition"

    text = (vault.root / "content" / "hello.md").read_text()
    assert "B wrote a distinctly longer body" in text
    assert "A overwrote" not in text


def test_fresh_precondition_is_accepted(vault: Vault) -> None:
    """토큰이 최신이면 정상 저장된다 — precondition이 정상 write를 막지 않는다."""
    write_page(vault, "hello", "base", title="Hello")
    result = write_page(
        vault,
        "hello",
        "updated body",
        title="Hello",
        precondition=stat_token(vault, "content/hello"),
    )
    assert result.ok is True
    assert "updated body" in (vault.root / "content" / "hello.md").read_text()


def test_precondition_token_changes_after_write(vault: Vault) -> None:
    """토큰이 write 후에도 같다면 검사 자체가 무의미하다."""
    write_page(vault, "hello", "base", title="Hello")
    before = page_precondition(vault, "content/hello")
    write_page(vault, "hello", "a clearly different length body", title="Hello")
    assert page_precondition(vault, "content/hello") != before


def test_absent_page_has_empty_token_and_create_succeeds(vault: Vault) -> None:
    """없는 페이지의 토큰은 빈 문자열이고, 그 토큰으로 create가 가능하다."""
    assert page_precondition(vault, "content/brand-new") == ""
    assert write_page(vault, "brand-new", "body", title="New", precondition="").ok is True


def test_precondition_expecting_absence_rejects_existing_page(vault: Vault) -> None:
    """없어야 한다고 믿고 create했는데 이미 생겼으면 거부한다."""
    write_page(vault, "hello", "someone created it first", title="Hello")
    result = write_page(vault, "hello", "my create", title="Hello", precondition="")
    assert result.ok is False
    assert result.error == "stale_precondition"
    assert "someone created it first" in (vault.root / "content" / "hello.md").read_text()
