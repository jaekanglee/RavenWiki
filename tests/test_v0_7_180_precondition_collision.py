"""precondition 토큰의 충돌 봉합 — v0.7.178이 남긴 한계 마감.

v0.7.178의 토큰은 `(st_mtime_ns, st_size)`였다. 그래서 **같은 mtime tick 안에서
바이트 수까지 같은** 개입 write는 토큰을 바꾸지 못하고, 검사를 통과해 그 편집을
조용히 덮어썼다. v0.7.178 changelog가 이를 "optimistic check, 절대적 방지 아님"으로
자백해 두었고 이 파일이 그 구멍을 닫는다.

충돌은 실파일시스템에서 우연히 만들기 어렵다. 그래서 개입 write를 같은 바이트 수로
쓰고 `os.utime(ns=...)`로 mtime을 원래 값으로 되돌려 **충돌 조건을 결정론적으로**
재현한다 — 타이밍 운에 기대지 않는다.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.contracts import page_precondition, precondition_for_path, write_page
from raven.core.vault import Vault

BODY = "base body paragraph long enough to keep byte counts comparable"


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-collide-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-collide-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("collide", target_root / "collide")
    write_page(v, "content/hello", BODY, title="Hello", type="concept", normalize=False)
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def page_file(vault: Vault) -> Path:
    return vault.root / "content" / "hello.md"


def rewrite_colliding(fp: Path, replacement: str) -> None:
    """파일 상태(mtime_ns, size)는 그대로 두고 내용만 바꾼다.

    다른 작성자가 같은 tick 안에서 같은 바이트 수로 저장한 상황과 구별할 수 없는
    파일 상태를 만든다 — 이것이 v0.7.178 토큰이 놓치던 케이스다.
    """
    original = fp.read_text(encoding="utf-8")
    st = fp.stat()
    changed = original.replace(BODY, replacement)
    assert len(changed.encode()) == len(original.encode()), "충돌 재현은 같은 바이트 수여야 한다"
    fp.write_text(changed, encoding="utf-8")
    os.utime(fp, ns=(st.st_atime_ns, st.st_mtime_ns))
    after = fp.stat()
    assert (after.st_mtime_ns, after.st_size) == (st.st_mtime_ns, st.st_size)


COLLIDING = "peer body paragraph long enough to keep byte counts comparable"


class TestCollisionIsRejected:
    def test_same_tick_same_size_change_is_detected(self, vault):
        """v0.7.178에서는 이 write가 성공해 개입 편집을 삼켰다."""
        fp = page_file(vault)
        token = page_precondition(vault, "content/hello", normalize=False)

        rewrite_colliding(fp, COLLIDING)

        result = write_page(
            vault, "content/hello", "my stale edit", title="Hello",
            normalize=False, precondition=token,
        )

        assert result.ok is False, "stat만 보는 토큰은 이 충돌을 통과시킨다"
        assert result.error == "stale_precondition"
        assert COLLIDING in fp.read_text(encoding="utf-8"), "개입 편집이 보존돼야 한다"
        assert "my stale edit" not in fp.read_text(encoding="utf-8")

    def test_token_follows_content_not_just_stat(self, vault):
        fp = page_file(vault)
        before = precondition_for_path(fp)

        rewrite_colliding(fp, COLLIDING)

        assert precondition_for_path(fp) != before


class TestExistingContractPreserved:
    """v0.7.178이 세운 계약은 그대로여야 한다 — 회귀 가드."""

    def test_absent_page_token_is_empty(self, vault):
        assert page_precondition(vault, "content/nope", normalize=False) == ""

    def test_empty_token_asserts_absence(self, vault):
        assert write_page(
            vault, "content/brand-new", "body text here", title="New",
            normalize=False, precondition="",
        ).ok is True

    def test_empty_token_rejects_existing_page(self, vault):
        result = write_page(
            vault, "content/hello", "my create", title="Hello",
            normalize=False, precondition="",
        )
        assert result.error == "stale_precondition"

    def test_fresh_token_is_accepted(self, vault):
        result = write_page(
            vault, "content/hello", "fresh edit body", title="Hello",
            normalize=False,
            precondition=page_precondition(vault, "content/hello", normalize=False),
        )
        assert result.ok is True

    def test_none_token_skips_the_check(self, vault):
        rewrite_colliding(page_file(vault), COLLIDING)
        assert write_page(
            vault, "content/hello", "unchecked overwrite", title="Hello", normalize=False
        ).ok is True

    def test_token_changes_after_a_normal_write(self, vault):
        before = page_precondition(vault, "content/hello", normalize=False)
        write_page(vault, "content/hello", "second body", title="Hello", normalize=False)
        assert page_precondition(vault, "content/hello", normalize=False) != before


def test_token_is_derived_from_file_bytes(vault):
    """토큰이 파일 바이트에서 나오는지 독립적으로 확인 (구현 공식 재유도 ❌)."""
    fp = page_file(vault)
    token = precondition_for_path(fp)
    digest = hashlib.sha256(fp.read_bytes()).hexdigest()

    assert digest[:32] in token, "같은 바이트에서 같은 토큰이 나와야 한다"

    copy = fp.with_name("copy.md")
    copy.write_bytes(fp.read_bytes())
    assert precondition_for_path(copy) == token, "내용이 같으면 경로가 달라도 같은 토큰"
