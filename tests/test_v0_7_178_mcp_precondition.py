"""MCP write도 precondition을 받는다 — Theme A 후속 (momus 리뷰 blocker 1).

`write_page`에 검사를 넣어도 호출자가 토큰을 전달하지 않으면 그 표면은 여전히
무방비다. MCP의 read-modify-write 두 작업은 마지막 기록이 첫 기록을 조용히
덮어쓸 수 있었다.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.contracts import page_precondition, write_page
from raven.core.vault import Vault
from raven.mcp.tools.write import wiki_update
from raven.mcp.tools import VaultContext


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-mcppre-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-mcppre-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("mcp-pre", target_root / "mcp-pre")
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def ctx_for(vault: Vault) -> VaultContext:
    return VaultContext(vault=vault.root, mode="write")


BASE_BODY = "base body paragraph kept long enough for the large-rewrite guard"
EDIT_BODY = "edit body paragraph kept long enough for the large-rewrite guard"


def test_mcp_update_without_precondition_keeps_legacy_behavior(vault):
    """토큰을 주지 않으면 기존 MCP 동작 그대로 (하위 호환)."""
    write_page(vault, "content/hello", BASE_BODY, title="Hello", normalize=False)
    result = wiki_update(
        slug="content/hello",
        content=EDIT_BODY,
        ctx=ctx_for(vault),
        actor="agent-a",
    )
    assert result.get("ok") is True, result
    assert EDIT_BODY in (vault.root / "content" / "hello.md").read_text()


def test_mcp_update_with_stale_precondition_is_rejected(vault):
    """에이전트가 읽은 뒤 남이 저장했으면 에이전트의 write는 거부된다."""
    write_page(vault, "content/hello", BASE_BODY, title="Hello", normalize=False)
    token = page_precondition(vault, "content/hello", normalize=False)

    write_page(
        vault,
        "content/hello",
        BASE_BODY + " plus someone else's appended sentence",
        title="Hello",
        normalize=False,
    )

    result = wiki_update(
        slug="content/hello",
        content=EDIT_BODY,
        ctx=ctx_for(vault),
        actor="agent-a",
        precondition=token,
    )
    assert result.get("ok") is False
    assert result.get("error") == "stale_precondition"

    text = (vault.root / "content" / "hello.md").read_text()
    assert "plus someone else's appended sentence" in text
    assert EDIT_BODY not in text


def test_mcp_update_with_fresh_precondition_succeeds(vault):
    """최신 토큰이면 정상 저장 — 검사가 정상 write를 막지 않는다."""
    write_page(vault, "content/hello", BASE_BODY, title="Hello", normalize=False)
    result = wiki_update(
        slug="content/hello",
        content=EDIT_BODY,
        ctx=ctx_for(vault),
        actor="agent-a",
        precondition=page_precondition(vault, "content/hello", normalize=False),
    )
    assert result.get("ok") is True, result
    assert EDIT_BODY in (vault.root / "content" / "hello.md").read_text()
