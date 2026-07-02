"""v0.7.55+: wiki_ingest user_command 플래그 (ADR-2026-07-02) 회귀 가드.

raw/ 폴더는 사람 1차 운영 영역. 에이전트가 자율로 wiki_ingest를 호출하면
source of truth가 변조될 수 있으므로 사람 운영자의 명시 명령이 있을 때만 허용.
"""
from __future__ import annotations

import sys
import tempfile
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# v0.7.55+: VaultContext는 raven.mcp.tools 모듈에 정의됨 (MCP 서버 컨텍스트).
from raven.mcp.tools import VaultContext
from raven.mcp.tools.write import wiki_ingest


@pytest.fixture
def temp_vault():
    """Fresh temp vault for ingest test."""
    with tempfile.TemporaryDirectory(prefix="raven-user-command-") as tmp:
        v = Path(tmp) / "test-vault"
        v.mkdir()
        (v / "raw").mkdir()
        # VaultContext.mode는 string ("read" | "write" | "admin")
        ctx = VaultContext(vault=v, mode="write")
        yield v, ctx


def test_wiki_ingest_without_user_command_is_rejected(temp_vault):
    """에이전트 자율 호출 (user_command=False 또는 생략) → 거부 (ok=False)."""
    v, ctx = temp_vault
    src = v / f"src_{uuid.uuid4().hex[:8]}.md"
    src.write_text("# raw content\n", encoding="utf-8")

    # user_command 명시 안 함 (에이전트 자율 호출 시나리오)
    r = wiki_ingest(source=str(src), project="proj", actor="agent", ctx=ctx)
    assert r["ok"] is False
    assert r["error"] == "user_command_required"
    assert "raw/ is human-first" in r["message"]
    assert r["pages_created"] == 0
    assert r["pages_updated"] == 0
    # 파일이 실제로 생성되지 않아야 함
    assert not (v / "raw" / "proj" / src.name).exists()


def test_wiki_ingest_user_command_false_explicitly_rejected(temp_vault):
    """user_command=False 명시도 동일하게 거부."""
    v, ctx = temp_vault
    src = v / f"src_{uuid.uuid4().hex[:8]}.md"
    src.write_text("# raw\n", encoding="utf-8")

    r = wiki_ingest(
        source=str(src), project="proj", actor="agent",
        ctx=ctx, user_command=False,  # 명시적 False
    )
    assert r["ok"] is False
    assert r["error"] == "user_command_required"


def test_wiki_ingest_user_command_true_succeeds(temp_vault):
    """사람 명시 명령 (user_command=True) → 정상 ingest."""
    v, ctx = temp_vault
    src = v / f"src_{uuid.uuid4().hex[:8]}.md"
    src.write_text("# raw content\n", encoding="utf-8")

    r = wiki_ingest(
        source=str(src), project="proj", actor="judy",
        ctx=ctx, user_command=True,  # 사람 운영자 시나리오
    )
    assert r["ok"] is True
    assert r["pages_created"] == 1
    # 파일이 실제로 생성됨
    assert (v / "raw" / "proj" / src.name).exists()
    assert r["actor"] == "judy"


def test_wiki_ingest_default_param_is_false():
    """기본값이 False (에이전트 거부 기본값) — 함수 시그니처 검증."""
    import inspect
    sig = inspect.signature(wiki_ingest)
    user_command_param = sig.parameters.get("user_command")
    assert user_command_param is not None, "user_command param missing"
    assert user_command_param.default is False, (
        f"user_command default must be False (rejects agent auto-call), "
        f"got {user_command_param.default!r}"
    )
