"""MCP read가 precondition 토큰을 내려준다 — Theme A 마감 (momus 라운드 3 확인 지점).

`wiki_update(precondition=...)`를 추가해도 에이전트가 토큰을 **얻을 경로**가 없으면
그 파라미터는 실사용 불가다. 토큰은 wiki.db가 아니라 **on-disk 파일 상태**에서
나와야 한다 — DB는 파생 캐시라 stale일 수 있고, precondition은 실제 파일이 밀렸는지를
물어야 하기 때문이다.
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
from raven.mcp import db as mcp_db
from raven.mcp.tools import VaultContext, WRITE
from raven.mcp.tools.write import wiki_update

BASE_BODY = "base body paragraph long enough to stay comparable across writes"
EDIT_BODY = "edit body paragraph long enough to stay comparable across writes"


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-mcpread-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-mcpread-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("mcpread", target_root / "mcpread")
    write_page(v, "content/hello", BASE_BODY, title="Hello", type="concept", normalize=False)
    from raven.core import db as core_db

    core_db.build_db(v, run_lint=False)
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_mcp_get_page_exposes_precondition(vault):
    """읽기 표면이 토큰을 주지 않으면 에이전트는 검사를 시작할 수 없다."""
    page = mcp_db.get_page(slug="content/hello", vault=vault.root)
    assert page is not None
    assert page["precondition"] == page_precondition(vault, "content/hello", normalize=False)


def test_mcp_read_token_is_accepted_by_write(vault):
    """읽어서 받은 토큰이 그대로 write에 통해야 한다 (round-trip)."""
    token = mcp_db.get_page(slug="content/hello", vault=vault.root)["precondition"]
    result = wiki_update(
        slug="content/hello",
        content=EDIT_BODY,
        ctx=VaultContext(vault=vault.root, mode=WRITE),
        actor="agent-a",
        precondition=token,
    )
    assert result.get("ok") is True, result
    assert EDIT_BODY in (vault.root / "content" / "hello.md").read_text(encoding="utf-8")


def test_mcp_read_token_goes_stale_after_another_write(vault):
    """읽은 뒤 남이 저장하면 그 토큰은 거부된다 — 토큰이 파일 상태를 따라간다는 증거."""
    token = mcp_db.get_page(slug="content/hello", vault=vault.root)["precondition"]
    write_page(
        vault,
        "content/hello",
        BASE_BODY + " plus another writer's appended sentence",
        title="Hello",
        normalize=False,
    )

    result = wiki_update(
        slug="content/hello",
        content=EDIT_BODY,
        ctx=VaultContext(vault=vault.root, mode=WRITE),
        actor="agent-a",
        precondition=token,
    )
    assert result.get("ok") is False, result
    assert result.get("error") == "stale_precondition"


def test_mcp_precondition_tracks_file_not_stale_db(vault):
    """DB를 다시 빌드하지 않아도 토큰은 파일 변경을 반영해야 한다 (DB는 파생 캐시)."""
    before = mcp_db.get_page(slug="content/hello", vault=vault.root)["precondition"]
    write_page(
        vault,
        "content/hello",
        BASE_BODY + " changed on disk without rebuilding the index",
        title="Hello",
        normalize=False,
    )
    after = mcp_db.get_page(slug="content/hello", vault=vault.root)["precondition"]
    assert before != after
